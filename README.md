# TalentPulse AI — Siamese Career Matcher & Skill-Gap Diagnosis Engine

> **A production-grade Deep Learning & Data Science platform built with PyTorch, FastAPI, SQLite, and an editorial Claude/Gemini-inspired interface.**

[![Python](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.14%20CPU%2FCUDA-red.svg)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-teal.svg)](https://fastapi.tiangolo.com)
[![Database](https://img.shields.io/badge/Database-SQLite%20%7C%20SQLAlchemy-lightgrey.svg)](https://sqlite.org)
[![PyCharm](https://img.shields.io/badge/IDE-PyCharm%20Ready-green.svg)](https://jetbrains.com/pycharm/)

---

## 1. Executive Summary

Traditional Applicant Tracking Systems (ATS) rely on brittle keyword matching that frequently rejects qualified candidates and fails to quantify semantic suitability. **TalentPulse AI** solves this problem by training a custom **PyTorch Asymmetric Dual-Encoder (Siamese Neural Network)** that projects candidate profiles and job descriptions into a shared hyperspherical metric latent space $\mathbb{R}^{64}$.

The platform computes calibrated suitability scores, measures vector cosine alignments, isolates missing critical competencies, and delivers tailored upskilling roadmaps aligned with the top software houses in Pakistan (**Systems Limited, Devsinc, 10Pearls, Arbisoft, VentureDive, Motive**) as well as remote international roles.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Data & Feature Pipeline
        RAW["Raw Job Data & Skills Taxonomy"] --> TOK["SkillTokenizer (NLP Extraction)"]
        RES["Candidate Resume & Profile"] --> TOK
        TOK --> FEAT_C["Candidate Feature Vector (70-D)"]
        TOK --> FEAT_J["Job Feature Vector (70-D)"]
    end

    subgraph PyTorch Deep Learning Core
        FEAT_C --> ENC_C["TowerEncoder: Candidate (Residual Dense + LayerNorm)"]
        FEAT_J --> ENC_J["TowerEncoder: Job (Residual Dense + LayerNorm)"]
        ENC_C --> L2_C["L2 Hypersphere Normalization (u)"]
        ENC_J --> L2_J["L2 Hypersphere Normalization (v)"]
        L2_C & L2_J --> INTERACT["Feature Interaction: [u || v || |u - v| || u ⊙ v]"]
        INTERACT --> HEAD["Calibrated Scoring Head (MLP + Sigmoid)"]
        HEAD --> SCORE["Suitability Score [0 - 100]"]
        L2_C & L2_J --> COS["Cosine Alignment Metric"]
    end

    subgraph Production Backend & Storage
        SCORE & COS --> SVC["CareerMatchingService"]
        SVC --> DB[("SQLite Database via SQLAlchemy")]
        SVC --> API["FastAPI Async REST Endpoints"]
    end

    subgraph User Experience
        API --> UI["Claude/Gemini-styled Minimalist Web App"]
    end
```

---

## 3. Key Machine Learning & Data Science Highlights

1. **Custom PyTorch Model (`model/architecture.py`)**:
   - Asymmetric Dual-Tower Encoders with `ResidualDenseBlock` layers, `LayerNorm`, and `GELU` non-linearities.
   - Hyperspherical $L_2$ Normalization ensuring that dot products equal cosine similarities.
   - Rich cross-tower interaction features: concatenation of representation vectors $u, v$, absolute difference $|u - v|$, and element-wise Hadamard product $u \odot v$.
   - **Dual-Objective Loss Function**:
     $$\mathcal{L}_{total} = 0.35 \cdot \mathcal{L}_{cosine}(u, v, y_{sim}) + 0.65 \cdot \mathcal{L}_{SmoothL1}(\hat{s}, s)$$
     Pulls genuine matches together in metric space while calibrating regression score percentages.

2. **Data Science & Validation (`model/train.py`)**:
   - Synthesizes market distributions across experience brackets (junior grads from FAST/NUST/LUMS, mid-level RAG engineers, senior deep learning architects).
   - 80/20 train/validation split with learning rate annealing (`CosineAnnealingLR`).
   - Achieves **5.67% Validation Mean Absolute Error (MAE)** and **0.950 Pearson Correlation**.

3. **Database Layer (`backend/database.py`)**:
   - SQLite backed by SQLAlchemy 2.0 ORM with relational integrity.
   - Structured schemas for `JobModel`, `CandidateProfileModel`, and `MatchHistoryModel`.

4. **Claude / Gemini Editorial Design System (`static/`)**:
   - Warm neutral color scheme (`#FAF9F5`, `#FAF8F5`, `#E8E6DF`) with Claude's signature terracotta accent (`#D97757`).
   - Clean, uncluttered layout with zero AI tropes (no neon gradients, no tacky glowing badges).
   - One-click demo profiles ("Junior Grad", "Generative AI / RAG", "Senior Deep Learning").

---

## 4. PyCharm Setup Guide

The project is structured to be turnkey in **PyCharm**:

1. **Open the Project in PyCharm**:
   - Launch PyCharm $\to$ **Open** $\to$ select `/home/kali/Projects/talentpulse-ai`.
2. **Configure Python Interpreter**:
   - Go to **Settings / Preferences** $\to$ **Project: talentpulse-ai** $\to$ **Python Interpreter**.
   - Select **Existing environment** $\to$ browse to:
     ```
     /home/kali/Projects/talentpulse-ai/venv/bin/python
     ```
3. **Pre-configured Run Configurations**:
   - The `.idea/runConfigurations/` folder is already committed with:
     - `Run TalentPulse AI` (Starts the FastAPI server)
     - `Train PyTorch Model` (Runs PyTorch training & generates weights)
     - `Run Test Suite` (Executes the test suite)
   - Simply select any configuration from the top right run dropdown and press **Shift + F10** (Run).

---

## 5. Quickstart via Terminal

```bash
cd /home/kali/Projects/talentpulse-ai

# Make executable and launch (automatically uses the venv)
./run.sh
```

Or run manually:
```bash
# 1. Activate environment
source venv/bin/activate

# 2. Run system tests
python test_system.py

# 3. Start the application
python main.py
```

Open your browser at **http://127.0.0.1:8000** to access the Claude/Gemini-styled interface.

---

## 6. How to Talk About This in an AI Engineer Interview (Pakistan & Remote)

When interviewers at **Systems Ltd, 10Pearls, Arbisoft, Devsinc**, or US remote startups ask you about your hands-on AI projects, use this framework:

| Interview Question | How TalentPulse AI Answers It |
| :--- | :--- |
| *"Why didn't you just use an LLM API for matching?"* | *"LLM prompting for batch candidate ranking is non-deterministic, introduces high latency (1-3s per pair), and costs scale linearly. By training an asymmetric dual-encoder in PyTorch, inference takes under 5ms, embeddings can be precomputed and indexed, and the metric space is mathematically grounded with cosine distance."* |
| *"Explain your loss function formulation."* | *"We formulated a composite dual-objective loss. The Cosine Embedding Loss acts as a contrastive metric constraint to cluster suitable candidates on a unit hypersphere, while Smooth L1 loss prevents outlier sensitivity during percentage calibration."* |
| *"How do you handle feature engineering?"* | *"We implemented a domain-specific SkillTokenizer that uses boundary-aware regex to extract technical terms against an NLP taxonomy, combined with normalized experience ratios and skill density indicators."* |
| *"How is this deployed in production?"* | *"The PyTorch model is wrapped in an asynchronous FastAPI service, backed by SQLAlchemy and SQLite for persistence, and can be containerized with Docker or exported to ONNX for production model serving."* |

---

## 7. Project Directory Layout

```
talentpulse-ai/
├── backend/
│   ├── app.py                 # FastAPI application & REST endpoints
│   ├── database.py            # SQLite + SQLAlchemy models
│   ├── schemas.py             # Pydantic request/response validation
│   └── service.py             # PyTorch inference & skill-gap diagnostics
├── model/
│   ├── architecture.py        # PyTorch Siamese Dual-Encoder & Loss function
│   ├── tokenizer.py           # NLP skill extraction & multi-hot vectorizer
│   ├── dataset.py             # PyTorch Dataset, DataLoader & synthesis
│   ├── train.py               # Complete training & validation pipeline
│   └── weights/               # Checkpoint (.pt) and metrics (.json)
├── data/
│   ├── raw_jobs.json          # Curated tech jobs (Pakistan + Remote)
│   ├── skills_taxonomy.json   # Comprehensive tech skill taxonomy
│   └── talentpulse.db         # SQLite relational database
├── static/
│   ├── index.html             # Claude/Gemini-styled layout
│   ├── styles.css             # Refined typography & warm palette
│   └── app.js                 # Dynamic client controller
├── .idea/                     # Turnkey PyCharm project configurations
├── requirements.txt           # Project dependencies
├── test_system.py             # End-to-end unittest suite
├── main.py                    # Root entrypoint
├── run.sh                     # Launch script
└── README.md                  # Complete documentation
```
