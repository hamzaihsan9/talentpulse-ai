"""
Dual-Encoder Siamese Neural Network for Candidate-Job Semantic Matching.
Built with PyTorch.

Architecture Highlights:
- Asymmetric Dual-Tower Encoders with Residual Projections
- L2 Hyperspherical Normalization for Metric Learning
- Bilinear & Hadamard Interaction Head for Granular Score Calibration
- Combined Metric-Rank Loss (Cosine Embedding Loss + Smooth L1)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Dict


class ResidualDenseBlock(nn.Module):
    """Residual dense block with LayerNorm and GELU non-linearity."""
    def __init__(self, dim: int, dropout: float = 0.15):
        super().__init__()
        self.fc1 = nn.Linear(dim, dim)
        self.norm1 = nn.LayerNorm(dim)
        self.fc2 = nn.Linear(dim, dim)
        self.norm2 = nn.LayerNorm(dim)
        self.dropout = nn.Dropout(dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        out = self.act(self.norm1(self.fc1(x)))
        out = self.dropout(out)
        out = self.norm2(self.fc2(out))
        return self.act(out + residual)


class TowerEncoder(nn.Module):
    """
    Encoder tower that projects sparse/dense multi-hot candidate or job features
    into a continuous metric latent space.
    """
    def __init__(self, input_dim: int, hidden_dim: int = 128, embed_dim: int = 64, dropout: float = 0.15):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout)
        )
        self.res_block = ResidualDenseBlock(hidden_dim, dropout=dropout)
        self.head = nn.Linear(hidden_dim, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(x)
        h = self.res_block(h)
        embed = self.head(h)
        # Project onto unit hypersphere (L2 normalization)
        return F.normalize(embed, p=2, dim=-1)


class SiameseCareerMatcher(nn.Module):
    """
    End-to-End Dual-Encoder Architecture for Candidate vs Job Suitability.
    Produces both latent embeddings (for vector search) and calibrated match scores.
    """
    def __init__(self, feature_dim: int, hidden_dim: int = 128, embed_dim: int = 64):
        super().__init__()
        self.candidate_encoder = TowerEncoder(feature_dim, hidden_dim, embed_dim)
        self.job_encoder = TowerEncoder(feature_dim, hidden_dim, embed_dim)
        
        # Interaction feature dimension: [u, v, |u - v|, u * v] -> 4 * embed_dim
        interaction_dim = embed_dim * 4
        self.score_head = nn.Sequential(
            nn.Linear(interaction_dim, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )

    def forward(self, cand_features: torch.Tensor, job_features: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Returns:
            cand_embed: (Batch, embed_dim) - normalized embedding
            job_embed: (Batch, embed_dim) - normalized embedding
            match_score: (Batch, 1) - calibrated score scaled [0, 100]
        """
        cand_embed = self.candidate_encoder(cand_features)
        job_embed = self.job_encoder(job_features)
        
        # Compute rich feature interactions
        diff = torch.abs(cand_embed - job_embed)
        hadamard = cand_embed * job_embed
        interaction = torch.cat([cand_embed, job_embed, diff, hadamard], dim=-1)
        
        # Output calibrated score from 0 to 100
        score = self.score_head(interaction) * 100.0
        return cand_embed, job_embed, score

    def encode_candidate(self, cand_features: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            return self.candidate_encoder(cand_features)

    def encode_job(self, job_features: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            return self.job_encoder(job_features)


class DualObjectiveLoss(nn.Module):
    """
    Dual Objective:
    1. Cosine Embedding Loss pushes non-matches apart and pulls matches together.
    2. Smooth L1 Loss ensures predicted match percentage is well-calibrated.
    """
    def __init__(self, alpha: float = 0.4, margin: float = 0.2):
        super().__init__()
        self.alpha = alpha
        self.cosine_loss = nn.CosineEmbeddingLoss(margin=margin)
        self.regression_loss = nn.SmoothL1Loss()

    def forward(self, cand_embed: torch.Tensor, job_embed: torch.Tensor, 
                pred_scores: torch.Tensor, target_scores: torch.Tensor) -> Dict[str, torch.Tensor]:
        # Target for cosine embedding loss: +1 for high matches (score >= 60), -1 for low matches
        sim_target = torch.where(target_scores >= 60.0, 1.0, -1.0).squeeze(-1)
        
        loss_cos = self.cosine_loss(cand_embed, job_embed, sim_target)
        loss_reg = self.regression_loss(pred_scores.squeeze(-1) / 100.0, target_scores.squeeze(-1) / 100.0)
        
        total_loss = self.alpha * loss_cos + (1.0 - self.alpha) * loss_reg
        return {
            "total_loss": total_loss,
            "cosine_loss": loss_cos,
            "regression_loss": loss_reg
        }
