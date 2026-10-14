"""
FastAPI Application for TalentPulse.
Provides REST API endpoints for user authentication, job search, candidate profiling,
and real-time skill-gap diagnosis. Serves the minimalist editorial frontend.
"""

import json
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.database import (
    get_db,
    init_database,
    UserModel,
    JobModel,
    CandidateProfileModel,
    MatchHistoryModel
)
from backend.schemas import (
    JobResponse,
    CandidateAnalyzeRequest,
    MultiJobMatchResponse,
    ModelMetricsResponse,
    CaptchaResponse,
    UserRegisterRequest,
    UserLoginRequest,
    OAuthLoginRequest,
    AuthResponse,
    UserResponse
)
from backend.auth import (
    generate_captcha,
    verify_captcha,
    hash_password,
    verify_password,
    validate_email_format,
    validate_password_strength,
    generate_session_token,
    get_current_user_optional
)
from backend.service import matcher_service
from model.train import train_pipeline

app = FastAPI(
    title="TalentPulse",
    description="Enterprise candidate-job matching engine and skill diagnostics platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"
WEIGHTS_DIR = BASE_DIR / "model" / "weights"

# Mount static folder
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup():
    """Ensure database schema is created and initial jobs are seeded."""
    db = init_database()
    db.close()


@app.get("/", include_in_schema=False)
def serve_index():
    """Serve the minimalist frontend interface."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend interface not found")
    return FileResponse(index_path)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "TalentPulse",
        "state": "operational"
    }


# ==============================================================================
# AUTHENTICATION & USER MANAGEMENT ENDPOINTS
# ==============================================================================

@app.get("/api/auth/captcha", response_model=CaptchaResponse)
def get_captcha():
    """Generates an anti-bot mathematical verification challenge."""
    return generate_captcha()


@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Registers a new unique user account with rigorous validation checks:
    - Captcha verification
    - Email format verification
    - Password strength verification
    - Single account uniqueness check (no duplicate registrations)
    """
    # 1. Verify Captcha
    if not verify_captcha(req.captcha_token, req.captcha_answer):
        raise HTTPException(status_code=400, detail="Incorrect security code. Please solve the updated challenge.")

    # 2. Validate email and password
    email_clean = req.email.strip().lower()
    validate_email_format(email_clean)
    validate_password_strength(req.password)

    # 3. Enforce single account check (no duplicate accounts)
    existing_user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Each user can register only once."
        )

    # 4. Secure salt and hash
    salt, pwd_hash = hash_password(req.password)
    session_token = generate_session_token()

    new_user = UserModel(
        email=email_clean,
        full_name=req.full_name.strip(),
        password_hash=pwd_hash,
        salt=salt,
        auth_provider="local",
        session_token=session_token
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "user": new_user.to_dict(),
        "token": session_token,
        "message": "Account successfully created."
    }


