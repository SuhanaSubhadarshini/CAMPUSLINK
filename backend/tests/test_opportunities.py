from sqlalchemy import create_engine
from app import database

P = "/api/v1"


def test_opportunity_sources_import_filters_and_atomicity(client):
    rows = client.get(P + "/opportunities").json()
    assert len(rows) == 6
    assert all(x["source"] == "demo" and x["vacancy_count"] is None for x in rows)
    original = client.get(P + "/jobs/1").json()
    body = {"company_id": 1, "title": "Custom Research Engineer", "required_skills": ["Custom Sensor Skill"],
            "location": "Remote", "vacancy_count": 3, "source_reference": "feed-2026-1", "source_url": "https://example.com/jobs/1"}
    result = client.post(P + "/opportunities/import", json={"opportunities": [body]})
    assert result.status_code == 201
    job = result.json()[0]
    assert job["source"] == "json_import" and job["created_at"]
    assert client.get(P + "/opportunities?q=Research&location=remote&source=json_import").json() == [job]
    assert client.get(P + "/opportunities?q=%25").json() == []
    assert client.get(P + "/opportunities?skip=0&limit=1").json() == [job]
    assert client.post(P + "/opportunities/import", json={"opportunities": [body]}).status_code == 409
    valid = dict(body, source_reference="new-reference")
    invalid = dict(body, company_id=999)
    assert client.post(P + "/opportunities/import", json={"opportunities": [valid, invalid]}).status_code == 404
    assert len(client.get(P + "/opportunities").json()) == 7
    assert client.post(P + "/opportunities/import", json={"opportunities": [valid, valid]}).status_code == 409
    assert client.post(P + "/opportunities", json=dict(body, vacancy_count=0)).status_code == 422
    assert client.post(P + "/opportunities", json=dict(body, source_url="javascript:alert(1)")).status_code == 422
    client.patch(P + f'/jobs/{job["id"]}', json={"status": "closed"})
    assert len(client.get(P + "/opportunities").json()) == 6
    assert client.get(P + "/opportunities?status=closed").json()[0]["id"] == job["id"]
    assert len(client.get(P + "/opportunities?status=all").json()) == 7
    assert client.get(P + "/jobs/1").json() == original
    assert client.get(P + "/opportunities/999").status_code == 404


def test_interest_lifecycle_and_real_dashboard(client):
    baseline = client.get(P + "/analytics/dashboard").json()
    assert baseline["available_opportunities"] == 6 and baseline["eligible_matches"] > 0
    assert baseline["opportunities_without_vacancy_count"] == 6
    assert baseline["opportunity_sources"] == {"demo": 6}
    assert client.post(P + "/applications", json={"student_id": 10, "job_id": 1}).status_code == 409
    # Eligible student without an existing offer for this job.
    response = client.post(P + "/applications", json={"student_id": 7, "job_id": 1})
    assert response.status_code == 201
    app = response.json()
    assert app["status"] == "interested" and app["placement_id"] is None
    assert client.post(P + "/applications", json={"student_id": 7, "job_id": 1}).status_code == 409
    assert client.get(P + "/applications?student_id=7&job_id=1").json() == [app]
    assert client.get(P + "/applications?student_id=8").json() == []
    assert client.delete(P + "/students/7").status_code == 409
    assert client.delete(P + "/jobs/1").status_code == 409
    assert client.patch(P + "/jobs/1", json={"company_id": 2}).status_code == 409
    for stage in ["shortlisted", "interview", "selected"]:
        response = client.patch(P + f'/applications/{app["id"]}/status', json={"status": stage})
        assert response.status_code == 200 and response.json()["status"] == stage
    placement = client.post(P + "/placements", json={"student_id": 7, "job_id": 1, "company_id": 1}).json()
    client.patch(P + f'/placements/{placement["id"]}/status', json={"status": "joined"})
    app = client.get(P + "/applications?student_id=7").json()[0]
    assert app["placement_id"] == placement["id"] and app["placement_status"] == "joined"
    data = client.get(P + "/analytics/dashboard").json()
    assert data["placed_students"] == baseline["placed_students"] + 1
    assert data["application_statistics"] == {"selected": 1}
    client.patch(P + "/jobs/1", json={"status": "closed"})
    assert client.post(P + "/applications", json={"student_id": 1, "job_id": 1}).status_code == 409
    assert client.get(P + "/analytics/dashboard").json()["available_opportunities"] == 5
    assert client.patch(P + f'/applications/{app["id"]}/status', json={"status": "hired"}).status_code == 422


def test_legacy_opportunity_migration_preserves_unknowns(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + (tmp_path / "legacy.db").as_posix())
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE jobs (id INTEGER PRIMARY KEY, title VARCHAR, description VARCHAR, company_id INTEGER)")
        conn.exec_driver_sql("INSERT INTO jobs VALUES (42, 'Existing role', 'Keep original', 9)")
    monkeypatch.setattr(database, "engine", engine)
    database.initialize_database()
    database.initialize_database()
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT id,title,description,source,vacancy_count,created_at,status FROM jobs").one() == (42, "Existing role", "Keep original", "legacy", None, None, "open")
    engine.dispose()
