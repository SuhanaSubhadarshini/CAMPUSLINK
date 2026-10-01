from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from ..models import Company, Job, Placement, Student
from ..schemas import PlacementCreate, PlacementRead, PlacementStatus
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/placements", tags=["Placements"])


@router.post("", response_model=PlacementRead, status_code=201)
def create_placement(body: PlacementCreate, db: DB):
    get_or_404(db, Student, body.student_id)
    get_or_404(db, Company, body.company_id)
    job = get_or_404(db, Job, body.job_id)
    if job.company_id != body.company_id:
        raise HTTPException(422, "company_id must match the job's company")
    item = Placement(**body.model_dump())
    db.add(item)
    commit(db)
    return item


@router.get("", response_model=list[PlacementRead])
def list_placements(db: DB, student_id: int | None = None, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    query = select(Placement).order_by(Placement.id)
    if student_id is not None:
        query = query.where(Placement.student_id == student_id)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.patch("/{placement_id}/status", response_model=PlacementRead)
def update_status(placement_id: int, body: PlacementStatus, db: DB):
    item = get_or_404(db, Placement, placement_id)
    item.status = body.status
    commit(db)
    return item
