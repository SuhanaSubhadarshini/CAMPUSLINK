"""Explicit opt-in, read-only live Adzuna smoke. Never used by pytest."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
parser = argparse.ArgumentParser()
parser.add_argument("--live", action="store_true")
parser.add_argument("--query", default="python developer")
parser.add_argument("--location", default="India")
args = parser.parse_args()
if not args.live:
    parser.error("Pass --live to spend one real provider API request; credentials stay server-side.")
from app import config
from app.services.adzuna_service import search
from fastapi import HTTPException
try:
    data = search(args.query, args.location, 1, 3)
    print("Live Adzuna search succeeded:",len(data["results"]),"usable listings;",data["skipped"],"skipped. No database writes.")
except HTTPException as error:
    print("Live Adzuna search unavailable:",error.status_code,error.detail)
    sys.exit(1)
