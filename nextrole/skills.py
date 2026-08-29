import re

from nextrole.models import FitAnalysis, JobAnalysis, RequirementEvidence

GENERIC_SINGLE_WORDS = {
    "ability",
    "analysis",
    "analytical",
    "big",
    "business",
    "communication",
    "company",
    "data",
    "detail",
    "development",
    "excellent",
    "experience",
    "knowledge",
    "management",
    "preferred",
    "required",
    "responsible",
    "skills",
    "strong",
    "team",
    "using",
    "work",
    "working",
}


def normalize_skill(value: str) -> str | None:
    value = re.sub(r"\s+", " ", value.strip(" .,:;-")).strip()
    if not value or len(value) < 2:
        return None
    if " " not in value and value.casefold() in GENERIC_SINGLE_WORDS:
        return None
    return value


def clean_skills(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        cleaned = normalize_skill(value)
        if cleaned and cleaned.casefold() not in seen:
            seen.add(cleaned.casefold())
            result.append(cleaned)
    return result


def normalize_job(job: JobAnalysis) -> JobAnalysis:
    values = job.model_dump()
    values["required_skills"] = clean_skills(job.required_skills)
    values["preferred_skills"] = clean_skills(job.preferred_skills)
    return JobAnalysis.model_validate(values)


def reconcile_evidence(fit: FitAnalysis, job: JobAnalysis) -> FitAnalysis:
    requirements = clean_skills(job.required_skills + job.preferred_skills)
    returned = {item.requirement.casefold(): item for item in fit.evidence_map}
    evidence = [
        returned.get(req.casefold())
        or RequirementEvidence(requirement=req, evidence=None, strength="missing")
        for req in requirements
    ]
    values = fit.model_dump()
    values["evidence_map"] = [item.model_dump() for item in evidence]
    values["strong_matches"] = [item.requirement for item in evidence if item.strength == "strong"]
    values["weak_areas"] = [item.requirement for item in evidence if item.strength != "strong"]
    return FitAnalysis.model_validate(values)
