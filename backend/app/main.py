from contextlib import asynccontextmanager

import os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from .database import SessionLocal, initialize_database

from .routes import (
    adzuna,
    opportunities,
    applications,
    analytics,
    companies,
    jobs,
    matching,
    placements,
    resumes,
    students,
)

from .routes.common import DB

from .seed import seed_demo


@asynccontextmanager
async def lifespan(app):
    initialize_database()

    if os.getenv("SEED_DEMO", "true").lower() == "true":
        with SessionLocal() as db:
            seed_demo(db)

    from .services.requirement_extractor import backfill

    with SessionLocal() as db:
        backfill(db)

    yield


app = FastAPI(
    title="CAMPUSLINK",
    version="1.0.0",
    description="Campus placement management and explainable matching hackathon prototype.",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# CORS CONFIGURATION
# ---------------------------------------------------------

default_cors_origins = (
    "http://localhost:3000,"
    "http://localhost:5173,"
    "http://localhost:5500,"
    "http://127.0.0.1:5500,"
    "https://campuslink-frontend-dpff.onrender.com"
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", default_cors_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------
# API ROUTERS
# ---------------------------------------------------------

for router in [
    adzuna.router,
    opportunities.router,
    applications.router,
    students.router,
    companies.router,
    jobs.router,
    matching.router,
    resumes.router,
    analytics.router,
    placements.router,
]:
    app.include_router(router, prefix="/api/v1")


# ---------------------------------------------------------
# SYSTEM ENDPOINTS
# ---------------------------------------------------------

@app.get("/", tags=["System"])
def root():
    return {
        "project": "CAMPUSLINK",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["System"])
def health(db: DB):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "service": "CAMPUSLINK Backend",
    }