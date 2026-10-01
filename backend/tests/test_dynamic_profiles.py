from sqlalchemy import create_engine
from app import database

PREFIX = "/api/v1"

def test_custom_profile_job_matching_and_review(client):
    response = client.post(PREFIX + "/students", json={
        "name": "Dynamic Candidate", "email": "dynamic@example.com",
        "degree": "B.Tech", "department": "CSE", "preferred_role": "Computer Vision Engineer",
        "graduation_year": 2026, "cgpa": 8.2,
        "skills": ["python", "PYTHON", " Computer   Vision ", "PyTorch", "OpenCV"],
        "coding_score": 85, "aptitude_score": 80, "communication_score": 82,
    })
    assert response.status_code == 201
    student = response.json()
    assert student["skills"] == ["Python", "Computer Vision", "PyTorch", "OpenCV"]
    company = client.post(PREFIX + "/companies", json={"name": "Dynamic Vision Labs"}).json()
    response = client.post(PREFIX + "/jobs", json={
        "company_id": company["id"], "title": "Computer Vision Engineer",
        "required_skills": ["computer vision", "PYTORCH", "opencv"], "minimum_cgpa": 7,
    })
    assert response.status_code == 201
    job = response.json()
    query = f'?student_id={student["id"]}&job_id={job["id"]}'
    assert client.get(PREFIX + "/matching/eligibility" + query).json()["eligible"]
    fit = client.get(PREFIX + "/matching/fit" + query).json()
    assert fit["skill_match_percentage"] == 100
    assert 0 <= fit["overall_fit_score"] <= 100
    response = client.patch(f'{PREFIX}/students/{student["id"]}', json={
        "skills": ["Computer Vision"], "preferred_role": "Generative AI Engineer", "extracted_skills": ["PyTorch"]
    })
    assert response.status_code == 200
    assert response.json()["preferred_role"] == "Generative AI Engineer"
    gap = client.get(PREFIX + "/matching/skill-gap" + query).json()
    assert gap["missing_skills"] == ["opencv"]
    client.patch(f'{PREFIX}/students/{student["id"]}', json={"extracted_skills": []})
    gap = client.get(PREFIX + "/matching/skill-gap" + query).json()
    assert sorted(x.casefold() for x in gap["missing_skills"]) == ["opencv", "pytorch"]
    assert client.get(f'{PREFIX}/students/{student["id"]}').json()["degree"] == "B.Tech"
    assert client.patch(f'{PREFIX}/students/{student["id"]}', json={"preferred_role": None}).status_code == 422
    assert client.patch(f'{PREFIX}/students/{student["id"]}', json={"extracted_skills": None}).status_code == 422

def test_additive_migration_preserves_existing_rows(tmp_path, monkeypatch):
    engine = create_engine("sqlite:///" + (tmp_path / "legacy.db").as_posix())
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE students (id INTEGER PRIMARY KEY, name VARCHAR(120))")
        conn.exec_driver_sql("INSERT INTO students (id, name) VALUES (7, 'Existing Student')")
    monkeypatch.setattr(database, "engine", engine)
    database.initialize_database()
    database.initialize_database()  # Restart must be safe and idempotent.
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT id, name, degree, preferred_role FROM students").one() == (7, "Existing Student", "", "")
    engine.dispose()
