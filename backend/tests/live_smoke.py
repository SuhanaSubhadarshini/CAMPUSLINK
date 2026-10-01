"""Run against an already running local server; remove created records afterward."""
from uuid import uuid4
import httpx


def run():
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as client:
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response

        for path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            assert get(path).status_code == 200
        prefix = "/api/v1"
        initial = get(prefix + "/analytics/dashboard").json()
        assert initial["total_students"] >= 10
        created = []
        try:
            suffix = uuid4().hex[:10]
            def create(resource, body):
                response = client.post(prefix + resource, json=body)
                assert response.status_code == 201, response.text
                result = response.json()
                created.append(f"{prefix}{resource}/{result['id']}")
                return result["id"]
            sid = create("/students", {"name": "Smoke Test", "email": f"smoke-{suffix}@example.com", "department": "CSE", "graduation_year": 2026, "cgpa": 8, "skills": ["Python"]})
            cid = create("/companies", {"name": f"Smoke Company {suffix}"})
            jid = create("/jobs", {"title": "Smoke Job", "company_id": cid, "required_skills": ["Python"], "minimum_cgpa": 7, "graduation_year": 2026})
            for resource in ["students", "companies", "jobs"]:
                assert isinstance(get(f"{prefix}/{resource}").json(), list)
            query = f"?student_id={sid}&job_id={jid}"
            assert get(prefix + "/matching/eligibility" + query).json()["eligible"]
            assert 0 <= get(prefix + "/matching/fit" + query).json()["overall_fit_score"] <= 100
            assert get(prefix + "/matching/skill-gap" + query).json()["missing_skills"] == []
            assert get(prefix + "/analytics/dashboard").json()["total_students"] == initial["total_students"] + 1
        finally:
            for path in reversed(created):
                response = client.delete(path)
                assert response.status_code == 204, response.text
        assert get(prefix + "/analytics/dashboard").json()["total_students"] == initial["total_students"]
        print("Live HTTP smoke checks passed: root, health, docs, database, create/list/delete, eligibility, fit, skill gap, dashboard.")


if __name__ == "__main__":
    run()
