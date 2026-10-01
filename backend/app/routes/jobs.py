from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import select
from ..models import Company, Job, Placement, Application
from ..schemas import JobCreate, JobRead, JobUpdate
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobRead, status_code=201)
def create_job(body: JobCreate, db: DB):
    get_or_404(db, Company, body.company_id)
    item = Job(**body.model_dump())
    db.add(item)
    commit(db)
    return item


@router.get("", response_model=list[JobRead])
def list_jobs(db: DB, company_id: int | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    query = select(Job).order_by(Job.id)
    if company_id is not None:
        query = query.where(Job.company_id == company_id)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: DB):
    return get_or_404(db, Job, job_id)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: int, body: JobUpdate, db: DB):
    item = get_or_404(db, Job, job_id)
    changes = body.model_dump(exclude_unset=True)
    if "company_id" in changes:
        get_or_404(db, Company, changes["company_id"])
        if changes["company_id"] != item.company_id and (db.scalar(select(Placement.id).where(Placement.job_id == job_id).limit(1)) or db.scalar(select(Application.id).where(Application.job_id == job_id).limit(1))):
            raise HTTPException(409, "Cannot change the company of a job with application or placement records")
    for key, value in changes.items():
        setattr(item, key, value)
    commit(db)
    db.refresh(item)
    return item


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, db: DB):
    db.delete(get_or_404(db, Job, job_id))
    commit(db)
    return Response(status_code=204)
