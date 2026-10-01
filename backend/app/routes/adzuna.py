from typing import Literal
from fastapi import APIRouter, Query
from ..schemas import AdzunaImport
from ..services import adzuna_service
from .common import DB

router = APIRouter(prefix="/opportunities", tags=["Adzuna"])


@router.get("/external/adzuna")
def search_adzuna(query: str = Query("software engineer", min_length=1, max_length=150),
                  location: str = Query("India", max_length=150), page: int = Query(1, ge=1, le=100),
                  limit: int = Query(10, ge=1, le=20),
                  sort_by: Literal["date", "relevance"] = "date",
                  focus: Literal["all", "fresher", "internship", "junior"] = "all"):
    return adzuna_service.search(query, location, page, limit, sort_by, focus)


@router.post("/import/adzuna")
def import_adzuna(body: AdzunaImport, db: DB):
    return adzuna_service.import_selected(db, body.search_token, body.references)
