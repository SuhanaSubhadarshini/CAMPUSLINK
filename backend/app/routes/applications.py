from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from ..models import Application, Student, Job, Placement
from ..schemas import ApplicationCreate, ApplicationRead, ApplicationStatus
from ..services.matching_service import eligibility
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/applications", tags=["Applications"])


def present(db, item):
    student = db.get(Student, item.student_id)
    job = db.get(Job, item.job_id)
    placement = db.scalar(select(Placement).where(Placement.student_id == item.student_id, Placement.job_id == item.job_id))
    return dict(id=item.id, student_id=item.student_id, job_id=item.job_id, status=item.status,
                created_at=item.created_at, updated_at=item.updated_at, student_name=student.name,
                job_title=job.title, company_name=job.company.name,
                placement_id=placement.id if placement else None, placement_status=placement.status if placement else None)


@router.get("", response_model=list[ApplicationRead])
def applications(db: DB, student_id: int | None = None, job_id: int | None = None,
                 skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    query = select(Application).order_by(Application.id.desc())
    if student_id is not None:
        query = query.where(Application.student_id == student_id)
    if job_id is not None:
        query = query.where(Application.job_id == job_id)
    return [present(db, x) for x in db.scalars(query.offset(skip).limit(limit)).all()]


@router.post("", response_model=ApplicationRead, status_code=201)
def apply(body: ApplicationCreate, db: DB):
    student = get_or_404(db, Student, body.student_id)
    job = get_or_404(db, Job, body.job_id)
    if job.status != "open":
        raise HTTPException(409, "This opportunity is closed")
    decision = eligibility(student, job)
    if decision["status"] == "UNVERIFIED":
        raise HTTPException(409, "Eligibility unverified; review the original listing and complete the student profile")
    if not decision["eligible"]:
        raise HTTPException(409, "Student does not meet this opportunity's eligibility requirements")
    item = Application(**body.model_dump())
    db.add(item)
    commit(db)
    return present(db, item)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
def change_status(application_id: int, body: ApplicationStatus, db: DB):
    item = get_or_404(db, Application, application_id)
    item.status = body.status
    item.updated_at = datetime.now(timezone.utc)
    commit(db)
    return present(db, item)
