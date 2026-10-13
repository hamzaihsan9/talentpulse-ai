"""
PyTorch Training Script for TalentPulse Siamese Dual-Encoder.
Includes validation loop, learning rate scheduling, metric tracking (MAE, MSE, Correlation),
and model serialization for production inference.
"""

import os
import json
import time
from pathlib import Path
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, random_split

from model.tokenizer import SkillTokenizer
from model.architecture import SiameseCareerMatcher, DualObjectiveLoss
from model.dataset import CareerMatchDataset, DataSciencePipeline


def train_pipeline(
    epochs: int = 25,
    batch_size: int = 32,
    lr: float = 0.0015,
    device_str: str = "cpu"
) -> dict:
    device = torch.device(device_str)
    print(f"[Training] Using compute device: {device}")

    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    data_path = base_dir / "data" / "raw_jobs.json"
    weights_dir = base_dir / "model" / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)
    model_save_path = weights_dir / "best_career_matcher.pt"
    metrics_save_path = weights_dir / "train_metrics.json"

    # 1. Load Data & Tokenizer
    with open(data_path, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    tokenizer = SkillTokenizer()
    pipeline = DataSciencePipeline(tokenizer)
    
    print(f"[Data Science] Vocabulary size: {tokenizer.vocab_size} core tech skills")
    print(f"[Data Science] Synthesizing candidate-job pairs from {len(jobs)} market postings...")
    all_pairs = pipeline.generate_pairs_from_jobs(jobs, num_candidates_per_job=180)
    print(f"[Data Science] Generated {len(all_pairs)} diverse candidate pairs for training")

    # 2. Train / Validation Split (80 / 20)
    dataset = CareerMatchDataset(all_pairs)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(42)
    )

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)

    # 3. Model Architecture
    feature_dim = tokenizer.vocab_size + 2  # skills + normalized_exp + density
    model = SiameseCareerMatcher(feature_dim=feature_dim, hidden_dim=128, embed_dim=64).to(device)
    
    criterion = DualObjectiveLoss(alpha=0.35, margin=0.25)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    # Tracking History
    history = {
        "epochs": [],
        "train_loss": [],
        "val_loss": [],
        "val_mae": [],
        "val_r2": [],
        "feature_dim": feature_dim,
        "vocab_size": tokenizer.vocab_size,
        "sample_count": len(all_pairs),
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    best_val_loss = float("inf")
    print("\n--- Starting PyTorch Deep Learning Training Loop ---")
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        # Training Phase
        model.train()
        train_running_loss = 0.0

        for batch in train_loader:
            cand_x = batch["cand_features"].to(device)
            job_x = batch["job_features"].to(device)
            target = batch["target_score"].to(device)

            optimizer.zero_grad()
            cand_emb, job_emb, pred_scores = model(cand_x, job_x)
            loss_dict = criterion(cand_emb, job_emb, pred_scores, target)
            loss = loss_dict["total_loss"]
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_running_loss += loss.item() * cand_x.size(0)

        scheduler.step()
        train_epoch_loss = train_running_loss / len(train_set)

        # Validation Phase
        model.eval()
        val_running_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for batch in val_loader:
                cand_x = batch["cand_features"].to(device)
                job_x = batch["job_features"].to(device)
                target = batch["target_score"].to(device)

                cand_emb, job_emb, pred_scores = model(cand_x, job_x)
                loss_dict = criterion(cand_emb, job_emb, pred_scores, target)
                
                val_running_loss += loss_dict["total_loss"].item() * cand_x.size(0)
                all_preds.extend(pred_scores.cpu().squeeze(-1).numpy().tolist())
                all_targets.extend(target.cpu().squeeze(-1).numpy().tolist())

        val_epoch_loss = val_running_loss / len(val_set)
        
        # Compute Data Science Evaluation Metrics: MAE & Correlation
        preds_arr = np.array(all_preds)
        targets_arr = np.array(all_targets)
        mae = float(np.mean(np.abs(preds_arr - targets_arr)))
        correlation = float(np.corrcoef(preds_arr, targets_arr)[0, 1])

        history["epochs"].append(epoch)
        history["train_loss"].append(round(train_epoch_loss, 4))
        history["val_loss"].append(round(val_epoch_loss, 4))
        history["val_mae"].append(round(mae, 2))
        history["val_r2"].append(round(correlation, 4))

        if epoch % 5 == 0 or epoch == 1 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs:02d}] | Train Loss: {train_epoch_loss:.4f} | Val Loss: {val_epoch_loss:.4f} | Val MAE: {mae:.2f}% | Correlation: {correlation:.3f}")

        # Save Best Model Checkpoint
        if val_epoch_loss < best_val_loss:
            best_val_loss = val_epoch_loss
            torch.save({
                "model_state_dict": model.state_dict(),
                "feature_dim": feature_dim,
                "hidden_dim": 128,
                "embed_dim": 64,
                "best_val_loss": best_val_loss,
                "epoch": epoch
            }, model_save_path)

    total_time = time.time() - start_time
    history["training_time_seconds"] = round(total_time, 2)
    history["best_val_loss"] = round(best_val_loss, 4)

    # Save metrics report
    with open(metrics_save_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print(f"\n[Completed] Model saved to {model_save_path}")
    print(f"[Completed] Metrics summary saved to {metrics_save_path} in {total_time:.2f}s")
    return history


if __name__ == "__main__":
    train_pipeline(epochs=25, batch_size=32)
