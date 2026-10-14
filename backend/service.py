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

    def parse_pdf_cv(self, pdf_bytes: bytes, jobs: List[JobModel], candidate_name: str = "Candidate") -> Dict:
        """
        Parses resume from PDF binary bytes:
        - Extracts raw text across pages using pypdf
        - Tokenizes technical competencies against standardized dictionary
        - Infers years of experience via contextual regex heuristic
        - Executes model matching against active tech market openings
        """
        import io
        import re
        import pypdf

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        except Exception as e:
            raise ValueError(f"Failed to read PDF structure: {str(e)}")

        page_texts = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text()
                if t:
                    page_texts.append(t)
            except Exception:
                continue

        full_text = "\n".join(page_texts).strip()
        if not full_text:
            raise ValueError("Could not extract readable text from PDF. The document may be empty or an image scan.")

        # 1. Extract technical competencies
        extracted_skills = self.tokenizer.extract_skills_from_text(full_text)

        # 2. Heuristic extraction of years of experience
        exp_years = 2.0
        exp_matches = re.findall(
            r'(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp|hands-on)',
            full_text,
            re.IGNORECASE
        )
        if exp_matches:
            try:
                found_exp = float(exp_matches[0])
                if 0.0 <= found_exp <= 30.0:
                    exp_years = found_exp
            except Exception:
                pass

        # 3. Match against jobs
        analysis = self.analyze_candidate(
            full_name=candidate_name,
            years_experience=exp_years,
            explicit_skills=extracted_skills,
            resume_text=full_text,
            jobs=jobs
        )

        summary_excerpt = full_text[:380].strip() + ("..." if len(full_text) > 380 else "")

        return {
            "page_count": len(reader.pages),
            "extracted_skills": extracted_skills,
            "years_experience": exp_years,
            "summary_excerpt": summary_excerpt,
            "total_skills_found": len(extracted_skills),
            "top_matches": analysis["top_matches"]
        }

    def process_assistant_query(
        self,
        query: str,
        current_skills: List[str],
        years_exp: float,
        jobs: List[JobModel],
        candidate_name: str = "User"
    ) -> Dict:
        """
        Processes AI Assistant queries with strict domain guardrails.
        Rejects non-career queries (e.g., cooking, sports, casual chit-chat).
        Provides intelligent job search, match scoring, compensation insights, and roadmap guidance.
        """
        import re

        clean_q = query.strip()
        lower_q = clean_q.lower()

        # 1. STRICT GUARDRAIL ENFORCEMENT
        off_topic_patterns = [
            r'\b(?:biryani|pulao|nihari|recipe|cook|cooking|bake|baking|curry|pizza|burger|pasta|food|dish|dessert|ingredients)\b',
            r'\b(?:cricket|football|soccer|psl|ipl|fifa|world cup|match score|weather|rain|temperature)\b',
            r'\b(?:joke|riddle|funny|meme|song|sing|lyrics|movie|film|actor|actress|cinema|bollywood|hollywood)\b',
            r'\b(?:politics|election|prime minister|president|parliament|horoscope|zodiac|astrology)\b'
        ]

        for pat in off_topic_patterns:
            if re.search(pat, lower_q):
                return {
                    "reply": "⚠️ **Off-Topic Request Rejected**\n\nI am the **TalentPulse AI Career Assistant**. I specialize strictly in career diagnostics, tech job search, technical skill gaps, resume review, and Pakistani/global tech market intelligence.\n\nPlease ask a career, job, skill, or hiring-related question.",
                    "is_error": True,
                    "action_suggested": None,
                    "suggested_jobs": []
                }

        # Check for career / technical / platform relevance
        career_keywords = [
            "job", "opening", "vacancy", "career", "hiring", "company", "companies", "role", "position",
            "systems", "devsinc", "10pearls", "arbisoft", "venturedive", "motive", "daraz", "remote",
            "skill", "skills", "experience", "resume", "cv", "pdf", "profile", "salary", "compensation", "pkr", "usd", "pay",
            "match", "score", "suitability", "gap", "missing", "roadmap", "learn", "prepare", "interview",
            "python", "pytorch", "deep learning", "machine learning", "ai", "llm", "rag", "langchain",
            "docker", "fastapi", "sql", "transformers", "nlp", "computer vision", "opencv", "kubernetes",
            "knowledge graph", "talentpulse", "hire", "apply"
        ]

        is_relevant = any(k in lower_q for k in career_keywords)
        if not is_relevant and len(clean_q.split()) > 2:
            return {
                "reply": "⚠️ **Off-Topic Request**\n\nI can only assist with career development, matching analysis, job listings, and skill gaps on TalentPulse. Try asking:\n• *'Find Generative AI or RAG jobs'* \n• *'What is my match score with Python and Docker?'* \n• *'What are the highest paying tech jobs in Lahore?'*",
                "is_error": True,
                "action_suggested": "explore_jobs",
                "suggested_jobs": []
            }

        # 2. INTENT: MATCH & SUITABILITY EVALUATION
        if any(w in lower_q for w in ["match", "score", "suitability", "gap", "missing", "how do i qualify"]):
            analysis = self.analyze_candidate(
                full_name=candidate_name,
                years_experience=years_exp,
                explicit_skills=current_skills,
                resume_text=" ".join(current_skills),
                jobs=jobs
            )
            top = analysis["top_matches"][0] if analysis["top_matches"] else None
            if top:
                reply = (
                    f"🎯 **Suitability Diagnostic for {candidate_name}**\n\n"
                    f"• **Top Match:** {top['job_title']} at **{top['company']}** ({top['overall_match_score']}% fit)\n"
                    f"• **Readiness Level:** {top['readiness_level']} (Latent Cosine Alignment: {top['cosine_similarity']})\n"
                    f"• **Matched Competencies:** {', '.join(top['skill_gap']['matched_skills']) if top['skill_gap']['matched_skills'] else 'None'}\n"
                    f"• **Priority Gaps:** {', '.join(top['skill_gap']['missing_required']) if top['skill_gap']['missing_required'] else 'All core prerequisites satisfied!'}\n\n"
                    f"💡 *Actionable Recommendation:* {top['suggested_roadmap'][0] if top['suggested_roadmap'] else 'Profile well aligned.'}"
                )
                return {
                    "reply": reply,
                    "is_error": False,
                    "action_suggested": "view_match",
                    "suggested_jobs": [top]
                }

        # 3. INTENT: SALARY & COMPENSATION BENCHMARKS
        if any(w in lower_q for w in ["salary", "compensation", "pay", "package", "rate"]):
            reply = (
                "💰 **TalentPulse Market Compensation Benchmarks (2026)**\n\n"
                "• **Tier-1 Enterprise (Systems Limited, Motive):**\n"
                "  PKR 450,000 – 850,000 / month for Senior Deep Learning & Telematics AI Engineers.\n\n"
                "• **High-Growth Software Houses (Devsinc, Arbisoft, 10Pearls, VentureDive):**\n"
                "  PKR 280,000 – 600,000 / month for Mid-to-Senior GenAI, NLP, MLOps, and Computer Vision Specialists.\n\n"
                "• **US / Silicon Valley Remote Clients (CognitiveFlow):**\n"
                "  $2,500 – $4,500 / month (~PKR 700,000 – 1,250,000) for Autonomous Full-Stack AI Engineers.\n\n"
                "All listings feature direct application links to verified portals."
            )
            return {
                "reply": reply,
                "is_error": False,
                "action_suggested": "view_jobs",
                "suggested_jobs": []
            }

        # 4. INTENT: SPECIFIC JOB SEARCH
        matched_jobs = []
        for j in jobs:
            searchable = f"{j.title} {j.company} {j.location} {' '.join(j.required_skills)}".lower()
            # Check terms
            words = [w for w in lower_q.split() if len(w) > 3 and w not in ["jobs", "find", "search", "show", "openings", "looking"]]
            if any(w in searchable for w in words):
                matched_jobs.append(j)

        if not matched_jobs:
            matched_jobs = jobs[:3]

        suggested = []
        reply_lines = [f"🔍 **Found {len(matched_jobs[:4])} relevant opportunities:**\n"]
        for j in matched_jobs[:4]:
            apply_url = getattr(j, "apply_url", None) or "https://www.google.com"
            reply_lines.append(
                f"• **{j.title}** at **{j.company}** ({j.location})\n"
                f"  Experience: {j.experience_years} Yrs | Stack: {', '.join(j.required_skills[:4])}\n"
                f"  Compensation: {j.salary_range} | [Apply Directly ↗]({apply_url})\n"
            )
            suggested.append(j.to_dict())

        reply_lines.append("Would you like to evaluate your specific suitability score or upload your PDF CV for automated matching?")

        return {
            "reply": "\n".join(reply_lines),
            "is_error": False,
            "action_suggested": "view_jobs",
            "suggested_jobs": suggested
        }

    def build_user_knowledge_graph(
        self,
        user_name: str,
        skills: List[str],
        years_experience: float,
        jobs: List[JobModel]
    ) -> Dict:
        """
        Builds a high-dimensional Knowledge Graph mapping:
        - Candidate Node (User)
        - Acquired Skills (Connected to User)
        - Market Openings (Connected to User with suitability weights)
        - Employer Companies (Connected to Job Openings)
        - Skill Gaps / Required Tech (Connected to Jobs)
        """
        nodes = []
        links = []
        node_ids = set()

        def add_node(n_id, label, n_type, group, val=10, meta=None):
            if n_id not in node_ids:
                nodes.append({
                    "id": n_id,
                    "label": label,
                    "type": n_type,
                    "group": group,
                    "val": val,
                    "meta": meta or {}
                })
                node_ids.add(n_id)

        # 1. Central Candidate Node
        user_id = "user-profile"
        user_label = user_name or "Verified Candidate"
        add_node(
            user_id,
            user_label,
            "user",
            "candidate",
            val=24,
            meta={"experience": f"{years_experience} Yrs", "skills_count": len(skills)}
        )

        # 2. Acquired User Skills
        user_skill_set = set(skills)
        for s in skills:
            s_id = f"skill-{s.lower().replace(' ', '-')}"
            add_node(s_id, s, "skill", "acquired_skill", val=13, meta={"status": "Possessed"})
            links.append({
                "source": user_id,
                "target": s_id,
                "type": "possesses",
                "weight": 2.2,
                "label": "Possesses"
            })

        # Run analysis to calculate real match affinity weights
        analysis = self.analyze_candidate(
            full_name=user_name,
            years_experience=years_experience,
            explicit_skills=skills,
            resume_text=" ".join(skills),
            jobs=jobs
        )
        score_map = {m["job_id"]: m for m in analysis["top_matches"]}

        # 3. Market Openings & Companies
        for j in jobs:
            match_data = score_map.get(j.id, {})
            score = match_data.get("overall_match_score", 50.0)
            readiness = match_data.get("readiness_level", "Prospect")

            job_node_id = f"job-{j.id}"
            add_node(
                job_node_id,
                j.title,
                "job",
                "job_opening",
                val=16,
                meta={
                    "company": j.company,
                    "location": j.location,
                    "salary": j.salary_range,
                    "score": f"{score}%",
                    "readiness": readiness,
                    "apply_url": getattr(j, "apply_url", None)
                }
            )

            # Link: User -> Job (Match Evaluation)
            links.append({
                "source": user_id,
                "target": job_node_id,
                "type": "evaluated",
                "weight": round(score / 25.0, 1) or 1.0,
                "label": f"{score}% Match"
            })

            # Company Node
            comp_id = f"comp-{j.company.lower().replace(' ', '-')}"
            add_node(
                comp_id,
                j.company,
                "company",
                "employer",
                val=12,
                meta={"location": j.location, "tier": j.tier}
            )
            # Link: Job -> Company
            links.append({
                "source": job_node_id,
                "target": comp_id,
                "type": "offers",
                "weight": 1.5,
                "label": "Offered By"
            })

            # Skills required by Job
            for req in j.required_skills:
                if req in user_skill_set:
                    # User already possesses this requirement!
                    s_id = f"skill-{req.lower().replace(' ', '-')}"
                    links.append({
                        "source": job_node_id,
                        "target": s_id,
                        "type": "requires",
                        "weight": 1.3,
                        "label": "Satisfied Requirement"
                    })
                else:
                    # Missing requirement (Skill Gap)
                    gap_id = f"gap-{req.lower().replace(' ', '-')}"
                    add_node(gap_id, req, "gap", "missing_skill", val=10, meta={"status": "Skill Deficit", "needed_by": j.company})
                    links.append({
                        "source": job_node_id,
                        "target": gap_id,
                        "type": "gap",
                        "weight": 1.0,
                        "label": "Skill Deficit"
                    })

        high_fit_count = len([j for j in jobs if score_map.get(j.id, {}).get("overall_match_score", 0) >= 70])
        summary = {
            "total_nodes": len(nodes),
            "total_entities": len(nodes),
            "total_links": len(links),
            "total_connections": len(links),
            "candidate_skills_count": len(skills),
            "acquired_skills": len(skills),
            "jobs_evaluated": len(jobs),
            "high_affinity_matches": high_fit_count,
            "high_fit_hubs": high_fit_count
        }

        return {
            "nodes": nodes,
            "links": links,
            "summary": summary
        }


# Global singleton instance
matcher_service = CareerMatchingService()

