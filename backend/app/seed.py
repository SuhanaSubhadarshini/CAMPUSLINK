from datetime import date
from sqlalchemy import select
from .database import SessionLocal, initialize_database
from .models import Company, Job, Placement, Student


def seed_demo(db):
    # Only seed a completely empty database; never append to user data.
    if any(db.scalar(select(model.id).limit(1)) is not None for model in [Student, Company, Job, Placement]):
        return False
    companies = [Company(name=name, industry=industry, location=location, description="Fictional company for the CAMPUSLINK demo.") for name, industry, location in [
        ("Odisha Techworks", "Software services", "Bhubaneswar"),
        ("Mahanadi Analytics", "Data analytics", "Bhubaneswar"),
        ("Kalinga Cloud Labs", "Cloud platforms", "Bengaluru"),
        ("Utkal Digital", "Web products", "Hyderabad")]]
    db.add_all(companies)
    db.flush()
    profiles = [
        ("Ananya Mishra", "CSE", 8.7, ["Python", "SQL", "FastAPI", "Git"], 85, 80, 78),
        ("Rahul Sahoo", "IT", 7.8, ["JavaScript", "React", "HTML", "CSS"], 78, 72, 80),
        ("Priya Das", "CSE", 9.1, ["Python", "SQL", "Pandas", "Machine Learning"], 90, 88, 84),
        ("Aditya Nayak", "ECE", 7.2, ["C++", "Data Structures", "Python"], 82, 70, 65),
        ("Sneha Patra", "IT", 8.3, ["Java", "SQL", "Spring Boot", "Git"], 83, 79, 86),
        ("Sourav Jena", "CSE", 6.4, ["HTML", "CSS", "JavaScript"], 55, 58, 62),
        ("Riya Behera", "EEE", 7.6, ["Python", "Excel", "SQL"], 62, 82, 77),
        ("Aman Panda", "CSE", 8.1, ["Python", "Docker", "AWS", "Linux", "Git"], 80, 76, 72),
        ("Swati Mohanty", "IT", 8.5, ["JavaScript", "React", "Node.js", "MongoDB"], 88, 84, 90),
        ("Debashish Rout", "Mechanical", 6.9, ["C", "Excel", "Communication"], 40, 68, 74)]
    students = [Student(name=name, email=f"student{i+1}@example.com", phone=f"90000000{i+1:02d}", department=department,
        graduation_year=2027 if i in {3, 9} else 2026, cgpa=cgpa, skills=skills,
        coding_score=coding, aptitude_score=aptitude, communication_score=communication,
        certifications=["Programming fundamentals"] if i % 2 == 0 else [],
        projects=["Campus event portal", "Placement tracker"] if i % 3 == 0 else ["Department mini project"])
        for i, (name, department, cgpa, skills, coding, aptitude, communication) in enumerate(profiles)]
    db.add_all(students)
    job_specs = [
        (0, "Python Backend Developer", ["Python", "SQL"], ["FastAPI", "Git"], 7.0, "6 LPA", "full-time"),
        (3, "Frontend Developer", ["JavaScript", "React"], ["HTML", "CSS"], 7.0, "5.5 LPA", "full-time"),
        (1, "Data Analyst", ["Python", "SQL", "Pandas"], ["Excel", "Power BI"], 7.5, "7 LPA", "full-time"),
        (2, "Cloud Engineering Intern", ["Python", "Linux"], ["AWS", "Docker"], 7.0, "INR 25000/month", "internship"),
        (0, "Java Developer", ["Java", "SQL"], ["Spring Boot", "Git"], 7.5, "6.5 LPA", "full-time"),
        (3, "Web Development Intern", ["HTML", "CSS"], ["JavaScript", "React"], 6.0, "INR 15000/month", "internship")]
    jobs = [Job(source="demo", company_id=companies[c].id, title=title, required_skills=required, preferred_skills=preferred,
        minimum_cgpa=cgpa, graduation_year=2026, location=companies[c].location,
        salary_stipend=pay, job_type=kind, description=f"Build practical products as a {title.lower()}.")
        for c, title, required, preferred, cgpa, pay, kind in job_specs]
    db.add_all(jobs)
    db.flush()
    for student_index, job_index, status, package in [(0, 0, "accepted", 6), (2, 2, "joined", 7), (4, 4, "offered", 6.5), (8, 1, "accepted", 5.5)]:
        db.add(Placement(student_id=students[student_index].id, company_id=jobs[job_index].company_id, job_id=jobs[job_index].id,
                         status=status, package=package, offer_date=date(2026, 9, 15)))
    db.commit()
    return True


if __name__ == "__main__":
    initialize_database()
    with SessionLocal() as db:
        print("Demo data created." if seed_demo(db) else "Database has data; nothing changed.")
