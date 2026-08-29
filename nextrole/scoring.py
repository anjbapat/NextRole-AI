from nextrole.models import FitAnalysis

WEIGHTS = {
    "skills_score": 0.40,
    "experience_score": 0.30,
    "domain_score": 0.15,
    "education_score": 0.05,
    "preference_score": 0.10,
}


def apply_deterministic_score(analysis: FitAnalysis) -> FitAnalysis:
    values = analysis.model_dump()
    score = round(sum(values[name] * weight for name, weight in WEIGHTS.items()))
    values["overall_score"] = score
    values["recommendation"] = "APPLY" if score >= 75 else "REVIEW" if score >= 55 else "SKIP"
    return FitAnalysis.model_validate(values)
