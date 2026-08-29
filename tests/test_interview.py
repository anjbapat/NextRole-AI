from nextrole import graph
from nextrole.models import FitAnalysis, JobAnalysis


def test_interview_failure_uses_local_fallback(monkeypatch):
    def fail(job, fit):
        raise RuntimeError("truncated")

    monkeypatch.setattr(graph.llm, "prepare_interview", fail)
    job = JobAnalysis(title="AI Engineer", required_skills=["LangGraph"])
    fit = FitAnalysis(
        overall_score=70,
        skills_score=70,
        experience_score=70,
        domain_score=70,
        education_score=70,
        preference_score=70,
        recommendation="REVIEW",
        rationale="x",
        weak_areas=["LangGraph"],
    )
    result = graph.prep(
        {
            "job_analysis": job.model_dump(),
            "fit_analysis": fit.model_dump(),
            "demo_mode": False,
            "errors": [],
        }
    )
    assert result["interview_source"] == "local_fallback"
    assert result["interview_prep"]["likely_questions"]
    assert "truncated" in result["errors"][0]
