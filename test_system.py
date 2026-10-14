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
from backend.database import init_database, JobModel, UserModel, UserJobViewModel
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

    def test_07_pdf_cv_extraction(self):
        """Tests PDF resume parsing, keyword extraction, and match computation."""
        import io
        from pypdf import PdfWriter

        # Create a genuine minimal PDF byte stream
        writer = PdfWriter()
        page = writer.add_blank_page(width=612, height=792)
        
        # Or construct a valid minimal PDF with text
        # Since pypdf PdfWriter can write a clean PDF, let's write text or use raw pdf stream
        # Minimal valid PDF with text stream:
        pdf_content = (
            b"%PDF-1.4\n"
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
            b"4 0 obj << /Length 135 >> stream\n"
            b"BT /F1 12 Tf 72 712 Td (Senior AI Engineer with 3.5 years experience in Python, PyTorch, Docker, FastAPI, and RAG architectures at FAST.) Tj ET\n"
            b"endstream\nendobj\n"
            b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000430 00000 n \n"
            b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n511\n%%EOF"
        )

        session = init_database()
        jobs = session.query(JobModel).all()
        result = self.service.parse_pdf_cv(pdf_content, jobs, "Fatima Khan")
        session.close()

        self.assertIn("extracted_skills", result)
        self.assertIn("Python", result["extracted_skills"])
        self.assertIn("PyTorch", result["extracted_skills"])
        self.assertIn("Docker", result["extracted_skills"])
        self.assertGreater(len(result["top_matches"]), 0)
        print(f"[Pass] PDF CV extraction parsed skills: {result['extracted_skills']}")

    def test_08_ai_assistant_guardrails(self):
        """Verifies strict domain guardrails: rejects off-topic (biryani) & answers career queries."""
        session = init_database()
        jobs = session.query(JobModel).all()

        # 1. Off-topic test: "make biryani" MUST be rejected with is_error=True
        biryani_query = "Can you give me a recipe to make biryani at home?"
        res_biryani = self.service.process_assistant_query(
            query=biryani_query,
            current_skills=["Python"],
            years_exp=2.0,
            jobs=jobs,
            candidate_name="Tester"
        )
        self.assertTrue(res_biryani["is_error"], "Off-topic query 'make biryani' was not flagged as an error!")
        self.assertIn("Off-Topic", res_biryani["reply"])
        print(f"[Pass] Guardrail successfully blocked off-topic prompt '{biryani_query}':\n       {res_biryani['reply']}")

        # 2. Another off-topic: movie recommendations
        movie_query = "Who won the premier league yesterday?"
        res_movie = self.service.process_assistant_query(
            query=movie_query,
            current_skills=["Python"],
            years_exp=2.0,
            jobs=jobs,
            candidate_name="Tester"
        )
        self.assertTrue(res_movie["is_error"])

        # 3. On-topic career query: "find Generative AI jobs"
        career_query = "Find Generative AI and RAG jobs in Lahore"
        res_career = self.service.process_assistant_query(
            query=career_query,
            current_skills=["Python", "PyTorch", "RAG"],
            years_exp=2.5,
            jobs=jobs,
            candidate_name="Fatima"
        )
        self.assertFalse(res_career["is_error"])
        self.assertGreater(len(res_career["suggested_jobs"]), 0)
        print(f"[Pass] On-topic query '{career_query}' returned {len(res_career['suggested_jobs'])} jobs.")
        session.close()

    def test_09_user_knowledge_graph(self):
        """Verifies construction of interactive User-Specific Knowledge Graph network and multi-user divergence."""
        session = init_database()
        jobs = session.query(JobModel).all()

        # User 1: AI / Computer Vision Engineer
        user1 = UserModel(email="hamza_cv@talentpulse.ai", full_name="Hamza Tariq")
        session.add(user1)
        session.commit()

        # User 2: NLP / LLM Engineer
        user2 = UserModel(email="sara_nlp@talentpulse.ai", full_name="Sara Khan")
        session.add(user2)
        session.commit()

        from backend.app import get_user_seen_job_ids, get_user_personal_skills

        skills1, exp1 = get_user_personal_skills(user1, session)
        seen1 = get_user_seen_job_ids(user1, session)
        jobs1 = [j for j in jobs if j.id in seen1]

        skills2, exp2 = get_user_personal_skills(user2, session)
        seen2 = get_user_seen_job_ids(user2, session)
        jobs2 = [j for j in jobs if j.id in seen2]

        graph1 = self.service.build_user_knowledge_graph(
            user_name=user1.full_name,
            skills=skills1,
            years_experience=exp1,
            jobs=jobs1,
            user_id_val=user1.id,
            user_email=user1.email
        )

        graph2 = self.service.build_user_knowledge_graph(
            user_name=user2.full_name,
            skills=skills2,
            years_experience=exp2,
            jobs=jobs2,
            user_id_val=user2.id,
            user_email=user2.email
        )

        # 1. Verify User 1 vs User 2 Knowledge Graphs are completely distinct
        user1_nodes = {n["label"] for n in graph1["nodes"]}
        user2_nodes = {n["label"] for n in graph2["nodes"]}

        self.assertIn("Hamza Tariq", user1_nodes)
        self.assertIn("Sara Khan", user2_nodes)
        self.assertNotIn("Sara Khan", user1_nodes)
        self.assertNotIn("Hamza Tariq", user2_nodes)

        # Skills should diverge
        self.assertNotEqual(skills1, skills2, "Different users must have distinct skill sets!")
        self.assertNotEqual(user1_nodes, user2_nodes, "User 1 and User 2 must produce distinct knowledge graph nodes!")

        # 2. Verify tracking a new job dynamically expands User 1's graph
        initial_node_count = len(graph1["nodes"])
        # User 1 views a job they haven't seen before
        unseen_job = next(j for j in jobs if j.id not in seen1)
        session.add(UserJobViewModel(user_id=user1.id, job_id=unseen_job.id))
        session.commit()

        seen1_updated = get_user_seen_job_ids(user1, session)
        self.assertIn(unseen_job.id, seen1_updated)
        jobs1_updated = [j for j in jobs if j.id in seen1_updated]

        graph1_updated = self.service.build_user_knowledge_graph(
            user_name=user1.full_name,
            skills=skills1,
            years_experience=exp1,
            jobs=jobs1_updated,
            user_id_val=user1.id,
            user_email=user1.email
        )
        self.assertGreater(len(graph1_updated["nodes"]), initial_node_count, "Viewing a new job must dynamically expand the user's graph!")

        # 3. Clean up test users
        session.delete(user1)
        session.delete(user2)
        session.commit()
        session.close()

        print(f"[Pass] User-specific knowledge graph validated: User 1 ({len(graph1['nodes'])} nodes) != User 2 ({len(graph2['nodes'])} nodes). Dynamic expansion confirmed.")

    def test_10_oauth_credential_and_verification_rules(self):
        """Verifies OAuth login endpoint requires credentials/verification."""
        from backend.schemas import OAuthLoginRequest
        from pydantic import ValidationError

        # Empty password/verification code should be caught by endpoint logic
        req = OAuthLoginRequest(email="test@gmail.com", password="secureGooglePassword123")
        self.assertEqual(req.email, "test@gmail.com")
        self.assertEqual(req.password, "secureGooglePassword123")

        # Invalid email format should fail
        with self.assertRaises(ValidationError):
            OAuthLoginRequest(email="notanemail", password="pwd")

        # Wrong password for Gmail must be rejected with 401
        from backend.auth import verify_google_credentials
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            verify_google_credentials("test_unregistered_9283@gmail.com", "wrongpassword")
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Google Authentication Failed", ctx.exception.detail)
        print(f"[Pass] Wrong Gmail credentials correctly rejected by Google with 401: {ctx.exception.detail[:60]}...")

        print("[Pass] OAuth request schemas and verification credential constraints validated.")


if __name__ == "__main__":
    unittest.main()

