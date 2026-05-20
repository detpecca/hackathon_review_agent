"""
Pydantic schemas for request/response validation
对应 openapi.yaml 中的 components/schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ============================================================
# Team schemas
# ============================================================
class TeamMember(BaseModel):
    name: str
    role: Optional[str] = None
    email: Optional[EmailStr] = None


class TeamCreate(BaseModel):
    team_code: str = Field(..., max_length=20, example="T001")
    team_name: str = Field(..., max_length=100, example="Code Masters")
    members: Optional[List[TeamMember]] = None
    contact_email: Optional[EmailStr] = None


class TeamResponse(BaseModel):
    id: UUID
    team_code: str
    team_name: str
    members: Optional[List[Dict[str, Any]]] = None
    contact_email: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedTeams(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[TeamResponse]


# ============================================================
# Question schemas
# ============================================================
class QuestionResponse(BaseModel):
    id: int
    question_code: str
    title: str
    max_score: int
    category: str
    evaluation_weights: Dict[str, float]

    model_config = {"from_attributes": True}


class QuestionDetail(QuestionResponse):
    description: Optional[str] = None
    baseline_description: Optional[str] = None
    test_cases_config: Optional[Dict[str, Any]] = None


# ============================================================
# Submission schemas
# ============================================================
class SubmissionResponse(BaseModel):
    id: UUID
    team_id: UUID
    question_id: int
    submission_version: int
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    status: str
    submitted_at: Optional[datetime] = None
    review_task_id: Optional[UUID] = None
    estimated_completion: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedSubmissions(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[SubmissionResponse]


class SubmissionDetail(SubmissionResponse):
    metadata: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    final_score: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None


# ============================================================
# Score schemas
# ============================================================
class DimensionScoreItem(BaseModel):
    dimension: str
    score: int
    confidence: float
    reasoning: Optional[str] = None
    strengths: Optional[List[str]] = None
    weaknesses: Optional[List[str]] = None
    improvements: Optional[List[str]] = None
    llm_model: Optional[str] = None
    scored_at: Optional[datetime] = None


class DimensionScoresResponse(BaseModel):
    submission_id: UUID
    scores: List[DimensionScoreItem]
    total_score: Optional[float] = None
    overall_confidence: Optional[float] = None


class VerificationResultItem(BaseModel):
    id: UUID
    verifier_model: str
    target_dimension: str
    original_score: Optional[int] = None
    verified_score: Optional[int] = None
    deviation: Optional[float] = None
    confidence: Optional[float] = None
    needs_human_review: bool
    verification_reason: Optional[str] = None
    created_at: Optional[datetime] = None


class ReviewReportResponse(BaseModel):
    submission_id: UUID
    status: str
    content: Optional[str] = None
    download_url: Optional[str] = None
    generated_at: Optional[datetime] = None


# ============================================================
# Leaderboard schemas
# ============================================================
class LeaderboardItem(BaseModel):
    rank: int
    team_id: UUID
    team_code: str
    team_name: str
    total_score: float
    confidence: Optional[float] = None
    human_reviewed: Optional[bool] = None
    scored_at: Optional[datetime] = None


class LeaderboardResponse(BaseModel):
    question_id: Optional[int] = None
    question_title: Optional[str] = None
    total: int
    page: int
    page_size: int
    items: List[LeaderboardItem]


# ============================================================
# Human Review schemas
# ============================================================
class HumanReviewInput(BaseModel):
    reviewer_name: str
    adjusted_scores: Dict[str, int]
    adjustment_reason: Optional[str] = None
    reviewer_notes: Optional[str] = None


class HumanReviewResult(BaseModel):
    submission_id: UUID
    reviewer_name: str
    original_total: Optional[float] = None
    adjusted_total: float
    finalized: bool
    reviewed_at: Optional[datetime] = None


class ReviewMaterials(BaseModel):
    submission_id: UUID
    project_files: Optional[List[Dict[str, Any]]] = None
    readme_content: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    agent_scores: Optional[List[DimensionScoreItem]] = None
    verification_results: Optional[List[VerificationResultItem]] = None
    sandbox_logs: Optional[List[Dict[str, Any]]] = None
    code_preview: Optional[List[Dict[str, Any]]] = None


# ============================================================
# System schemas
# ============================================================
class HealthStatus(BaseModel):
    status: str
    version: str
    components: Dict[str, str]
    timestamp: str


class TaskStats(BaseModel):
    pending: int
    running: int
    completed_last_hour: int
    failed_last_hour: int
    avg_processing_time_ms: int
    queue_depth: int
    active_workers: int


class ReviewTaskResponse(BaseModel):
    id: UUID
    submission_id: UUID
    task_type: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
