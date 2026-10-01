import io
import pytest
from docx import Document
from pypdf import PdfWriter
from app.database import SessionLocal
from app.seed import seed_demo

PREFIX = "/api/v1"


def student_payload(**changes):
    return {"name": "Test Student", "email": "test@example.com", "department": "CSE", "graduation_year": 2026,
            "cgpa": 8.2, "skills": ["python", "SQL"], **changes}


def test_bootstrap_docs_seed_and_cors(client):
    assert client.get("/").json()["project"] == "CAMPUSLINK"
    assert client.get("/health").json()["status"] == "healthy"
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 200
    assert len(client.get(PREFIX + "/students").json()) == 10
    assert len(client.get(PREFIX + "/companies").json()) == 4
    assert len(client.get(PREFIX + "/jobs").json()) == 6
    with SessionLocal() as db:
        assert seed_demo(db) is False
    response = client.options(PREFIX + "/students", headers={"Origin": "http://localhost:5500", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"


def test_student_crud_and_validation(client):
    response = client.post(PREFIX + "/students", json=student_payload())
    assert response.status_code == 201, response.text
    sid = response.json()["id"]
    assert client.get(f"{PREFIX}/students/{sid}").json()["cgpa"] == 8.2
    assert client.post(PREFIX + "/students", json=student_payload(email="TEST@example.com")).status_code == 409
    response = client.patch(f"{PREFIX}/students/{sid}", json={"cgpa": 9, "skills": ["Python", "Python", " "]})
    assert response.status_code == 200, response.text
    assert response.json()["skills"] == ["Python"]
    assert response.json()["email"] == "test@example.com"
    for body in [{"cgpa": 11}, {"name": None}, {"skills": None}, {"coding_score": -1}, {"email": "bad"}, {"name": " "}, {"unknown": 1}]:
        assert client.patch(f"{PREFIX}/students/{sid}", json=body).status_code == 422
    assert client.delete(f"{PREFIX}/students/{sid}").status_code == 204
    assert client.get(f"{PREFIX}/students/{sid}").status_code == 404
    assert client.get(PREFIX + "/students?limit=0").status_code == 422


def test_company_and_job_crud(client):
    response = client.post(PREFIX + "/companies", json={"name": "Test Company", "location": "Pune"})
    assert response.status_code == 201
    cid = response.json()["id"]
    assert client.get(f"{PREFIX}/companies/{cid}").status_code == 200
    assert client.patch(f"{PREFIX}/companies/{cid}", json={"industry": "Software"}).json()["industry"] == "Software"
    body = {"company_id": cid, "title": "Engineer", "required_skills": ["Python"]}
    response = client.post(PREFIX + "/jobs", json=body)
    assert response.status_code == 201, response.text
    jid = response.json()["id"]
    assert client.get(f"{PREFIX}/jobs/{jid}").json()["company"]["name"] == "Test Company"
    assert client.patch(f"{PREFIX}/jobs/{jid}", json={"minimum_cgpa": 7, "graduation_year": None}).status_code == 200
    assert client.delete(f"{PREFIX}/companies/{cid}").status_code == 409
    assert client.post(PREFIX + "/jobs", json={**body, "company_id": 99999}).status_code == 404
    assert client.delete(f"{PREFIX}/jobs/{jid}").status_code == 204
    assert client.delete(f"{PREFIX}/companies/{cid}").status_code == 204


def test_eligibility_matching_and_gaps(client):
    query = "?student_id=1&job_id=1"
    assert client.get(PREFIX + "/matching/eligibility" + query).json()["eligible"] is True
    fit = client.get(PREFIX + "/matching/fit" + query).json()
    # 45 skills + 13.05 CGPA + 12.75 coding + 8 aptitude + 7.8 communication + 4 portfolio
    assert fit["overall_fit_score"] == 90.6
    assert fit["skill_match_percentage"] == 100
    assert fit["missing_skills"] == []
    assert sum(x["weight_percent"] for x in fit["explanation"]["components"].values()) == 100
    result = client.get(PREFIX + "/matching/eligibility?student_id=10&job_id=1").json()
    assert result["eligible"] is False
    assert {r["requirement"] for r in result["missing_requirements"]} == {"cgpa", "graduation_year", "required_skills"}
    gap = client.get(PREFIX + "/matching/skill-gap?student_id=6&job_id=2").json()
    assert gap["missing_skills"] == ["React"]
    assert gap["skill_match_percentage"] == 50
    assert client.get(PREFIX + "/matching/fit?student_id=9999&job_id=1").status_code == 404


def test_placement_integrity_and_dashboard(client):
    dashboard = client.get(PREFIX + "/analytics/dashboard").json()
    assert [dashboard[k] for k in ["total_students", "total_companies", "total_jobs", "placed_students", "placement_rate"]] == [10, 4, 6, 3, 30]
    assert dashboard["average_cgpa"] == 7.86
    assert len(dashboard["eligible_students_per_job"]) == 6
    assert client.get(PREFIX + "/analytics/skills").status_code == 200
    assert client.get(PREFIX + "/analytics/eligibility").status_code == 200
    body = {"student_id": 1, "company_id": 4, "job_id": 2, "status": "accepted", "package": 5.5}
    response = client.post(PREFIX + "/placements", json=body)
    assert response.status_code == 201, response.text
    pid = response.json()["id"]
    assert client.get(PREFIX + "/analytics/dashboard").json()["placed_students"] == 3  # Count students, not offers.
    assert client.post(PREFIX + "/placements", json=body).status_code == 409
    assert client.post(PREFIX + "/placements", json={**body, "student_id": 2, "company_id": 1}).status_code == 422
    assert client.patch(f"{PREFIX}/placements/{pid}/status", json={"status": "rejected"}).json()["status"] == "rejected"
    assert client.patch(f"{PREFIX}/placements/{pid}/status", json={"status": "invalid"}).status_code == 422
    assert client.patch(PREFIX + "/jobs/1", json={"company_id": 2}).status_code == 409
    assert client.delete(PREFIX + "/students/1").status_code == 409
    assert client.delete(PREFIX + "/jobs/1").status_code == 409
    assert client.post(PREFIX + "/placements", json={**body, "offer_date": "2026-10-10", "joining_date": "2026-01-01"}).status_code == 422


def test_resume_upload_replacement_and_aliases(client):
    url = PREFIX + "/students/6/resume"
    response = client.post(url, files={"file": ("../../resume.txt", b"Python, SQL, React.js and C++ programmer. JavaScript.", "text/plain")})
    assert response.status_code == 200, response.text
    assert response.json()["filename"] == "resume.txt"
    assert response.json()["extracted_skills"] == ["C++", "JavaScript", "Python", "React", "SQL"]
    assert client.get(url + "/download").status_code == 200
    assert "Python" in client.get(url).json()["text"]
    assert client.get(PREFIX + "/matching/skill-gap?student_id=6&job_id=2").json()["missing_skills"] == []
    assert client.post(url, files={"file": ("new.txt", b"Docker", "text/plain")}).status_code == 200
    assert client.get(url).json()["extracted_skills"] == ["Docker"]
    assert client.get(PREFIX + "/matching/skill-gap?student_id=6&job_id=2").json()["missing_skills"] == ["React"]
    assert client.post(url, files={"file": ("bad.exe", b"abc")}).status_code == 415
    assert client.post(url, files={"file": ("bad.pdf", b"not pdf")}).status_code == 422
    assert client.post(url, files={"file": ("empty.txt", b"")}).status_code == 422
    assert client.post(url, files={"file": ("huge.txt", b"x" * (5 * 1024 * 1024 + 1))}).status_code == 413


def test_docx_and_scanned_pdf(client):
    document = Document()
    document.add_paragraph("Python and FastAPI")
    buffer = io.BytesIO()
    document.save(buffer)
    url = PREFIX + "/students/1/resume"
    response = client.post(url, files={"file": ("resume.docx", buffer.getvalue())})
    assert response.status_code == 200
    assert response.json()["extracted_skills"] == ["FastAPI", "Python"]
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buffer = io.BytesIO()
    writer.write(buffer)
    response = client.post(url, files={"file": ("blank.pdf", buffer.getvalue())})
    assert response.status_code == 200
    assert "OCR" in response.json()["warning"]


def test_empty_database_analytics(client):
    from app.database import Base, engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    result = client.get(PREFIX + "/analytics/dashboard")
    assert result.status_code == 200
    assert result.json()["average_cgpa"] == 0
    assert result.json()["placement_rate"] == 0
