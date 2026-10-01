from typing import Literal
from fastapi import APIRouter, Query
from sqlalchemy import select, or_
from ..models import Job, Company
from ..schemas import JobCreate, JobRead, OpportunityImport
from ..services.opportunity_service import ingest
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/opportunities", tags=["Opportunities"])


@router.get("", response_model=list[JobRead])
def opportunities(db: DB, q: str = "", location: str = "", job_type: str = "",
                  source: str = "", status: Literal["open", "closed", "all"] = "open",
                  skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    query = select(Job).join(Company).order_by(Job.id.desc())
    if status != "all":
        query = query.where(Job.status == status)
    if q:
        query = query.where(or_(Job.title.contains(q, autoescape=True), Company.name.contains(q, autoescape=True)))
    if location:
        query = query.where(Job.location.contains(location, autoescape=True))
    if job_type:
        query = query.where(Job.job_type == job_type)
    if source:
        query = query.where(Job.source == source)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.post("", response_model=JobRead, status_code=201)
def create_opportunity(body: JobCreate, db: DB):
    items = ingest(db, [body], "manual")
    commit(db)
    return items[0]


@router.post("/import", response_model=list[JobRead], status_code=201)
def import_opportunities(body: OpportunityImport, db: DB):
    items = ingest(db, body.opportunities, "json_import")
    commit(db)
    return items


@router.get("/{job_id}", response_model=JobRead)
def opportunity(job_id: int, db: DB):
    return get_or_404(db, Job, job_id)
