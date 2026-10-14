"""
Inference & Skill-Gap Analysis Service for TalentPulse AI.
Bridges PyTorch deep learning model inference with database entities and candidate analytics.
"""

import time
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import torch
import numpy as np

from model.tokenizer import SkillTokenizer
from model.architecture import SiameseCareerMatcher
from backend.database import JobModel, CandidateProfileModel, MatchHistoryModel


class CareerMatchingService:
    def __init__(self):
        self.device = torch.device("cpu")
        self.tokenizer = SkillTokenizer()
        self.model: Optional[SiameseCareerMatcher] = None
        self._load_model()

    def _load_model(self):
        base_dir = Path(__file__).resolve().parent.parent
        weights_path = base_dir / "model" / "weights" / "best_career_matcher.pt"
        feature_dim = self.tokenizer.vocab_size + 2
        
        self.model = SiameseCareerMatcher(feature_dim=feature_dim, hidden_dim=128, embed_dim=64)
        
        if weights_path.exists():
            checkpoint = torch.load(weights_path, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])
            print(f"[Service] Loaded PyTorch model checkpoint from {weights_path}")
        else:
            print("[Service] No checkpoint found, using uninitialized model weights.")
            
        self.model.to(self.device)
        self.model.eval()

    def analyze_candidate(
        self,
        full_name: str,
        years_experience: float,
        explicit_skills: List[str],
        resume_text: str,
        jobs: List[JobModel],
        target_job_id: Optional[str] = None
    ) -> Dict:
        start_time = time.time()
        
        # 1. Feature Extraction & Skill Discovery
        combined_text = f"{resume_text or ''} {' '.join(explicit_skills or [])}"
        extracted_skills = self.tokenizer.extract_skills_from_text(combined_text)
        all_candidate_skills = list(set([s.strip() for s in explicit_skills if s.strip()] + extracted_skills))
        
        cand_feature_vec = self.tokenizer.build_dense_profile(
            text=combined_text,
            explicit_skills=all_candidate_skills,
            years_exp=years_experience
        )
        cand_tensor = torch.tensor(cand_feature_vec, dtype=torch.float32).unsqueeze(0).to(self.device)

        # 2. Score candidate against jobs
        target_jobs = [j for j in jobs if j.id == target_job_id] if target_job_id else jobs
        if not target_jobs and jobs:
            target_jobs = jobs

        results = []
        with torch.no_grad():
            for job in target_jobs:
                job_text = f"{job.title} {job.description}"
                all_job_skills = list(set(job.required_skills + job.preferred_skills))
                job_feature_vec = self.tokenizer.build_dense_profile(
                    text=job_text,
                    explicit_skills=all_job_skills,
                    years_exp=job.experience_years
                )
                job_tensor = torch.tensor(job_feature_vec, dtype=torch.float32).unsqueeze(0).to(self.device)

                cand_emb, job_emb, pred_score = self.model(cand_tensor, job_tensor)
                
                # Cosine similarity in unit hypersphere space
                cos_sim = float(torch.sum(cand_emb * job_emb, dim=-1).item())
                score_val = float(pred_score.item())

                # Skill Gap Diagnosis
                cand_skills_set = set(s.lower() for s in all_candidate_skills)
                missing_req = [s for s in job.required_skills if s.lower() not in cand_skills_set]
                missing_pref = [s for s in job.preferred_skills if s.lower() not in cand_skills_set]
                matched = [s for s in job.required_skills if s.lower() in cand_skills_set]

                # Readiness classification
                if score_val >= 78.0:
                    readiness = "Interview Ready (Top 5%)"
                    urgency = "Competitive Edge"
                elif score_val >= 55.0:
                    readiness = "Strong Prospect"
                    urgency = "Recommended"
                else:
                    readiness = "Upskilling Required"
                    urgency = "Immediate Action"

                # Generate actionable career roadmap based on missing skills & Pakistan/Global market
                roadmap = self._generate_roadmap(missing_req, missing_pref, years_experience, job.experience_years)

                results.append({
                    "job_id": job.id,
                    "job_title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "salary_range": job.salary_range,
                    "apply_url": getattr(job, "apply_url", None) or f"https://www.google.com/search?q={job.company.replace(' ', '+')}+careers",
                    "overall_match_score": round(score_val, 1),
                    "cosine_similarity": round(cos_sim, 3),
                    "readiness_level": readiness,
                    "skill_gap": {
                        "missing_required": missing_req,
                        "missing_preferred": missing_pref,
                        "matched_skills": matched,
                        "recommendations": roadmap[:3],
                        "urgency": urgency
                    },
                    "suggested_roadmap": roadmap
                })

        # Rank by overall match score descending
        results.sort(key=lambda x: x["overall_match_score"], reverse=True)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "candidate_name": full_name or "Applicant",
            "extracted_skills": all_candidate_skills,
            "years_experience": years_experience,
            "top_matches": results,
            "model_inference_ms": elapsed_ms
        }

    def _generate_roadmap(self, missing_req: List[str], missing_pref: List[str], cand_exp: float, job_exp: float) -> List[str]:
        steps = []
        if missing_req:
            priority = ", ".join(missing_req[:3])
            steps.append(f"Master core prerequisites: Prioritize building functional GitHub repositories demonstrating {priority}.")
        
        if "PyTorch" in missing_req or "Deep Learning" in missing_req:
            steps.append("Deep Learning Foundations: Implement end-to-end training pipelines in PyTorch with custom loss functions and tensor operations.")
            
        if "Docker" in missing_req or "FastAPI" in missing_req:
            steps.append("Production Engineering: Containerize your Python models using Docker and expose RESTful inference endpoints with FastAPI.")
            
        if "LLMs" in missing_req or "RAG" in missing_req or "LangChain" in missing_req:
            steps.append("Generative AI Systems: Construct a production RAG application utilizing vector indexing, hybrid search, and LangChain/LlamaIndex.")

        if "Transformers" in missing_req or "BERT" in missing_req:
            steps.append("Modern NLP: Experiment with Hugging Face transformers, fine-tuning pre-trained models on domain-specific corpora.")

        if cand_exp < job_exp:
            diff = job_exp - cand_exp
            steps.append(f"Experience Calibration: Frame your projects around production metrics (latency, throughput, drift) to bridge the {diff:.1f}-year seniority expectation.")

        if not steps:
            steps.append("Profile is highly optimized! Prepare for system design interviews and live PyTorch coding assessments.")

        return steps


# Global singleton instance
matcher_service = CareerMatchingService()
