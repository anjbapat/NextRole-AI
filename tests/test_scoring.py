from nextrole.models import FitAnalysis
from nextrole.scoring import apply_deterministic_score


def test_weighted_score_and_routing():
    raw = FitAnalysis(
        overall_score=1,
        skills_score=80,
        experience_score=70,
        domain_score=60,
        education_score=100,
        preference_score=90,
        recommendation="SKIP",
        rationale="x",
    )
    scored = apply_deterministic_score(raw)
    assert scored.overall_score == 76
    assert scored.recommendation == "APPLY"


def test_review_threshold():
    raw = FitAnalysis(
        overall_score=0,
        skills_score=55,
        experience_score=55,
        domain_score=55,
        education_score=55,
        preference_score=55,
        recommendation="SKIP",
        rationale="x",
    )
    assert apply_deterministic_score(raw).recommendation == "REVIEW"
