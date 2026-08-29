import os
from io import BytesIO
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command
from openai import OpenAIError
from pypdf import PdfReader

from nextrole.graph import build_graph
from nextrole.storage import load_journeys

load_dotenv()
st.set_page_config(page_title="NextRole-AI", page_icon=":dart:", layout="wide")


def pdf_text(f):
    return "\n".join(p.extract_text() or "" for p in PdfReader(BytesIO(f.getvalue())).pages).strip()


def state():
    snapshot = st.session_state.graph.get_state(st.session_state.config)
    return dict(snapshot.values) if snapshot else {}


def show_fit(f):
    a, b = st.columns(2)
    a.metric("Overall Fit", f"{f['overall_score']}%")
    b.metric("Recommendation", f["recommendation"])
    st.caption(f["rationale"])
    cols = st.columns(5)
    for col, (label, key) in zip(
        cols,
        [
            ("Skills", "skills_score"),
            ("Experience", "experience_score"),
            ("Domain", "domain_score"),
            ("Education", "education_score"),
            ("Preferences", "preference_score"),
        ],
    ):
        col.metric(label, f"{f[key]}%")
    a, b = st.columns(2)
    a.subheader("Strong matches")
    a.markdown("\n".join(f"- {x}" for x in f["strong_matches"]) or "None")
    b.subheader("Missing / weak areas")
    b.markdown("\n".join(f"- {x}" for x in f["weak_areas"]) or "None")
    with st.expander("Why this score", expanded=True):
        strong = sum(x["strength"] == "strong" for x in f["evidence_map"])
        partial = sum(x["strength"] == "partial" for x in f["evidence_map"])
        gaps = sum(x["strength"] == "missing" for x in f["evidence_map"])
        st.caption(
            f"{len(f['evidence_map'])} requirements: {strong} strong, {partial} partial, {gaps} gaps. Weighted in deterministic code."
        )
        st.dataframe(f["evidence_map"], use_container_width=True, hide_index=True)


def show_package(p):
    st.header("Application ready")
    st.warning("The AI cannot submit applications. Review and edit every item before continuing.")
    for x in p["resume_suggestions"]:
        with st.expander(x["original"][:100], expanded=True):
            st.write("Original", x["original"])
            st.write("Suggested", x["suggested"])
            st.caption("Why: " + x["reason"])
    p["recruiter_message"] = st.text_area("Recruiter message", p["recruiter_message"], height=140)
    p["why_im_a_fit"] = st.text_area("Why I'm a fit", p["why_im_a_fit"], height=120)
    st.write("Truthful keywords to include")
    st.write(", ".join(p["keywords_to_include"]) or "None")


def show_prep(p):
    st.header("Interview prep")
    for i, x in enumerate(p["likely_questions"], 1):
        with st.expander(f"{i}. {x['question']}", expanded=i == 1):
            st.write(f"Category: {x['category']} | Difficulty: {x['difficulty']}")
            st.write("Why it may be asked:", x["why_asked"])
            st.write("Preparation:", x["preparation_hint"])
    st.subheader("Gap-to-action plan")
    st.dataframe(p["knowledge_gaps"], use_container_width=True, hide_index=True)
    with st.expander("Study plan", expanded=True):
        for i, x in enumerate(p["study_plan"], 1):
            st.write(f"{i}. {x}")


if "graph" not in st.session_state:
    st.session_state.graph = build_graph()
if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": str(uuid4())}}
st.title("NextRole-AI")
st.caption(
    "Evidence -> deterministic decision -> truthful tailoring -> human approval -> gap-based preparation"
)
analysis_tab, application_tab, prep_tab, tracker_tab = st.tabs(
    ["Job Analysis", "Application", "Interview Prep", "Applications"]
)
with st.sidebar:
    configured = bool(os.getenv("FIREWORKS_API_KEY") or os.getenv("NEBIUS_API_KEY"))
    demo = st.toggle("Demo mode", value=not configured)
    if demo:
        st.info(
            "Local lexical scoring is active. Add a provider key for semantic evidence extraction."
        )
    if st.button("Start a new journey", use_container_width=True):
        st.session_state.config = {"configurable": {"thread_id": str(uuid4())}}
        st.rerun()
with analysis_tab:
    upload = st.file_uploader("Resume", type=["pdf"])
    jd = st.text_area(
        "Job description", height=260, placeholder="Paste the full job description..."
    )
    if st.button("Analyze job", type="primary", disabled=not (upload and jd.strip())):
        try:
            text = pdf_text(upload)
            if not text:
                raise ValueError("No selectable text found. Please use a text-based PDF.")
            jid = st.session_state.config["configurable"]["thread_id"]
            with st.spinner("Mapping requirements to resume evidence..."):
                st.session_state.graph.invoke(
                    {
                        "journey_id": jid,
                        "resume_text": text,
                        "job_description": jd,
                        "demo_mode": demo,
                        "errors": [],
                    },
                    st.session_state.config,
                )
            st.rerun()
        except (OSError, RuntimeError, ValueError, OpenAIError) as exc:
            st.error(f"Analysis failed: {exc}")
    s = state()
    if s.get("fit_analysis"):
        show_fit(s["fit_analysis"])
with application_tab:
    s = state()
    if not s.get("application_package"):
        st.info("Analyze an APPLY or REVIEW role to create an application package.")
    else:
        package = dict(s["application_package"])
        show_package(package)
        if s.get("status") == "awaiting_approval":
            st.session_state.graph.update_state(
                st.session_state.config, {"application_package": package}
            )
            reject, approve = st.columns(2)
            if reject.button("Reject", use_container_width=True):
                st.session_state.graph.invoke(Command(resume="reject"), st.session_state.config)
                st.rerun()
            if approve.button("Approve application", type="primary", use_container_width=True):
                try:
                    with st.spinner("Creating interview preparation..."):
                        st.session_state.graph.invoke(
                            Command(resume="approve"), st.session_state.config
                        )
                    st.rerun()
                except (OSError, RuntimeError, ValueError, OpenAIError) as exc:
                    st.error(f"Interview preparation failed safely: {exc}")
        else:
            st.success(f"Application status: {s.get('status', '').upper()}")
with prep_tab:
    s = state()
    if s.get("interview_prep"):
        if s.get("interview_source") == "local_fallback":
            st.warning(
                "The hosted model did not complete this step, so NextRole-AI generated "
                "an evidence-based local preparation plan at no API cost."
            )
        show_prep(s["interview_prep"])
    else:
        st.info("Interview preparation appears after you approve the application package.")
with tracker_tab:
    rows = load_journeys()
    if not rows:
        st.info("No saved applications yet.")
    else:
        st.dataframe(
            [{**r, "fit_score": f"{r['fit_score']}%"} for r in rows],
            use_container_width=True,
            hide_index=True,
        )
        selected = st.selectbox(
            "Resume a saved journey",
            rows,
            format_func=lambda r: f"{r['company']} - {r['role']} ({r['status']})",
        )
        if st.button("Continue selected journey"):
            st.session_state.config = {"configurable": {"thread_id": selected["id"]}}
            st.rerun()
