"""
SQLAlchemy ORM 模型
对应 database/schema.sql 的所有表
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, ForeignKey, UniqueConstraint, CheckConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from src.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_code = Column(String(20), unique=True, nullable=False)
    team_name = Column(String(100), nullable=False)
    members = Column(JSONB)
    contact_email = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submissions = relationship("Submission", back_populates="team")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    question_code = Column(String(20), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    max_score = Column(Integer, nullable=False, default=100)
    category = Column(String(50), nullable=False)
    evaluation_weights = Column(JSONB, nullable=False)
    test_cases_config = Column(JSONB)
    baseline_description = Column(Text)
    prompt_template_dir = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="question")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False)
    submission_version = Column(Integer, nullable=False, default=1)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64))
    project_metadata = Column("metadata", JSONB)
    status = Column(String(20), nullable=False, default="pending")
    submitted_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    team = relationship("Team", back_populates="submissions")
    question = relationship("Question", back_populates="submissions")
    dimension_scores = relationship("DimensionScore", back_populates="submission")
    final_score = relationship("FinalScore", back_populates="submission", uselist=False)

    __table_args__ = (
        UniqueConstraint("team_id", "question_id", "submission_version"),
    )


class DimensionScore(Base):
    __tablename__ = "dimension_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    dimension = Column(String(50), nullable=False)
    score = Column(Integer, nullable=False)
    raw_score = Column(Float)
    confidence = Column(Float, nullable=False)
    verification_count = Column(Integer, default=1)
    llm_model = Column(String(50))
    reasoning = Column(Text)
    strengths = Column(JSONB)
    weaknesses = Column(JSONB)
    improvements = Column(JSONB)
    raw_response = Column(JSONB)
    scored_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="dimension_scores")

    __table_args__ = (
        UniqueConstraint("submission_id", "dimension"),
        CheckConstraint("score BETWEEN 0 AND 100"),
        CheckConstraint("confidence BETWEEN 0 AND 1"),
    )


class FinalScore(Base):
    __tablename__ = "final_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True)
    functionality_score = Column(Integer)
    code_quality_score = Column(Integer)
    architecture_score = Column(Integer)
    innovation_score = Column(Integer)
    documentation_score = Column(Integer)
    testing_score = Column(Integer)
    test_execution_score = Column(Integer)
    bonus_score = Column(Integer, default=0)
    total_score = Column(Float, nullable=False)
    confidence = Column(Float)
    human_review_required = Column(Boolean, default=False)
    human_reviewed = Column(Boolean, default=False)
    human_adjusted_score = Column(Float)
    reviewer_notes = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)
    finalized_at = Column(DateTime)

    submission = relationship("Submission", back_populates="final_score")


class ReviewTask(Base):
    __tablename__ = "review_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    celery_task_id = Column(String(100))
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    verifier_model = Column(String(50), nullable=False)
    target_dimension = Column(String(50), nullable=False)
    original_score = Column(Integer)
    verified_score = Column(Integer)
    deviation = Column(Float)
    confidence = Column(Float)
    needs_human_review = Column(Boolean, default=False)
    verification_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SandboxExecution(Base):
    __tablename__ = "sandbox_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    container_id = Column(String(100))
    image_used = Column(String(100))
    execution_type = Column(String(50))
    exit_code = Column(Integer)
    stdout = Column(Text)
    stderr = Column(Text)
    execution_time_ms = Column(Integer)
    resource_usage = Column(JSONB)
    security_flags = Column(JSONB)
    executed_at = Column(DateTime, default=datetime.utcnow)


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    reviewer_name = Column(String(100))
    reviewed_dimensions = Column(JSONB)
    original_scores = Column(JSONB)
    adjusted_scores = Column(JSONB)
    adjustment_reason = Column(Text)
    reviewed_at = Column(DateTime, default=datetime.utcnow)


class ReviewReport(Base):
    __tablename__ = "review_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    report_path = Column(String(500))
    report_content = Column(Text)
    summary = Column(Text)
    generation_status = Column(String(20), default="pending")
    generated_at = Column(DateTime)

    submission = relationship("Submission")

    __table_args__ = (UniqueConstraint("submission_id"),)


class ScoreCalibrationLog(Base):
    __tablename__ = "score_calibration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    dimension = Column(String(50))
    agent_score = Column(Integer)
    human_score = Column(Integer)
    delta = Column(Integer)
    prompt_version = Column(String(20))
    model_version = Column(String(50))
    logged_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission")
