from collections import Counter
import pandas as pd
from sqlalchemy import select
from ..models import Company, Job, Placement, Student, Application
from ..schemas import JobRead, PlacementRead
from .matching_service import eligibility, student_skills
from .skill_extractor import normalize_skills
from .requirement_extractor import required_skills


def dashboard(db):
    students = db.scalars(select(Student).order_by(Student.id)).all()
    jobs = db.scalars(select(Job).order_by(Job.id)).all()
    placements = db.scalars(select(Placement).order_by(Placement.id)).all()
    companies = db.scalars(select(Company.id)).all()
    open_jobs = [j for j in jobs if j.status == "open"]
    applications = db.scalars(select(Application)).all()
    frame = pd.DataFrame([{"department": s.department, "cgpa": s.cgpa} for s in students])
    supply = Counter(skill for s in students for skill in student_skills(s))
    demand = Counter(skill for j in jobs for skill in required_skills(j))
    placed = {p.student_id for p in placements if p.status in {"accepted", "joined"}}
    decisions = {j.id: Counter(eligibility(s, j)["status"] for s in students) for j in jobs}
    counts = sum((decisions[j.id] for j in open_jobs), Counter())
    def top(counter):
        return [{"skill": k, "count": v} for k, v in counter.most_common(10)]
    return {
        "available_opportunities": len(open_jobs),
        "known_vacancies": sum(j.vacancy_count for j in open_jobs if j.vacancy_count is not None),
        "opportunities_without_vacancy_count": sum(j.vacancy_count is None for j in open_jobs),
        "eligible_matches": counts["ELIGIBLE"],
        "unverified_matches": counts["UNVERIFIED"],
        "not_eligible_matches": counts["NOT_ELIGIBLE"],
        "opportunity_sources": dict(Counter(j.source for j in open_jobs)),
        "application_statistics": dict(Counter(a.status for a in applications)),
        "latest_opportunities": [JobRead.model_validate(j).model_dump(mode="json") for j in open_jobs[-5:][::-1]],
        "total_students": len(students), "total_companies": len(companies), "total_jobs": len(jobs),
        "placed_students": len(placed), "placement_rate": round(100 * len(placed) / len(students), 2) if students else 0,
        "average_cgpa": round(float(frame.cgpa.mean()), 2) if students else 0,
        "top_skills": top(supply), "most_demanded_skills": top(demand),
        "recent_jobs": [JobRead.model_validate(j).model_dump(mode="json") for j in jobs[-5:][::-1]],
        "recent_placements": [PlacementRead.model_validate(p).model_dump(mode="json") for p in placements[-5:][::-1]],
        "eligible_students_per_job": [{"job_id": j.id, "title": j.title, "eligible_students": decisions[j.id]["ELIGIBLE"], "unverified_students": decisions[j.id]["UNVERIFIED"], "not_eligible_students": decisions[j.id]["NOT_ELIGIBLE"]} for j in jobs],
        "skill_gaps": [{"skill": skill, "jobs_requiring": count, "students_with_skill": supply[skill], "students_without_skill": len(students) - supply[skill]} for skill, count in demand.most_common()],
        "department_statistics": frame.groupby("department").agg(students=("cgpa", "size"), average_cgpa=("cgpa", "mean")).round(2).reset_index().to_dict(orient="records") if students else [],
        "placement_statistics": {"total_records": len(placements), "by_status": dict(Counter(p.status for p in placements)),
            "average_package_lpa": round(sum(p.package for p in placements if p.status in {"accepted", "joined"}) / sum(p.status in {"accepted", "joined"} for p in placements), 2) if placed else 0},
        "definitions": {"placed_students": "Distinct students with accepted or joined offers", "placement_rate": "Placed students / all students * 100", "package": "Annual INR lakhs (LPA)", "recent": "Last five records by creation ID", "skill_demand": "Required skills only; each job counted once per normalized skill"},
    }
