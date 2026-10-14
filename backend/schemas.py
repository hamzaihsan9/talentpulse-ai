"""
Pydantic schemas for TalentPulse API.
Defines strongly typed data structures for authentication, job openings,
candidate evaluations, and skill diagnostics.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict


# --- Authentication Schemas ---

class CaptchaResponse(BaseModel):
    captcha_token: str
    captcha_question: str


class UserRegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=128)
    password: str = Field(min_length=6, max_length=100)
    captcha_token: str
    captcha_answer: str


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=128)
    password: str = Field(min_length=1, max_length=100)
    captcha_token: str
    captcha_answer: str


class OAuthLoginRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = "Verified User"
    provider_id: Optional[str] = None
    password: Optional[str] = None
    verification_code: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    auth_provider: str
    created_at: Optional[str]


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    message: str


# --- Job & Candidate Evaluation Schemas ---

class JobBase(BaseModel):
    title: str
    company: str
    location: str
    tier: Optional[str] = None
    level: str = "Mid-Level"
    salary_range: Optional[str] = None
    experience_years: float = 2.0
    description: str
    required_skills: List[str] = []
    preferred_skills: List[str] = []
    industry: Optional[str] = None
    apply_url: Optional[str] = None


class JobCreate(JobBase):
    id: str


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class CandidateAnalyzeRequest(BaseModel):
    full_name: str = Field(default="Candidate", description="Applicant name")
    target_role: Optional[str] = Field(default=None, description="Desired job title")
    years_experience: float = Field(default=2.0, ge=0.0, le=30.0)
    skills: List[str] = Field(default=[], description="Explicit list of skills")
    resume_text: Optional[str] = Field(default="", description="Resume summary or profile description")
    target_job_id: Optional[str] = Field(default=None, description="Target job ID")


class SkillGapAnalysis(BaseModel):
    missing_required: List[str]
    missing_preferred: List[str]
    matched_skills: List[str]
    recommendations: List[str]
    urgency: str  # "Immediate Action", "Recommended", "Competitive Edge"


class MatchResultResponse(BaseModel):
    job_id: str
    job_title: str
    company: str
    location: str
    salary_range: Optional[str]
    apply_url: Optional[str] = None
    overall_match_score: float
    cosine_similarity: float
    readiness_level: str
    skill_gap: SkillGapAnalysis
    suggested_roadmap: List[str]


class MultiJobMatchResponse(BaseModel):
    candidate_name: str
    extracted_skills: List[str]
    years_experience: float
    top_matches: List[MatchResultResponse]
    model_inference_ms: float


class ModelMetricsResponse(BaseModel):
    vocab_size: int
    feature_dim: int
    best_val_loss: float
    val_mae: float
    val_correlation: float
    epochs_trained: int
    trained_at: str
    history: Dict[str, Any]


# --- CV Upload & Skill Extraction Schema ---

class CVUploadResponse(BaseModel):
    filename: str
    page_count: int
    extracted_skills: List[str]
    years_experience: float
    summary_excerpt: str
    total_skills_found: int
    top_matches: List[MatchResultResponse]


# --- AI Assistant Schemas with Guardrails ---

class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    current_skills: Optional[List[str]] = []
    years_experience: Optional[float] = 2.0
    conversation_history: Optional[List[Dict[str, str]]] = []


class AssistantChatResponse(BaseModel):
    reply: str
    is_error: bool = False
    action_suggested: Optional[str] = None
    suggested_jobs: Optional[List[Dict[str, Any]]] = None


# --- Knowledge Graph Schemas ---

class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "user", "skill", "job", "company", "gap"
    group: str
    val: float = 1.0
    meta: Dict[str, Any] = {}


class GraphLink(BaseModel):
    source: str
    target: str
    type: str  # "possesses", "requires", "offers", "evaluated", "gap"
    weight: float = 1.0
    label: Optional[str] = None


class KnowledgeGraphResponse(BaseModel):
    nodes: List[GraphNode]
    links: List[GraphLink]
    summary: Dict[str, Any]

