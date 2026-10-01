from fastapi import APIRouter
from ..models import Job, Student
from ..services.matching_service import eligibility, match, skill_gap
from .common import DB, get_or_404

router = APIRouter(prefix="/matching", tags=["Matching"])


@router.get("/eligibility")
def check_eligibility(student_id: int, job_id: int, db: DB):
    return eligibility(get_or_404(db, Student, student_id), get_or_404(db, Job, job_id))


@router.get("/fit")
def job_fit(student_id: int, job_id: int, db: DB):
    return match(get_or_404(db, Student, student_id), get_or_404(db, Job, job_id))


@router.get("/skill-gap")
def get_skill_gap(student_id: int, job_id: int, db: DB):
    return skill_gap(get_or_404(db, Student, student_id), get_or_404(db, Job, job_id))
