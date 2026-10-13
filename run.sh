#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "================================================================="
echo "  TalentPulse AI — Siamese Career Matcher & Skill Diagnostics   "
echo "================================================================="

if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

if [ ! -f "model/weights/best_career_matcher.pt" ]; then
    echo "[2/3] Training PyTorch Dual-Encoder model..."
    ./venv/bin/python -m model.train
else
    echo "[2/3] Found existing PyTorch model weights at model/weights/best_career_matcher.pt"
fi

echo "[3/3] Starting TalentPulse AI server on http://127.0.0.1:8000 ..."
./venv/bin/python main.py
