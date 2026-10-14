"""
Database Layer for TalentPulse using SQLAlchemy and SQLite.
Manages Users, Authentication, Job Openings, Candidate Profiles, and Evaluation Logs.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "talentpulse.db"
DB_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String(128), unique=True, index=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    password_hash = Column(String(256), nullable=True)
    salt = Column(String(64), nullable=True)
    auth_provider = Column(String(32), default="local")  # "local", "google", "github"
    session_token = Column(String(128), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    candidates = relationship("CandidateProfileModel", back_populates="user", cascade="all, delete-orphan")
    matches = relationship("MatchHistoryModel", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    company = Column(String(128), nullable=False)
    location = Column(String(128), nullable=False)
    tier = Column(String(64), nullable=True)
    level = Column(String(32), default="Mid-Level")
    salary_range = Column(String(64), nullable=True)
    experience_years = Column(Float, default=2.0)
    description = Column(Text, nullable=False)
    required_skills_json = Column(Text, default="[]")
    preferred_skills_json = Column(Text, default="[]")
    industry = Column(String(64), nullable=True)
    apply_url = Column(String(256), nullable=True)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    matches = relationship("MatchHistoryModel", back_populates="job", cascade="all, delete-orphan")

    @property
    def required_skills(self) -> List[str]:
        return json.loads(self.required_skills_json or "[]")

    @required_skills.setter
    def required_skills(self, skills: List[str]):
        self.required_skills_json = json.dumps(skills)

    @property
    def preferred_skills(self) -> List[str]:
        return json.loads(self.preferred_skills_json or "[]")

    @preferred_skills.setter
    def preferred_skills(self, skills: List[str]):
        self.preferred_skills_json = json.dumps(skills)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "tier": self.tier,
            "level": self.level,
            "salary_range": self.salary_range,
            "experience_years": self.experience_years,
            "description": self.description,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "industry": self.industry,
            "apply_url": self.apply_url or f"https://www.google.com/search?q={self.company.replace(' ', '+')}+careers",
        }


class CandidateProfileModel(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    full_name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=True)
    target_role = Column(String(128), nullable=True)
    years_experience = Column(Float, default=0.0)
    skills_json = Column(Text, default="[]")
    resume_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserModel", back_populates="candidates")
    matches = relationship("MatchHistoryModel", back_populates="candidate", cascade="all, delete-orphan")

    @property
    def skills(self) -> List[str]:
        return json.loads(self.skills_json or "[]")

    @skills.setter
    def skills(self, val: List[str]):
        self.skills_json = json.dumps(val)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "target_role": self.target_role,
            "years_experience": self.years_experience,
            "skills": self.skills,
            "resume_text": self.resume_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MatchHistoryModel(Base):
    __tablename__ = "match_history"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    job_id = Column(String(64), ForeignKey("jobs.id"), nullable=False)
    match_score = Column(Float, nullable=False)
    cosine_similarity = Column(Float, nullable=False)
    missing_skills_json = Column(Text, default="[]")
    readiness_level = Column(String(32), nullable=False)
    recommendations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("UserModel", back_populates="matches")
    candidate = relationship("CandidateProfileModel", back_populates="matches")
    job = relationship("JobModel", back_populates="matches")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "match_score": round(self.match_score, 1),
            "cosine_similarity": round(self.cosine_similarity, 3),
            "missing_skills": json.loads(self.missing_skills_json or "[]"),
            "readiness_level": self.readiness_level,
            "recommendations": json.loads(self.recommendations_json or "[]"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def init_database() -> Session:
    """Creates database schema, migrates columns, and seeds/updates market jobs."""
    Base.metadata.create_all(bind=engine)
    
    # Auto-migrate columns if tables existed prior to auth isolation
    with engine.connect() as conn:
        for table, col, col_type in [
            ("candidates", "user_id", "INTEGER REFERENCES users(id)"),
            ("match_history", "user_id", "INTEGER REFERENCES users(id)"),
            ("jobs", "apply_url", "VARCHAR(256)")
        ]:
            try:
                cols = [row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()]
                if col not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                    conn.commit()
            except Exception:
                pass

    session = SessionLocal()
    
    # Seed or synchronize application URLs from raw_jobs.json
    raw_path = Path(__file__).resolve().parent.parent / "data" / "raw_jobs.json"
    if raw_path.exists():
        with open(raw_path, "r", encoding="utf-8") as f:
            jobs_data = json.load(f)
        
        for j in jobs_data:
            job_rec = session.query(JobModel).filter(JobModel.id == j["id"]).first()
            if not job_rec:
                job_rec = JobModel(
                    id=j["id"],
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    tier=j.get("tier"),
                    level=j.get("level", "Mid-Level"),
                    salary_range=j.get("salary_range"),
                    experience_years=float(j.get("experience_years", 2.0)),
                    description=j["description"],
                    industry=j.get("industry"),
                    apply_url=j.get("apply_url")
                )
                job_rec.required_skills = j.get("required_skills", [])
                job_rec.preferred_skills = j.get("preferred_skills", [])
                session.add(job_rec)
            else:
                if j.get("apply_url") and not job_rec.apply_url:
                    job_rec.apply_url = j.get("apply_url")
        session.commit()

    return session


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
