from typing import Literal

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    name: str = "Candidate"
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_highlights: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)


class JobAnalysis(BaseModel):
    title: str = "Target role"
    company: str = "Unknown company"
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)


class RequirementEvidence(BaseModel):
    requirement: str
    evidence: str | None = None
    strength: Literal["strong", "partial", "missing"]


class FitAnalysis(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    skills_score: int = Field(ge=0, le=100)
    experience_score: int = Field(ge=0, le=100)
    domain_score: int = Field(ge=0, le=100)
    education_score: int = Field(ge=0, le=100)
    preference_score: int = Field(ge=0, le=100, default=100)
    recommendation: Literal["APPLY", "REVIEW", "SKIP"]
    rationale: str
    strong_matches: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    experience_matches: list[str] = Field(default_factory=list)
    evidence_map: list[RequirementEvidence] = Field(default_factory=list)


class ResumeSuggestion(BaseModel):
    original: str
    suggested: str
    reason: str


class ApplicationPackage(BaseModel):
    resume_suggestions: list[ResumeSuggestion] = Field(default_factory=list)
    recruiter_message: str
    why_im_a_fit: str
    cover_letter_summary: str = ""
    keywords_to_include: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    question: str
    category: Literal["technical", "behavioral", "system_design", "resume"]
    difficulty: Literal["easy", "medium", "hard"]
    why_asked: str
    preparation_hint: str
    focus: str = ""


class KnowledgeGap(BaseModel):
    topic: str
    priority: Literal["HIGH", "MEDIUM", "LOW"]
    action: str


class InterviewPrep(BaseModel):
    likely_questions: list[InterviewQuestion] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    study_plan: list[str] = Field(default_factory=list)
