from typing import Literal, Optional
from pydantic import BaseModel, Field

# Bounds matter: FastAPI validates every response against these models, so a
# scoring bug that produces e.g. 130 or -5 fails loudly instead of reaching the UI.


class ComponentScore(BaseModel):
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=100, description='Share of the final score; sums to 100 across components')


class RequirementMatch(BaseModel):
    requirement: str
    best_match: str
    similarity: float = Field(ge=0, le=100, description='Rescaled cosine similarity of the closest resume line')


class SemanticResult(BaseModel):
    raw_cosine_mean: float
    requirements: list[RequirementMatch]


class ContentResult(BaseModel):
    bullet_count: int = Field(ge=0)
    action_verb_ratio: float = Field(ge=0, le=100, description='% of bullets starting with a strong verb')
    quantified_bullets: int = Field(ge=0)
    weak_phrases: list[str]


class ContactInfo(BaseModel):
    email: bool
    phone: bool
    linkedin: bool
    github: bool


class FormattingResult(BaseModel):
    contact: ContactInfo
    sections_found: list[str]
    sections_missing: list[str]
    word_count: int = Field(ge=0)


class Suggestion(BaseModel):
    priority: Literal['high', 'medium', 'low']
    category: str
    message: str


class AnalysisResponse(BaseModel):
    id: Optional[str] = None            # set when saved to the user's history
    filename: str
    job_title: str
    parser: Literal['groq', 'local']    # whether LLM parsing was used
    ats_score: int = Field(ge=0, le=100)
    score_label: Literal['Excellent', 'Good', 'Fair', 'Needs Work']
    breakdown: dict[str, ComponentScore]
    keyword_match: float = Field(ge=0, le=100, description='Keyword component score (0 if the JD has no hard skills)')
    matched_keywords: list[str]
    missing_keywords: list[str]
    missing_preferred: list[str]
    resume_skills: list[str]
    semantic: SemanticResult
    content: ContentResult
    formatting: FormattingResult
    suggestions: list[Suggestion]
    candidate_name: Optional[str] = None


class HistoryItem(BaseModel):
    id: str
    filename: str
    job_title: str
    ats_score: int
    keyword_match: float
    created_at: str
    analysis_result: dict


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    groq_enabled: bool
    database_enabled: bool
