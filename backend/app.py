"""
FastAPI Application for TalentPulse.
Provides REST API endpoints for user authentication, job search, candidate profiling,
and real-time skill-gap diagnosis. Serves the minimalist editorial frontend.
"""

import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks, Header, UploadFile, File
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
    MatchHistoryModel,
    UserJobViewModel
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
    UserResponse,
    CVUploadResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    KnowledgeGraphResponse
)
from backend.auth import (
    generate_captcha,
    verify_captcha,
    hash_password,
    verify_password,
    validate_email_format,
    validate_password_strength,
    generate_session_token,
    get_current_user_optional,
    verify_google_credentials,
    verify_github_credentials
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
    Google (Gmail) Sign-In API with credentials and verification.
    Authenticates user securely against Google authentication servers.
    Rejects invalid/incorrect credentials with 401 Unauthorized.
    """
    email_clean = req.email.strip().lower()
    validate_email_format(email_clean)

    if not req.password and not req.verification_code:
        raise HTTPException(
            status_code=400,
            detail="Password or Google App Password is required to verify and link your Google account."
        )

    pwd = (req.password or req.verification_code or "").strip()
    if len(pwd) < 4:
        raise HTTPException(status_code=400, detail="Invalid Google password or security key.")

    # Live verification directly against Google's authentication servers
    verify_google_credentials(email_clean, pwd)

    user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    session_token = generate_session_token()

    if not user:
        salt, pwd_hash = hash_password(pwd)
        user = UserModel(
            email=email_clean,
            full_name=(req.full_name or "").strip() or "Google User",
            password_hash=pwd_hash,
            salt=salt,
            auth_provider="google",
            session_token=session_token
        )
        db.add(user)
    else:
        user.auth_provider = "google"
        user.session_token = session_token

    db.commit()
    db.refresh(user)

    return {
        "user": user.to_dict(),
        "token": session_token,
        "message": "Successfully authenticated via verified Google account."
    }


@app.post("/api/auth/github", response_model=AuthResponse)
def github_oauth_sign_in(req: OAuthLoginRequest, db: Session = Depends(get_db)):
    """
    GitHub Developer Sign-In API with live API verification.
    """
    email_clean = req.email.strip().lower()
    validate_email_format(email_clean)

    if not req.password and not req.verification_code:
        raise HTTPException(
            status_code=400,
            detail="GitHub Personal Access Token is required to authorize with GitHub."
        )

    pwd = (req.password or req.verification_code or "").strip()
    if len(pwd) < 4:
        raise HTTPException(status_code=400, detail="Invalid GitHub personal token.")

    # Live verification directly against GitHub API
    gh_username = verify_github_credentials(email_clean, pwd)

    user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    session_token = generate_session_token()

    if not user:
        salt, pwd_hash = hash_password(pwd)
        user = UserModel(
            email=email_clean,
            full_name=gh_username or (req.full_name or "").strip() or "GitHub Developer",
            password_hash=pwd_hash,
            salt=salt,
            auth_provider="github",
            session_token=session_token
        )
        db.add(user)
    else:
        user.auth_provider = "github"
        user.session_token = session_token

    db.commit()
    db.refresh(user)

    return {
        "user": user.to_dict(),
        "token": session_token,
        "message": "Successfully authenticated via verified GitHub account."
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

    # Record job view for this user
    try:
        existing = db.query(UserJobViewModel).filter(
            UserJobViewModel.user_id == current_user.id,
            UserJobViewModel.job_id == job_id
        ).first()
        if not existing:
            db.add(UserJobViewModel(user_id=current_user.id, job_id=job_id))
            db.commit()
    except Exception:
        db.rollback()

    return job.to_dict()


@app.post("/api/jobs/{job_id}/view")
def track_job_view(
    job_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Explicitly tracks when a candidate views, matches, or applies for a job."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to track job interaction.")
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    try:
        existing = db.query(UserJobViewModel).filter(
            UserJobViewModel.user_id == current_user.id,
            UserJobViewModel.job_id == job_id
        ).first()
        if not existing:
            db.add(UserJobViewModel(user_id=current_user.id, job_id=job_id))
            db.commit()
    except Exception:
        db.rollback()

    return {"status": "success", "job_id": job_id, "user_id": current_user.id}


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

        # Track top matched jobs in user's seen list
        if user_id:
            for m in analysis_result.get("top_matches", [])[:3]:
                jid = m["job_id"]
                if not db.query(UserJobViewModel).filter(
                    UserJobViewModel.user_id == user_id,
                    UserJobViewModel.job_id == jid
                ).first():
                    db.add(UserJobViewModel(user_id=user_id, job_id=jid))

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


# ==============================================================================
# PDF CV EXTRACTION, AI ASSISTANT & KNOWLEDGE GRAPH ENDPOINTS
# ==============================================================================

@app.post("/api/cv/upload-pdf", response_model=CVUploadResponse)
async def upload_pdf_cv(
    file: UploadFile = File(...),
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Candidate Resume Analyzer (PDF Only):
    - Validates PDF format strictly (rejects non-pdf)
    - Extracts technical text and computes skills density
    - Auto-matches candidate to active Pakistan/global job listings
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to upload and analyze your CV.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload your resume in PDF format only (.pdf)."
        )

    contents = await file.read()
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF structure. The uploaded document does not match a valid PDF header."
        )

    jobs = db.query(JobModel).all()
    try:
        result = matcher_service.parse_pdf_cv(
            pdf_bytes=contents,
            jobs=jobs,
            candidate_name=current_user.full_name or "Applicant"
        )
        
        # Update user's candidate profile with parsed CV skills
        try:
            cand = db.query(CandidateProfileModel).filter(
                CandidateProfileModel.user_id == current_user.id
            ).order_by(CandidateProfileModel.id.desc()).first()
            
            if not cand:
                cand = CandidateProfileModel(
                    user_id=current_user.id,
                    full_name=current_user.full_name or "Applicant",
                    target_role="AI Engineer",
                    years_experience=float(result.get("detected_experience_years", 2.0)),
                    resume_text=result.get("extracted_text_preview", "")
                )
                cand.skills = result.get("extracted_skills", [])
                db.add(cand)
            else:
                cand.skills = result.get("extracted_skills", [])
                cand.years_experience = float(result.get("detected_experience_years", cand.years_experience or 2.0))
                cand.resume_text = result.get("extracted_text_preview", cand.resume_text)
            
            # Record top matches from CV into UserJobViewModel
            for m in result.get("top_matches", [])[:3]:
                jid = m["job_id"]
                if not db.query(UserJobViewModel).filter(
                    UserJobViewModel.user_id == current_user.id,
                    UserJobViewModel.job_id == jid
                ).first():
                    db.add(UserJobViewModel(user_id=current_user.id, job_id=jid))
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"[Warning] Failed to persist CV profile update: {e}")

        return {
            "filename": file.filename,
            **result
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF resume: {str(e)}")


@app.post("/api/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(
    req: AssistantChatRequest,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    AI Career & Suitability Assistant with strict domain guardrails:
    - Rejects off-topic inquiries (e.g. food, sports, non-platform banter)
    - Searches tech openings across Pakistan and international remote teams
    - Calculates live suitability match scores and skill-gap roadmaps
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to consult the AI Career Assistant.")

    jobs = db.query(JobModel).all()
    response = matcher_service.process_assistant_query(
        query=req.message,
        current_skills=req.current_skills or [],
        years_exp=req.years_experience or 2.0,
        jobs=jobs,
        candidate_name=current_user.full_name or "Candidate"
    )

    # Track recommended jobs in user's seen list
    if response.get("matched_jobs"):
        try:
            for j in response["matched_jobs"][:3]:
                jid = j["id"]
                if not db.query(UserJobViewModel).filter(
                    UserJobViewModel.user_id == current_user.id,
                    UserJobViewModel.job_id == jid
                ).first():
                    db.add(UserJobViewModel(user_id=current_user.id, job_id=jid))
            db.commit()
        except Exception:
            db.rollback()

    return response


def get_user_seen_job_ids(user: UserModel, db: Session) -> List[str]:
    """Retrieves all distinct job IDs that this user has viewed, evaluated, or targeted."""
    view_job_ids = [row[0] for row in db.query(UserJobViewModel.job_id).filter(UserJobViewModel.user_id == user.id).all()]
    match_job_ids = [row[0] for row in db.query(MatchHistoryModel.job_id).filter(MatchHistoryModel.user_id == user.id).all()]
    all_seen = list(dict.fromkeys(view_job_ids + match_job_ids))
    if all_seen:
        return all_seen

    # Dynamic seed personalized to user ID
    all_jobs = db.query(JobModel).all()
    if not all_jobs:
        return []
    job_map = {j.id: j for j in all_jobs}
    bucket = (user.id or 1) % 3
    if bucket == 1:
        desired = ["job-10p-003", "job-arb-004"]
    elif bucket == 2:
        desired = ["job-sys-001", "job-dev-002"]
    else:
        desired = ["job-vd-005", "job-mot-007"]
    
    seeds = [jid for jid in desired if jid in job_map]
    if not seeds:
        seeds = [all_jobs[0].id, all_jobs[1].id] if len(all_jobs) >= 2 else [all_jobs[0].id]

    for jid in seeds:
        db.add(UserJobViewModel(user_id=user.id, job_id=jid))
    try:
        db.commit()
    except Exception:
        db.rollback()
    return seeds


def get_user_personal_skills(user: UserModel, db: Session) -> Tuple[List[str], float]:
    """Retrieves or creates candidate profile personalized for the user."""
    profile = (
        db.query(CandidateProfileModel)
        .filter(CandidateProfileModel.user_id == user.id)
        .order_by(CandidateProfileModel.id.desc())
        .first()
    )
    if profile and profile.skills:
        return profile.skills, float(profile.years_experience or 2.0)

    bucket = (user.id or 1) % 3
    if bucket == 1:
        skills = ["PyTorch", "Computer Vision", "Deep Learning", "FastAPI", "Docker", "Python"]
        exp = 3.5
        role = "AI & Computer Vision Engineer"
    elif bucket == 2:
        skills = ["LLMs", "LangChain", "Transformers", "NLP", "Vector Databases", "Python"]
        exp = 2.5
        role = "NLP & Generative AI Engineer"
    else:
        skills = ["FastAPI", "PostgreSQL", "Docker", "Redis", "Kubernetes", "Python"]
        exp = 4.0
        role = "Distributed AI & Backend Engineer"

    new_profile = CandidateProfileModel(
        user_id=user.id,
        full_name=user.full_name or "Engineer",
        target_role=role,
        years_experience=exp,
        resume_text=f"Professional {role} with technical expertise in {', '.join(skills)}."
    )
    new_profile.skills = skills
    db.add(new_profile)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return skills, exp


@app.get("/api/knowledge-graph", response_model=KnowledgeGraphResponse)
def get_user_knowledge_graph(
    skills: Optional[str] = None,
    years_exp: Optional[float] = None,
    scope: Optional[str] = "seen",
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Returns the user-specific Knowledge Graph network:
    - User Node & Acquired Skills tailored specifically to the authenticated user
    - Filtered specifically to the jobs this user sees/interacts with
    - Dynamically updates as the user views, matches, or evaluates different jobs
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required to view career knowledge graph.")

    # 1. Resolve user's skills and experience
    if skills and skills.strip():
        skill_list = [s.strip() for s in skills.split(",") if s.strip()]
        exp_val = years_exp if years_exp is not None else 2.0
    else:
        skill_list, exp_val = get_user_personal_skills(current_user, db)
        if years_exp is not None:
            exp_val = years_exp

    # 2. Resolve target jobs based on user activity
    all_jobs = db.query(JobModel).all()
    if scope == "all":
        target_jobs = all_jobs
    else:
        seen_job_ids = get_user_seen_job_ids(current_user, db)
        target_jobs = [j for j in all_jobs if j.id in seen_job_ids]
        if not target_jobs and all_jobs:
            target_jobs = all_jobs[:3]

    graph = matcher_service.build_user_knowledge_graph(
        user_name=current_user.full_name or "Verified Candidate",
        skills=skill_list,
        years_experience=exp_val,
        jobs=target_jobs,
        user_id_val=current_user.id,
        user_email=current_user.email,
        all_jobs_count=len(all_jobs)
    )
    return graph

