"""Initialize the database. Run from server/ with venv activated:
    cd server && python ../scripts/init_db.py
"""
import sys
from pathlib import Path

# Allow running from project root or server/
ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
sys.path.insert(0, str(SERVER))

from app.db import init_db
from app.db.session import engine
from app.db.base import Base
from app.config import settings


def main():
    print(f"Initializing DB at: {settings.db_path}")
    settings.ensure_dirs()
    # Import models so they register with Base
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created.")


if __name__ == "__main__":
    main()
