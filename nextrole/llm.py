import json
import os
import re
from time import sleep
from typing import TypeVar

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError

from nextrole.models import (
    ApplicationPackage,
    FitAnalysis,
    InterviewPrep,
    JobAnalysis,
    ResumeProfile,
)

T = TypeVar("T", bound=BaseModel)


class StructuredLLM:
    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "fireworks").lower()
        self.provider = provider
        settings = {
            "fireworks": (
                "FIREWORKS_API_KEY",
                "FIREWORKS_MODEL",
                "accounts/fireworks/models/deepseek-v4-flash-0731",
                "FIREWORKS_BASE_URL",
                "https://api.fireworks.ai/inference/v1",
            ),
            "nebius": (
                "NEBIUS_API_KEY",
                "NEBIUS_MODEL",
                "Qwen/Qwen3-235B-A22B",
                "NEBIUS_BASE_URL",
                "https://api.tokenfactory.nebius.com/v1/",
            ),
        }
        if provider not in settings:
            raise RuntimeError("LLM_PROVIDER must be fireworks or nebius")
        kn, mn, md, un, ud = settings[provider]
        key = os.getenv(kn, "").strip()
        if not key:
            raise RuntimeError(f"{kn} is not configured")
        self.client = OpenAI(api_key=key, base_url=os.getenv(un, ud))
        self.model = os.getenv(mn, md)

    def structured(self, schema: type[T], system: str, prompt: str) -> T:
        spec = schema.model_json_schema()
        last_error = None
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system + " Return only JSON matching the supplied schema.",
                        },
                        {"role": "user", "content": prompt + "\nSchema:\n" + json.dumps(spec)},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": schema.__name__, "schema": spec},
                    },
                    temperature=0.1,
                    max_tokens=3000 * (attempt + 1),
                    extra_body={"reasoning_effort": "none"} if self.provider == "fireworks" else {},
                )
                choice = response.choices[0]
                content = choice.message.content
                if choice.finish_reason == "length":
                    raise RuntimeError(
                        f"Model output was truncated at {3000 * (attempt + 1)} tokens"
                    )
                if not content:
                    raise RuntimeError("The model returned an empty response")
                return schema.model_validate_json(content)
            except (ValidationError, RuntimeError, OpenAIError) as exc:
                last_error = exc
                if attempt == 0:
                    sleep(0.25)
        raise RuntimeError(f"Structured model output failed after retry: {last_error}")


def parse_resume(t):
    return StructuredLLM().structured(
        ResumeProfile,
        "Extract every explicitly stated technical skill, tool, platform, method, domain, education item, and concise experience highlight. Do not omit skills appearing in skills sections or project bullets. Deduplicate names. Return at most 50 skills and 15 highlights, each under 240 characters. Never invent details.",
        t[:30000],
    )


def analyze_job(t):
    return StructuredLLM().structured(
        JobAnalysis,
        "Extract an exhaustive, normalized list of technologies, tools, methods, domain competencies, education requirements, and responsibilities. Preserve meaningful phrases such as big data and data analysis. Never emit generic standalone words such as big, analysis, strong, work, or experience as skills.",
        t[:30000],
    )


def calculate_fit(r, j):
    return StructuredLLM().structured(
        FitAnalysis,
        "Evaluate every required and preferred skill from the supplied job object. Produce exactly one evidence_map row per requirement, using a concise resume quote or null. A missing skill must be an actual named job requirement, never a generic word. Score the five components from this evidence. Do not decide routing; code recalculates the weighted score. Never invent experience.",
        json.dumps({"resume": r.model_dump(), "job": j.model_dump()}),
    )


def tailor_application(t, j, f):
    return StructuredLLM().structured(
        ApplicationPackage,
        "Rewrite only supported evidence. Never invent employers, technologies, metrics, responsibilities, or certifications. Mark unsupported requirements as gaps.",
        json.dumps({"resume": t[:25000], "job": j.model_dump(), "fit": f.model_dump()}),
    )


def prepare_interview(j, f):
    return StructuredLLM().structured(
        InterviewPrep,
        "Connect every question and study action to job requirements, resume evidence, or identified gaps.",
        json.dumps({"job": j.model_dump(), "fit": f.model_dump()}),
    )


def demo_analysis(resume_text, job_text):
    tok = lambda v: set(re.findall(r"[a-z][a-z+#.]{2,}", v.lower()))
    rw, jw = tok(resume_text), tok(job_text)
    stop = {"and", "the", "with", "for", "you", "our", "will", "are", "this", "that"}
    overlap = sorted((rw & jw) - stop)
    missing = sorted((jw - rw) - stop)[:8]
    skill = min(100, 30 + len(overlap) * 6)
    exp = max(20, skill - 8)
    p = ResumeProfile(summary=resume_text[:240], skills=overlap[:12])
    j = JobAnalysis(required_skills=(overlap + missing)[:12])
    evidence = [
        {"requirement": x, "evidence": f"Mentioned in resume: {x}", "strength": "strong"}
        for x in overlap[:8]
    ] + [{"requirement": x, "evidence": None, "strength": "missing"} for x in missing[:5]]
    f = FitAnalysis(
        overall_score=0,
        skills_score=skill,
        experience_score=exp,
        domain_score=skill,
        education_score=70,
        preference_score=100,
        recommendation="REVIEW",
        rationale="Demo lexical evidence. Add an API key for semantic analysis.",
        strong_matches=overlap[:8],
        weak_areas=missing[:5],
        experience_matches=overlap[:4],
        evidence_map=evidence,
    )
    return p, j, f
