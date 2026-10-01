"""Load backend-local environment defaults; shell variables always take precedence."""
import os
from pathlib import Path


def load_environment(path=None):
    path = path or Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        return
    # Deliberately simple dotenv format: NAME=value or quoted value, no interpolation.
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip()
        if name not in {"ADZUNA_APP_ID", "ADZUNA_APP_KEY", "SEED_DEMO", "DATABASE_URL", "UPLOAD_DIR", "CORS_ORIGINS"}:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {chr(34), chr(39)}:
            value = value[1:-1]
        os.environ.setdefault(name, value)


load_environment()
