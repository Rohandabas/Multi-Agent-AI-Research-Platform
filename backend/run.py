"""
Entry point for the Multi-Agent AI Research Platform backend.
Run: python run.py
"""
import os
import sys
import asyncio
import uvicorn
from pathlib import Path

# Ensure the backend directory is in the Python path
sys.path.insert(0, str(Path(__file__).parent))


def create_directories():
    """Create all required output and data directories."""
    dirs = [
        "outputs/reports",
        "outputs/charts",
        "outputs/markdown",
        "outputs/pdf",
        "outputs/docx",
        "outputs/downloads",
        "outputs/logs",
        "data/chroma",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print(f"[*] Output directories created")


def check_env():
    """Validate required environment variables are set."""
    from dotenv import load_dotenv
    load_dotenv()

    required = ["GOOGLE_API_KEY", "TAVILY_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your API keys.")
        sys.exit(1)
    print("[OK] Environment variables validated")


if __name__ == "__main__":
    print("\n=== Starting Multi-Agent AI Research Platform ===\n")
    check_env()
    create_directories()

    from app.database.session import init_db
    asyncio.run(init_db())
    print("[OK] Database initialized")

    print(f"\n[*] Backend running at http://localhost:8000")
    print(f"[*] API docs at http://localhost:8000/docs\n")

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
