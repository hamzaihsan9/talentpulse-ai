"""
TalentPulse AI — Application Entry Point.
Launches the FastAPI server with Uvicorn.
Can be directly executed via PyCharm (Right-Click -> Run 'main') or terminal (python main.py).
"""

import os
import sys
import uvicorn
from pathlib import Path

# Ensure root project directory is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main():
    if "--init-only" in sys.argv:
        from backend.database import init_database
        print("Initializing database and models...")
        db = init_database()
        db.close()
        print("Initialization completed successfully.")
        return

    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")

    print("=" * 65)
    print("  TalentPulse AI — Siamese Career Matcher & Skill Diagnostics")
    print("  Production AI Engineering Showcase")
    print("=" * 65)
    print(f"  Project Root: {BASE_DIR}")
    print(f"  Starting Server at: http://{host}:{port}")
    print("=" * 65)

    uvicorn.run(
        "backend.app:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
