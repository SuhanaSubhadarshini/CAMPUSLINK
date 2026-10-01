"""Loopback Live Server ports are allowed; unrelated origins remain denied."""
import pytest


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5500", "http://127.0.0.1:5501", "http://localhost:5502", "http://127.0.0.1:61234"])
def test_live_server_allowed(client, origin):
    response = client.options("/api/v1/students", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers
    response = client.get("/api/v1/analytics/dashboard", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


@pytest.mark.parametrize("origin", ["null", "http://evil.example:5501", "http://localhost.evil.example:5501", "http://127.0.0.1.evil.example:5501", "http://192.168.1.10:5501", "https://localhost:5501"])
def test_live_server_disallowed(client, origin):
    response = client.options("/api/v1/students", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_original_configured_profile_score_is_preserved(client):
    # Fixed inputs preserve the original 56.25 backend / 56.3 display regression
    # without depending on or overwriting a user's editable working profile.
    student = client.post("/api/v1/students", json={
        "name": "Configured profile regression", "email": "configured-regression@example.com",
        "department": "CS(AIML)", "graduation_year": 2028, "cgpa": 7.5,
        "skills": ["Python", "Machine Learning", "Deep Learning", "TensorFlow"]
    }).json()
    job = client.post("/api/v1/jobs", json={
        "company_id": 1, "title": "Configured matching regression",
        "required_skills": ["Python", "Machine Learning"],
        "preferred_skills": ["Deep Learning", "TensorFlow"]
    }).json()
    fit = client.get("/api/v1/matching/fit", params={"student_id": student["id"], "job_id": job["id"]}).json()
    assert fit["overall_fit_score"] == 56.25
    assert fit["skill_match_percentage"] == 100
    assert fit["eligibility"]["status"] == "ELIGIBLE"
    assert [c["weight_percent"] for c in fit["explanation"]["components"].values()] == [45, 15, 15, 10, 10, 5]
