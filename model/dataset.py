"""
PyTorch Dataset and Data Generation Pipeline for Candidate-Job Matching.
Includes Data Science routines: Train/Val split, feature normalization, and noise injection.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader

from model.tokenizer import SkillTokenizer


class CareerMatchDataset(Dataset):
    """
    PyTorch Dataset yielding pairs of (candidate_features, job_features, ground_truth_score).
    """
    def __init__(self, samples: List[Dict]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        item = self.samples[idx]
        return {
            "cand_features": torch.tensor(item["cand_features"], dtype=torch.float32),
            "job_features": torch.tensor(item["job_features"], dtype=torch.float32),
            "target_score": torch.tensor([item["target_score"]], dtype=torch.float32)
        }


class DataSciencePipeline:
    """
    Data Science utilities for dataset synthesis, exploratory feature engineering,
    and synthetic candidate-job pair creation reflecting modern market distributions.
    """
    def __init__(self, tokenizer: SkillTokenizer = None):
        self.tokenizer = tokenizer or SkillTokenizer()

    def generate_pairs_from_jobs(self, jobs: List[Dict], num_candidates_per_job: int = 150) -> List[Dict]:
        """
        Synthesizes diverse candidate profiles across various skill profiles:
        - High matches (top talent matching required and preferred skills)
        - Partial matches (transitioning engineers, missing 1-2 core skills)
        - Junior applicants (matching core languages, but lacking specialized frameworks)
        - Mismatched profiles (frontend or unrelated dev applying for ML)
        """
        all_skills = self.tokenizer.skills
        dataset = []

        for job in jobs:
            req = set(s.strip() for s in job.get("required_skills", []))
            pref = set(s.strip() for s in job.get("preferred_skills", []))
            req_years = float(job.get("experience_years", 3.0))
            job_text = f"{job['title']} {job['description']}"
            job_features = self.tokenizer.build_dense_profile(job_text, list(req | pref), req_years)

            for _ in range(num_candidates_per_job):
                cand_type = random.choices(
                    ["expert", "strong", "transition", "junior", "mismatch"],
                    weights=[0.15, 0.35, 0.25, 0.15, 0.10]
                )[0]

                cand_years = 0.0
                cand_skills = set()

                if cand_type == "expert":
                    # Has almost all required + some preferred + extra
                    sampled_req = random.sample(list(req), k=max(1, len(req) - random.randint(0, 1)))
                    sampled_pref = random.sample(list(pref), k=min(len(pref), random.randint(1, len(pref)))) if pref else []
                    cand_skills = set(sampled_req + sampled_pref)
                    cand_years = max(req_years, req_years + random.uniform(0.5, 4.0))

                elif cand_type == "strong":
                    # Has 70-90% of required skills
                    k = max(1, int(len(req) * random.uniform(0.7, 0.9)))
                    cand_skills = set(random.sample(list(req), k=k))
                    cand_years = max(1.0, req_years + random.uniform(-1.0, 1.5))

                elif cand_type == "transition":
                    # Has general programming & foundational math/Python, but missing deep learning frameworks
                    foundation = {"Python", "SQL", "Git", "Pandas", "Scikit-Learn"}
                    cand_skills = set(random.sample(list(foundation), k=min(len(foundation), 3)))
                    if req:
                        cand_skills.add(random.choice(list(req)))
                    cand_years = random.uniform(1.0, 4.0)

                elif cand_type == "junior":
                    # Has basic skills, fresh graduate from FAST-NUCES / NUST / ITU / LUMS in Pakistan
                    cand_skills = {"Python", "NumPy", "Git"}
                    if random.random() > 0.5 and req:
                        cand_skills.add(random.choice(list(req)))
                    cand_years = random.uniform(0.0, 1.0)

                else:  # mismatch
                    unrelated = [s for s in all_skills if s not in req and s not in pref]
                    cand_skills = set(random.sample(unrelated, k=min(len(unrelated), random.randint(2, 5))))
                    cand_years = random.uniform(0.5, 5.0)

                # Add some random exploration skills
                extra = random.sample(all_skills, k=random.randint(0, 3))
                cand_skills.update(extra)

                # Compute rigorous ground-truth score based on weighted criteria
                req_overlap = len(cand_skills & req) / max(1, len(req))
                pref_overlap = len(cand_skills & pref) / max(1, len(pref)) if pref else 0.5
                
                exp_ratio = min(cand_years / max(1.0, req_years), 1.2)
                exp_score = min(1.0, exp_ratio)

                raw_score = (0.55 * req_overlap + 0.25 * pref_overlap + 0.20 * exp_score) * 100.0
                # Add realistic human evaluator variance / noise (+- 4%)
                noise = np.random.normal(0, 2.5)
                calibrated_score = float(np.clip(raw_score + noise, 5.0, 98.0))

                cand_text = f"Experience: {cand_years:.1f} years. Skills: {', '.join(cand_skills)}"
                cand_features = self.tokenizer.build_dense_profile(cand_text, list(cand_skills), cand_years)

                dataset.append({
                    "cand_features": cand_features.tolist(),
                    "job_features": job_features.tolist(),
                    "target_score": calibrated_score,
                    "cand_skills": list(cand_skills),
                    "cand_years": cand_years,
                    "job_id": job.get("id", "job-0"),
                    "match_type": cand_type
                })

        random.shuffle(dataset)
        return dataset
