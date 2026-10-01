import json
import logging
from urllib.error import HTTPError, URLError
import pytest
from app.services import adzuna_service as service

P = "/api/v1"
RAW = {"id": "provider-123", "title": "<b>Python Developer</b>",
       "company": {"display_name": "  Research   Systems "}, "location": {"display_name": "Bengaluru"},
       "description": "Python, SQL, FastAPI and PyTorch. Familiarity with Docker is useful.",
       "created": "2026-09-20T10:30:00Z", "contract_type": "permanent", "contract_time": "full_time",
       "category": {"label": "IT Jobs"}, "redirect_url": "https://www.adzuna.in/land/ad/provider-123"}


@pytest.fixture(autouse=True)
def isolate_provider(monkeypatch):
    service._cache.clear()
    monkeypatch.setattr(service, "_next_request", 0)
    monkeypatch.setenv("ADZUNA_APP_ID", "unit-test-app-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "unit-test-secret")
    def no_network(params):
        raise AssertionError("Tests must mock Adzuna; real network access is prohibited")
    monkeypatch.setattr(service, "_fetch", no_network)


def search(client, monkeypatch, raw=None):
    monkeypatch.setattr(service, "_fetch", lambda params: {"results": [RAW if raw is None else raw], "count": 1})
    response = client.get(P + "/opportunities/external/adzuna?query=python&location=Bengaluru&limit=5")
    assert response.status_code == 200
    return response.json()


def import_body(data):
    return {"search_token": data["search_token"], "references": [x["source_reference"] for x in data["results"]]}


def test_missing_configuration(client, monkeypatch):
    monkeypatch.setenv("ADZUNA_APP_KEY", "")
    response = client.get(P + "/opportunities/external/adzuna")
    assert response.status_code == 503 and "not configured" in response.json()["detail"]
    assert len(client.get(P + "/opportunities").json()) == 6


def test_normalization_cache_no_search_writes(client, monkeypatch):
    calls = []
    def fetch(params):
        calls.append(params)
        return {"results": [RAW, {"id": "bad"}, RAW, None], "count": 4}
    monkeypatch.setattr(service, "_fetch", fetch)
    url = P + "/opportunities/external/adzuna?query=python&location=Bengaluru&limit=5"
    data = client.get(url).json()
    assert data["stored"] is False and data["skipped"] == 3
    row = data["results"][0]
    assert row["title"] == "Python Developer" and row["company_name"] == "Research Systems"
    assert row["source"] == "adzuna" and row["source_reference"] == "in:provider-123"
    assert row["source_url"] == RAW["redirect_url"] and row["vacancy_count"] is None
    assert row["required_skills"] == [] and "PyTorch" in row["preferred_skills"]
    assert row["external_metadata"]["posted_at"] and row["external_metadata"]["category"] == "IT Jobs"
    assert row["job_type"] == "full-time"
    assert len(client.get(P + "/opportunities").json()) == 6
    assert client.get(url).json()["cached"] and len(calls) == 1
    assert calls[0]["what"] == "python" and calls[0]["where"] == "Bengaluru"
    assert client.get(P + "/opportunities/external/adzuna?query=other").status_code == 429


def test_upsert_and_existing_lifecycle_survives(client, monkeypatch):
    existing_company = client.post(P + "/companies", json={"name": "research systems", "description": "Keep this"}).json()
    data = search(client, monkeypatch)
    imported = client.post(P + "/opportunities/import/adzuna", json=import_body(data))
    assert imported.status_code == 200
    result = imported.json()
    job = result["opportunities"][0]
    assert result["created"] == 1 and job["company_id"] == existing_company["id"]
    assert job["external_metadata"]["fetched_at"] and job["created_at"]
    jid = job["id"]
    query = f"?student_id=1&job_id={jid}"
    assert client.get(P + "/matching/eligibility"+query).json()["status"] == "UNVERIFIED"
    assert client.get(P + "/matching/fit"+query).json()["explanation"]["components"]["skills"]["weight_percent"] == 45
    assert "PyTorch".casefold() in [s.casefold() for s in client.get(P + "/matching/skill-gap"+query).json()["missing_preferred_skills"]]
    assert client.post(P + "/applications", json={"student_id": 1, "job_id": jid}).status_code == 409
    # Historical applications remain intact after the verification upgrade.
    from app.database import SessionLocal
    from app.models import Application
    with SessionLocal() as db:
        historical = Application(student_id=1, job_id=jid)
        db.add(historical)
        db.commit()
        application = {"id": historical.id}
    placement = client.post(P + "/placements", json={"student_id": 1, "job_id": jid, "company_id": job["company_id"]}).json()
    client.patch(P + f"/jobs/{jid}", json={"status": "closed", "required_skills": ["Python"]})
    # A company spelling change must not reassign a historical offer or duplicate its job.
    for entry in service._cache.values():
        entry["response"]["results"][0]["company_name"] = "Changed Source Name"
        entry["response"]["results"][0]["title"] = "Updated Python Developer"
    second = client.post(P + "/opportunities/import/adzuna", json=import_body(data)).json()
    saved = second["opportunities"][0]
    assert second["updated"] == 1 and second["created"] == 0 and saved["id"] == jid
    assert saved["status"] == "closed" and saved["required_skills"] == ["Python"]
    assert saved["company_id"] == job["company_id"] and saved["title"] == "Updated Python Developer"
    assert len(client.get(P + "/jobs").json()) == 7
    assert client.get(P + f"/companies/{job['company_id']}").json()["description"] == "Keep this"
    stored_app = client.get(P + "/applications").json()[0]
    assert stored_app["id"] == application["id"] and stored_app["placement_id"] == placement["id"]
    assert client.get(P + "/matching/fit?student_id=1&job_id=1").json()["overall_fit_score"] == 90.6
    assert len(client.get(P + "/opportunities?source=demo").json()) == 6


@pytest.mark.parametrize("error,status", [(HTTPError("https://api.adzuna.com/?app_key=unit-test-secret", c, "unit-test-secret", {}, None), s) for c,s in [(401,503),(403,503),(429,429),(500,502),(400,502)]] + [(TimeoutError("unit-test-secret"),504),(URLError("unit-test-secret"),504),(ValueError("unit-test-secret"),502)])
def test_safe_provider_errors(client, monkeypatch, caplog, error, status):
    def fail(params):
        raise error
    monkeypatch.setattr(service, "_fetch", fail)
    with caplog.at_level(logging.DEBUG):
        response = client.get(P + "/opportunities/external/adzuna")
    assert response.status_code == status
    for secret in ["unit-test-secret", "unit-test-app-id"]:
        assert secret not in response.text and secret not in caplog.text


def test_untrusted_records_and_expired_selection(client, monkeypatch):
    data = search(client, monkeypatch, dict(RAW, description="unit-test-secret"))
    assert data["results"] == [] and data["skipped"] == 1
    service._cache.clear();monkeypatch.setattr(service, "_next_request", 0)
    data = search(client, monkeypatch, dict(RAW, redirect_url="javascript:alert(1)"))
    assert data["results"] == []
    service._cache.clear();monkeypatch.setattr(service, "_next_request", 0)
    data = search(client, monkeypatch)
    assert client.post(P + "/opportunities/import/adzuna", json={"search_token": data["search_token"], "references": ["forged"]}).status_code == 422
    service._cache.clear()
    assert client.post(P + "/opportunities/import/adzuna", json=import_body(data)).status_code == 409
    assert len(client.get(P + "/companies").json()) == 4


def test_unknown_fields_are_not_invented(client, monkeypatch):
    raw = {k:v for k,v in RAW.items() if k not in {"created", "contract_type", "contract_time", "category", "location", "description"}}
    data = search(client, monkeypatch, raw)
    row = data["results"][0]
    assert row["job_type"] == "unknown" and row["vacancy_count"] is None
    assert row["location"] == "" and row["salary_stipend"] == ""
    assert row["external_metadata"]["posted_at"] is None
    assert row["preferred_skills"] == [] and row["required_skills"] == []


def test_tracking_id_is_removed_without_losing_destination(client, monkeypatch):
    raw = dict(RAW, redirect_url=RAW["redirect_url"]+"?v=provider-token&utm_source=unit-test-app-id&utm_medium=api")
    data = search(client, monkeypatch, raw)
    row = data["results"][0]
    assert row["source_url"] == RAW["redirect_url"]+"?v=provider-token&utm_medium=api"
    assert row["external_metadata"]["credential_tracking_removed"] is True
    imported = client.post(P + "/opportunities/import/adzuna", json=import_body(data))
    assert imported.status_code == 200
    for secret in ["unit-test-app-id", "unit-test-secret"]:
        assert secret not in json.dumps(data) and secret not in imported.text


def test_invalid_envelope_and_input_bounds(client, monkeypatch):
    monkeypatch.setattr(service, "_fetch", lambda params: {"results": "bad format"})
    assert client.get(P + "/opportunities/external/adzuna").status_code == 502
    assert client.get(P + "/opportunities/external/adzuna?limit=21").status_code == 422
    assert client.get(P + "/opportunities/external/adzuna?page=0").status_code == 422
    assert client.post(P + "/opportunities/import/adzuna", json={"search_token": "x"*32, "references": []}).status_code == 422


def test_backend_dotenv_environment_precedence(tmp_path, monkeypatch):
    from app.config import load_environment
    path = tmp_path / ".env"
    path.write_text('ADZUNA_APP_ID="file-test-id"\nADZUNA_APP_KEY=file-test-key\nUNRECOGNIZED_SETTING=ignored\n')
    monkeypatch.delenv("ADZUNA_APP_ID", raising=False)
    monkeypatch.setenv("ADZUNA_APP_KEY", "shell-test-key")
    load_environment(path)
    import os
    assert os.environ["ADZUNA_APP_ID"] == "file-test-id"
    assert os.environ["ADZUNA_APP_KEY"] == "shell-test-key"
    assert "UNRECOGNIZED_SETTING" not in os.environ
