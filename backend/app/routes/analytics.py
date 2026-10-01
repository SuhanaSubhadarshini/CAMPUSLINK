from fastapi import APIRouter
from ..services.analytics_service import dashboard
from .common import DB

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def get_dashboard(db: DB):
    return dashboard(db)


@router.get("/skills")
def get_skill_analytics(db: DB):
    data = dashboard(db)
    return {key: data[key] for key in ["top_skills", "most_demanded_skills", "skill_gaps"]}


@router.get("/eligibility")
def get_eligibility_analytics(db: DB):
    return dashboard(db)["eligible_students_per_job"]
