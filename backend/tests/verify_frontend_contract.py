"""Check documented routes and JSON examples without accessing the working database."""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
with tempfile.TemporaryDirectory(prefix="campuslink-contract-") as tmp:
    os.environ["DATABASE_URL"] = "sqlite:///" + (Path(tmp) / "verify.db").as_posix()
    from app.main import app
    from app.database import engine
    text = (ROOT / "FRONTEND_API_GUIDE.md").read_text(encoding="utf-8")
    expected = set(re.findall(r"\*\*(GET|POST|PATCH|DELETE) `([^`]+)`\*\*", text))
    expected.update((method, path) for method, path in re.findall(r"\| (GET|POST|PATCH|DELETE) \| `([^`]+)`", text))
    actual = {(method.upper(), path) for path, operations in app.openapi()["paths"].items() for method in operations}
    assert expected <= actual, "Nonexistent documented operations: " + str(expected - actual)
    assert actual <= expected, "Undocumented operations: " + str(actual - expected)
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.S)
    for block in blocks:
        json.loads(block)
    engine.dispose()
    print(f"PASS: All {len(expected)} operations match OpenAPI; all {len(blocks)} JSON examples parse.")
