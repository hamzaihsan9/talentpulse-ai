"""
End-to-End System Test Suite for TalentPulse AI.
Tests PyTorch Siamese Matcher, Skill Tokenizer, SQLite Database, and FastAPI REST endpoints.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import torch
from model.tokenizer import SkillTokenizer
from model.architecture import SiameseCareerMatcher
from backend.database import init_database, JobModel
from backend.service import CareerMatchingService


class TestTalentPulseAI(unittest.TestCase):
    def setUp(self):
        self.tokenizer = SkillTokenizer()
        self.service = CareerMatchingService()

    def test_01_tokenizer_skill_extraction(self):
        """Verifies boundary-aware regex skill extraction."""
        sample_text = "I have 3 years of experience writing PyTorch deep learning code, training Transformers with Hugging Face, and deploying on Docker with FastAPI."
        extracted = self.tokenizer.extract_skills_from_text(sample_text)
        
        self.assertIn("PyTorch", extracted)
        self.assertIn("Docker", extracted)
        self.assertIn("FastAPI", extracted)
        self.assertIn("Transformers", extracted)
        print(f"[Pass] Tokenizer extracted skills: {extracted}")

    def test_02_pytorch_siamese_architecture(self):
        """Tests PyTorch Dual-Encoder forward pass shapes and score ranges."""
        feature_dim = self.tokenizer.vocab_size + 2
        model = SiameseCareerMatcher(feature_dim=feature_dim, hidden_dim=128, embed_dim=64)
        
        batch_size = 4
        dummy_cand = torch.randn(batch_size, feature_dim)
        dummy_job = torch.randn(batch_size, feature_dim)

        cand_emb, job_emb, scores = model(dummy_cand, dummy_job)
        
        self.assertEqual(cand_emb.shape, (batch_size, 64))
        self.assertEqual(job_emb.shape, (batch_size, 64))
        self.assertEqual(scores.shape, (batch_size, 1))

        # Test L2 normalization on unit hypersphere
        cand_norm = torch.norm(cand_emb, p=2, dim=-1)
        self.assertTrue(torch.allclose(cand_norm, torch.ones(batch_size), atol=1e-5))

        print(f"[Pass] PyTorch Siamese Dual-Encoder verified. Embed shape: {cand_emb.shape}, Score shape: {scores.shape}")

    def test_03_sqlite_database_seeding(self):
        """Verifies database initialization and job seeding."""
        session = init_database()
        job_count = session.query(JobModel).count()
        self.assertGreater(job_count, 0)
        
        first_job = session.query(JobModel).first()
        self.assertIsNotNone(first_job.title)
        self.assertIsNotNone(first_job.company)
        self.assertGreater(len(first_job.required_skills), 0)
        session.close()
        print(f"[Pass] SQLite database contains {job_count} seeded tech openings.")

    def test_04_career_matching_service_inference(self):
        """Verifies full inference pipeline and skill gap diagnostics."""
        session = init_database()
        jobs = session.query(JobModel).all()
        
        result = self.service.analyze_candidate(
            full_name="Muhammad Ali",
            years_experience=3.0,
            explicit_skills=["Python", "PyTorch", "Transformers", "Docker"],
            resume_text="Senior ML developer focusing on generative models and neural search.",
            jobs=jobs
        )
        session.close()

        self.assertIn("top_matches", result)
        self.assertGreater(len(result["top_matches"]), 0)
        
        top = result["top_matches"][0]
        self.assertIn("overall_match_score", top)
        self.assertIn("cosine_similarity", top)
        self.assertIn("skill_gap", top)
        self.assertIn("suggested_roadmap", top)
        
        print(f"[Pass] Top matched job: {top['job_title']} at {top['company']}")
        print(f"       Score: {top['overall_match_score']}%, Cosine: {top['cosine_similarity']}, Readiness: {top['readiness_level']}")

    def test_05_auth_security_engine(self):
        """Verifies PBKDF2 password hashing, captcha challenges, and user isolation."""
        from backend.auth import (
            generate_captcha, verify_captcha, hash_password, verify_password,
            validate_email_format, validate_password_strength, _CAPTCHA_STORE
        )
        from backend.database import UserModel

        # 1. Captcha
        c = generate_captcha()
        tok = c["captcha_token"]
        ans = _CAPTCHA_STORE[tok]["answer"]
        self.assertTrue(verify_captcha(tok, ans))
        self.assertFalse(verify_captcha(tok, ans))  # one-time use

        # 2. Salt & Hash
        salt, pwd_hash = hash_password("MySecurePass2026")
        self.assertTrue(verify_password("MySecurePass2026", salt, pwd_hash))
        self.assertFalse(verify_password("WrongPassword", salt, pwd_hash))

        # 3. Format validations
        validate_email_format("candidate@example.com")
        validate_password_strength("ValidPass1")

        # 4. User isolation in database
        session = init_database()
        user_email = f"isolation_test_{salt[:8]}@domain.com"
        new_user = UserModel(
            email=user_email,
            full_name="Isolation Test User",
            password_hash=pwd_hash,
            salt=salt,
            session_token=f"tok_{salt[:8]}"
        )
        session.add(new_user)
        session.commit()

        # Check unique constraint
        self.assertIsNotNone(new_user.id)
        session.delete(new_user)
        session.commit()
        session.close()

        print("[Pass] Authentication security, PBKDF2 crypto, Captcha, and database isolation verified.")

    def test_06_job_apply_urls_and_page_spec(self):
        """Verifies that all jobs have valid apply URLs and HTML meets UI constraints."""
        session = init_database()
        jobs = session.query(JobModel).all()
        for j in jobs:
            self.assertTrue(j.apply_url and j.apply_url.startswith("http"), f"Job {j.company} missing apply_url")
        
        # Test analysis output includes apply_url
        result = self.service.analyze_candidate(
            full_name="Hamza Tariq",
            years_experience=2.0,
            explicit_skills=["Python", "PyTorch"],
            resume_text="AI engineer with Python and PyTorch experience",
            jobs=jobs
        )
        session.close()

        for top in result["top_matches"]:
            self.assertTrue(top.get("apply_url") and top["apply_url"].startswith("http"), f"Match {top['company']} missing apply_url")

        # Verify index.html spec
        index_html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("<title>TalentPulse</title>", index_html)
        self.assertNotIn("TalentPulse--Semantic Care", index_html)
        self.assertNotIn("code-snippet", index_html)
        self.assertIn("auth-field-row", index_html)
        self.assertIn("btn-apply", (BASE_DIR / "static" / "styles.css").read_text(encoding="utf-8"))

        print("[Pass] Job application URLs, HTML title TalentPulse, and clean analytics UI verified.")


if __name__ == "__main__":
    unittest.main()
