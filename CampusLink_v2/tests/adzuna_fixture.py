"""Test-only provider fixture; production never reads this module."""
import os,runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"backend"))
os.environ["ADZUNA_APP_ID"]="browser-test-id"
os.environ["ADZUNA_APP_KEY"]="browser-test-key"
from app.services import adzuna_service

def fetch(params):
    import time
    time.sleep(0.75)
    return {"count":1,"results":[{"id":"browser-external-1","title":"Fixture Python Engineer",
      "company":{"display_name":"External Test Company"},"location":{"display_name":"Bengaluru"},
      "description":"Python SQL FastAPI Docker", "created":"2026-09-20T10:00:00Z",
      "redirect_url":"https://www.adzuna.in/land/ad/browser-external-1?utm_source=browser-test-id&v=provider-token",
      "contract_time":"full_time","category":{"label":"IT Jobs"}}]}
adzuna_service._fetch=fetch
runpy.run_path(str(Path(__file__).with_name("api_fixture.py")),run_name="__main__")
