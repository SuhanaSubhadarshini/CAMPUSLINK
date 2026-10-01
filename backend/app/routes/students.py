from fastapi import APIRouter, Query, Response
from sqlalchemy import select
from ..models import Student
from ..schemas import StudentCreate, StudentRead, StudentUpdate
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentRead, status_code=201)
def create_student(body: StudentCreate, db: DB):
    item = Student(**body.model_dump())
    db.add(item)
    commit(db)
    return item


@router.get("", response_model=list[StudentRead])
def list_students(db: DB, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    return db.scalars(select(Student).order_by(Student.id).offset(skip).limit(limit)).all()


@router.get("/{student_id}", response_model=StudentRead)
def get_student(student_id: int, db: DB):
    return get_or_404(db, Student, student_id)


@router.patch("/{student_id}", response_model=StudentRead)
def update_student(student_id: int, body: StudentUpdate, db: DB):
    item = get_or_404(db, Student, student_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    commit(db)
    return item


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, db: DB):
    item = get_or_404(db, Student, student_id)
    stored = item.resume_storage_name
    db.delete(item)
    commit(db)
    if stored:
        from ..services.resume_service import remove_file
        remove_file(stored)
    return Response(status_code=204)
