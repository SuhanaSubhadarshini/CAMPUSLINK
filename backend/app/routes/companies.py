from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from ..models import Company
from ..schemas import CompanyCreate, CompanyRead, CompanyUpdate
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(body: CompanyCreate, db: DB):
    item = Company(**body.model_dump())
    db.add(item)
    commit(db)
    return item


@router.get("", response_model=list[CompanyRead])
def list_companies(db: DB, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    return db.scalars(select(Company).order_by(Company.id).offset(skip).limit(limit)).all()


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, db: DB):
    return get_or_404(db, Company, company_id)


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(company_id: int, body: CompanyUpdate, db: DB):
    item = get_or_404(db, Company, company_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    commit(db)
    return item


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: DB):
    db.delete(get_or_404(db, Company, company_id))
    commit(db)
    return Response(status_code=204)
