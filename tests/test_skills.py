from nextrole.models import FitAnalysis, JobAnalysis
from nextrole.skills import clean_skills, reconcile_evidence


def test_generic_tokens_removed_but_phrases_preserved():
    assert clean_skills(["big", "analysis", "Big Data", "Data Analysis", "Python", "python"]) == [
        "Big Data",
        "Data Analysis",
        "Python",
    ]


def test_evidence_is_complete_and_job_scoped():
    job = JobAnalysis(required_skills=["Python", "LangGraph"], preferred_skills=["Azure OpenAI"])
    fit = FitAnalysis(
        overall_score=70,
        skills_score=70,
        experience_score=70,
        domain_score=70,
        education_score=70,
        preference_score=70,
        recommendation="REVIEW",
        rationale="x",
        evidence_map=[
            {"requirement": "Python", "evidence": "Built Python APIs", "strength": "strong"},
            {"requirement": "analysis", "evidence": None, "strength": "missing"},
        ],
    )
    result = reconcile_evidence(fit, job)
    assert [x.requirement for x in result.evidence_map] == ["Python", "LangGraph", "Azure OpenAI"]
    assert result.strong_matches == ["Python"]
    assert result.weak_areas == ["LangGraph", "Azure OpenAI"]
