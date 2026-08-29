import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from nextrole import llm
from nextrole.interview import build_fallback_interview
from nextrole.models import (
    ApplicationPackage,
    FitAnalysis,
    InterviewPrep,
    JobAnalysis,
    ResumeProfile,
)
from nextrole.scoring import apply_deterministic_score
from nextrole.skills import normalize_job, reconcile_evidence
from nextrole.storage import DB_PATH, save_journey


class AgentState(TypedDict, total=False):
    journey_id: str
    resume_text: str
    job_description: str
    resume_profile: dict
    job_analysis: dict
    fit_analysis: dict
    application_package: dict
    approval: str
    interview_prep: dict
    status: str
    current_step: str
    demo_mode: bool
    errors: list[str]
    interview_source: str


def parse_resume(s):
    errors = list(s.get("errors", []))
    try:
        p = (
            llm.demo_analysis(s["resume_text"], s["job_description"])[0]
            if s.get("demo_mode")
            else llm.parse_resume(s["resume_text"])
        )
    except RuntimeError as exc:
        p = llm.demo_analysis(s["resume_text"], s["job_description"])[0]
        errors.append(f"Resume model fallback: {exc}")
    return {
        "resume_profile": p.model_dump(),
        "status": "resume_parsed",
        "current_step": "JOB_ANALYSIS",
        "errors": errors,
    }


def analyze_job(s):
    j = (
        llm.demo_analysis(s["resume_text"], s["job_description"])[1]
        if s.get("demo_mode")
        else llm.analyze_job(s["job_description"])
    )
    j = normalize_job(j)
    return {"job_analysis": j.model_dump(), "status": "job_analyzed", "current_step": "FIT_SCORING"}


def calculate_fit(s):
    errors = list(s.get("errors", []))
    try:
        raw = (
            llm.demo_analysis(s["resume_text"], s["job_description"])[2]
            if s.get("demo_mode")
            else llm.calculate_fit(
                ResumeProfile.model_validate(s["resume_profile"]),
                JobAnalysis.model_validate(s["job_analysis"]),
            )
        )
    except RuntimeError as exc:
        raw = llm.demo_analysis(s["resume_text"], s["job_description"])[2]
        errors.append(f"Fit model fallback: {exc}")
    f = apply_deterministic_score(
        reconcile_evidence(raw, JobAnalysis.model_validate(s["job_analysis"]))
    )
    return {
        "fit_analysis": f.model_dump(),
        "status": "fit_calculated",
        "current_step": "APPLICATION_DECISION",
        "errors": errors,
    }


def route_fit(s):
    return "save_skipped" if s["fit_analysis"]["recommendation"] == "SKIP" else "tailor_application"


def tailor(s):
    if s.get("demo_mode"):
        strong = ", ".join(s["fit_analysis"]["strong_matches"][:4]) or "relevant experience"
        p = ApplicationPackage(
            resume_suggestions=[],
            recruiter_message=f"I'm interested in this role and bring experience with {strong}.",
            why_im_a_fit=f"My background aligns through {strong}.",
            cover_letter_summary=f"Evidence-backed alignment: {strong}.",
            keywords_to_include=s["fit_analysis"]["strong_matches"][:6],
        )
    else:
        p = llm.tailor_application(
            s["resume_text"],
            JobAnalysis.model_validate(s["job_analysis"]),
            FitAnalysis.model_validate(s["fit_analysis"]),
        )
    return {
        "application_package": p.model_dump(),
        "status": "awaiting_approval",
        "current_step": "HUMAN_APPROVAL",
    }


def approval(s):
    decision = str(
        interrupt(
            {
                "question": "Review the package. The AI cannot submit it. Approve or reject?",
                "options": ["approve", "reject"],
            }
        )
    ).lower()
    return {
        "approval": decision,
        "status": f"application_{decision}",
        "current_step": "INTERVIEW_PREPARATION" if decision == "approve" else "REJECTED",
    }


def route_approval(s):
    return "interview_prep" if s.get("approval") == "approve" else "save_rejected"


def prep(s):
    if s.get("demo_mode"):
        gaps = s["fit_analysis"]["weak_areas"][:3]
        matches = s["fit_analysis"]["strong_matches"][:3]
        p = InterviewPrep(
            likely_questions=[
                {
                    "question": f"How have you used {x}, and what tradeoffs did you make?",
                    "category": "technical",
                    "difficulty": "medium",
                    "why_asked": f"The role values {x}.",
                    "preparation_hint": f"Prepare a STAR example grounded in your {x} evidence.",
                    "focus": x,
                }
                for x in matches
            ],
            knowledge_gaps=[
                {
                    "topic": x,
                    "priority": "HIGH" if i == 0 else "MEDIUM",
                    "action": f"Study {x} and build a small example.",
                }
                for i, x in enumerate(gaps)
            ],
            study_plan=[
                f"Review {x}; create one example; practice a two-minute answer." for x in gaps
            ],
        )
    else:
        job = JobAnalysis.model_validate(s["job_analysis"])
        fit = FitAnalysis.model_validate(s["fit_analysis"])
        try:
            p = llm.prepare_interview(job, fit)
        except RuntimeError as exc:
            p = build_fallback_interview(job, fit)
            return {
                "interview_prep": p.model_dump(),
                "status": "interview_ready_fallback",
                "current_step": "INTERVIEW_PREPARATION",
                "errors": [*s.get("errors", []), f"Interview model fallback: {exc}"],
                "interview_source": "local_fallback",
            }
    return {
        "interview_prep": p.model_dump(),
        "status": "interview_ready",
        "current_step": "INTERVIEW_PREPARATION",
    }


def saver(status):
    def node(s):
        return {"journey_id": save_journey({**s, "status": status}), "status": status}

    return node


def build_graph():
    g = StateGraph(AgentState)
    for name, node in [
        ("parse_resume", parse_resume),
        ("analyze_job", analyze_job),
        ("calculate_fit", calculate_fit),
        ("tailor_application", tailor),
        ("human_approval", approval),
        ("interview_prep", prep),
        ("save_skipped", saver("skipped")),
        ("save_rejected", saver("rejected")),
        ("save_complete", saver("ready_to_submit")),
    ]:
        g.add_node(name, node)
    g.add_edge(START, "parse_resume")
    g.add_edge("parse_resume", "analyze_job")
    g.add_edge("analyze_job", "calculate_fit")
    g.add_conditional_edges("calculate_fit", route_fit)
    g.add_edge("tailor_application", "human_approval")
    g.add_conditional_edges("human_approval", route_approval)
    g.add_edge("interview_prep", "save_complete")
    g.add_edge("save_skipped", END)
    g.add_edge("save_rejected", END)
    g.add_edge("save_complete", END)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return g.compile(checkpointer=SqliteSaver(conn))