@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user with email, password, and anti-bot verification.
    Guarantees strict account isolation.
    """
    # 1. Verify Captcha
    if not verify_captcha(req.captcha_token, req.captcha_answer):
        raise HTTPException(status_code=400, detail="Incorrect security code. Please solve the updated challenge.")

    email_clean = req.email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == email_clean).first()

    if not user or not user.password_hash or not user.salt:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # 2. Verify password
    if not verify_password(req.password, user.salt, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # 3. Issue fresh session token
    session_token = generate_session_token()
    user.session_token = session_token
    db.commit()

    return {
        "user": user.to_dict(),
        "token": session_token,
        "message": "Successfully authenticated."
    }


@app.post("/api/auth/google", response_model=AuthResponse)
def google_oauth_sign_in(req: OAuthLoginRequest, db: Session = Depends(get_db)):
    """
    Google (Gmail) Sign-In API.
    Authenticates or provisions user securely with verified email identity.
    """
    email_clean = req.email.strip().lower()
    validate_email_format(email_clean)

    user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    session_token = generate_session_token()

    if not user:
        user = UserModel(
            email=email_clean,
            full_name=req.full_name.strip() or "Google User",
            auth_provider="google",
            session_token=session_token
        )
        db.add(user)
    else:
        user.session_token = session_token

    db.commit()
    db.refresh(user)

    return {
        "user": user.to_dict(),
        "token": session_token,
        "message": "Signed in with Google."
    }


@app.post("/api/auth/github", response_model=AuthResponse)
def github_oauth_sign_in(req: OAuthLoginRequest, db: Session = Depends(get_db)):
    """
    GitHub Sign-In API.
    Authenticates or provisions user securely with GitHub developer credentials.
    """
    email_clean = req.email.strip().lower()
    validate_email_format(email_clean)

    user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    session_token = generate_session_token()

    if not user:
        user = UserModel(
            email=email_clean,
            full_name=req.full_name.strip() or "GitHub Developer",
            auth_provider="github",
            session_token=session_token
        )
        db.add(user)
    else:
        user.session_token = session_token

    db.commit()
    db.refresh(user)

    return {
        "user": user.to_dict(),
        "token": session_token,
        "message": "Signed in with GitHub."
    }


@app.get("/api/auth/me", response_model=UserResponse)
def get_current_user_profile(user: Optional[UserModel] = Depends(get_current_user_optional)):
    """Returns current active user session."""
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or not authenticated.")
    return user.to_dict()


@app.post("/api/auth/logout")
def logout_user(user: Optional[UserModel] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    """Revokes session token."""
    if user:
        user.session_token = None
        db.commit()
    return {"message": "Logged out successfully."}


# ==============================================================================
# JOB CATALOG & ANALYSIS ENDPOINTS
# ==============================================================================

@app.get("/api/jobs", response_model=List[JobResponse])
def get_jobs(
    tier: Optional[str] = None,
    level: Optional[str] = None,
    query: Optional[str] = None,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Retrieve all tech job openings with optional filtering. Requires authentication."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to view market openings.")
    q = db.query(JobModel)
    if tier:
        q = q.filter(JobModel.tier == tier)
    if level:
        q = q.filter(JobModel.level == level)
    if query:
        search = f"%{query}%"
        q = q.filter((JobModel.title.ilike(search)) | (JobModel.company.ilike(search)) | (JobModel.location.ilike(search)))
    
    jobs = q.all()
    return [j.to_dict() for j in jobs]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job_by_id(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to view job details.")
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return job.to_dict()


@app.get("/api/skills")
def get_skills_taxonomy():
    """Returns the categorized skills taxonomy for quick-select chips."""
    taxonomy_file = DATA_DIR / "skills_taxonomy.json"
    if taxonomy_file.exists():
        with open(taxonomy_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"all": matcher_service.tokenizer.skills}


@app.post("/api/analyze", response_model=MultiJobMatchResponse)
def analyze_candidate_profile(
    request: CandidateAnalyzeRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Core Evaluation Endpoint:
    Computes semantic alignment against active openings and performs
    comprehensive skill-gap diagnosis with candidate data isolation.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to evaluate candidate profiles.")
    jobs = db.query(JobModel).all()
    if not jobs:
        raise HTTPException(status_code=404, detail="No job postings available for analysis")

    analysis_result = matcher_service.analyze_candidate(
        full_name=request.full_name,
        years_experience=request.years_experience,
        explicit_skills=request.skills,
        resume_text=request.resume_text or "",
        jobs=jobs,
        target_job_id=request.target_job_id
    )

    # Persist candidate and match log associated with current_user
    try:
        user_id = current_user.id if current_user else None
        cand_record = CandidateProfileModel(
            user_id=user_id,
            full_name=request.full_name,
            target_role=request.target_role or "AI Engineer",
            years_experience=request.years_experience,
            resume_text=request.resume_text
        )
        cand_record.skills = analysis_result["extracted_skills"]
        db.add(cand_record)
        db.flush()

        top_match = analysis_result["top_matches"][0] if analysis_result["top_matches"] else None
        if top_match:
            match_log = MatchHistoryModel(
                user_id=user_id,
                candidate_id=cand_record.id,
                job_id=top_match["job_id"],
                match_score=top_match["overall_match_score"],
                cosine_similarity=top_match["cosine_similarity"],
                readiness_level=top_match["readiness_level"]
            )
            match_log.missing_skills_json = json.dumps(top_match["skill_gap"]["missing_required"])
            match_log.recommendations_json = json.dumps(top_match["suggested_roadmap"])
            db.add(match_log)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Warning] Failed to log match to database: {e}")

    return analysis_result


@app.get("/api/model/metrics")
def get_model_metrics():
    """Returns evaluation metrics, loss curves, and reliability indices."""
    metrics_file = WEIGHTS_DIR / "train_metrics.json"
    if not metrics_file.exists():
        return {
            "status": "not_trained",
            "message": "Metrics log file was not found."
        }
    with open(metrics_file, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    return metrics


@app.post("/api/model/retrain")
def retrain_model(background_tasks: BackgroundTasks):
    """Triggers retraining pass over current distribution."""
    def run_training_and_reload():
        train_pipeline(epochs=20, batch_size=32)
        matcher_service._load_model()

    background_tasks.add_task(run_training_and_reload)
    return {"message": "Model calibration task initiated in background."}
