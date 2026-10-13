"""
Tokenizer and Feature Extraction Engine for TalentPulse AI.
Converts free-text resumes, skill sets, and job postings into numerical representations
suitable for deep neural network consumption and data science analysis.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
import numpy as np


class SkillTokenizer:
    def __init__(self, taxonomy_path: str = None):
        self.skills: List[str] = []
        self.skill_to_idx: Dict[str, int] = {}
        self.idx_to_skill: Dict[int, str] = {}
        self.category_map: Dict[str, str] = {}
        
        if taxonomy_path and Path(taxonomy_path).exists():
            self._load_taxonomy(taxonomy_path)
        else:
            default_path = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"
            if default_path.exists():
                self._load_taxonomy(str(default_path))
            else:
                self._init_default_taxonomy()

    def _load_taxonomy(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        all_skills = []
        for category, skills in data.items():
            for skill in skills:
                skill_norm = skill.strip()
                if skill_norm not in all_skills:
                    all_skills.append(skill_norm)
                self.category_map[skill_norm.lower()] = category
                
        self.skills = sorted(all_skills)
        self.skill_to_idx = {s.lower(): idx for idx, s in enumerate(self.skills)}
        self.idx_to_skill = {idx: s for idx, s in enumerate(self.skills)}

    def _init_default_taxonomy(self):
        core = [
            "PyTorch", "TensorFlow", "Scikit-Learn", "Deep Learning", "Neural Networks",
            "Supervised Learning", "Transformers", "Hugging Face", "BERT", "LLMs",
            "RAG", "LangChain", "Vector Databases", "Embeddings", "Fine-Tuning", "LoRA",
            "OpenCV", "YOLO", "CNN", "Docker", "Kubernetes", "MLflow", "AWS SageMaker",
            "FastAPI", "Python", "SQL", "PostgreSQL", "SQLite", "Pandas", "NumPy", "Git"
        ]
        self.skills = sorted(core)
        self.skill_to_idx = {s.lower(): idx for idx, s in enumerate(self.skills)}
        self.idx_to_skill = {idx: s for idx, s in enumerate(self.skills)}

    @property
    def vocab_size(self) -> int:
        return len(self.skills)

    def extract_skills_from_text(self, text: str) -> List[str]:
        """Identifies skills present in raw text via regex boundary matching."""
        found = []
        text_lower = text.lower()
        for skill in self.skills:
            pattern = r"(?<!\w)" + re.escape(skill.lower()) + r"(?!\w)"
            if re.search(pattern, text_lower):
                found.append(skill)
        return found

    def encode_skills_multi_hot(self, skills_list: List[str]) -> np.ndarray:
        """Converts a list of skills into a multi-hot binary vector."""
        vec = np.zeros(self.vocab_size, dtype=np.float32)
        for s in skills_list:
            s_low = s.strip().lower()
            if s_low in self.skill_to_idx:
                vec[self.skill_to_idx[s_low]] = 1.0
        return vec

    def decode_skills_vector(self, vec: np.ndarray, threshold: float = 0.5) -> List[str]:
        """Decodes multi-hot vector back to human-readable skills."""
        indices = np.where(vec >= threshold)[0]
        return [self.idx_to_skill[int(idx)] for idx in indices]

    def build_dense_profile(self, text: str, explicit_skills: List[str] = None, years_exp: float = 0.0) -> np.ndarray:
        """
        Creates a combined feature vector:
        [multi-hot skills (vocab_size) | normalized years exp (1) | skill count density (1)]
        """
        extracted = self.extract_skills_from_text(text)
        all_skills = list(set(extracted + (explicit_skills or [])))
        skill_vec = self.encode_skills_multi_hot(all_skills)
        
        norm_exp = np.array([min(years_exp, 15.0) / 15.0], dtype=np.float32)
        skill_density = np.array([min(len(all_skills), 30) / 30.0], dtype=np.float32)
        
        return np.concatenate([skill_vec, norm_exp, skill_density])
