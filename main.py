"""
TalentPulse AI — Application Entry Point.
Launches the FastAPI server with Uvicorn.
Can be directly executed via PyCharm (Right-Click -> Run 'main') or terminal (python main.py).
"""

import sys
import uvicorn
from pathlib import Path

# Ensure root project directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    print("=" * 65)
    print("  TalentPulse AI — Siamese Career Matcher & Skill Diagnostics")
    print("  Production AI Engineering Showcase")
    print("=" * 65)
    print(f"  Project Root: {BASE_DIR}")
    print("  Starting Server at: http://127.0.0.1:8000")
    print("=" * 65)

    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
