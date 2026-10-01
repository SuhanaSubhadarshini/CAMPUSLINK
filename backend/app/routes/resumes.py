from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from ..models import Student
from ..services.resume_service import file_path, remove_file, save_resume
from .common import DB, commit, get_or_404

router = APIRouter(prefix="/students", tags=["Resumes"])


@router.post("/{student_id}/resume")
def upload_resume(student_id: int, file: UploadFile, db: DB):
    student = get_or_404(db, Student, student_id)
    saved = save_resume(file)
    old_name = student.resume_storage_name
    try:
        student.resume_filename = saved["filename"]
        student.resume_storage_name = saved["storage_name"]
        student.resume_text = saved["text"]
        student.extracted_skills = saved["skills"]
        commit(db)
    except Exception:
        remove_file(saved["storage_name"])
        raise
    if old_name:
        remove_file(old_name)
    return {"student_id": student.id, "filename": saved["filename"], "extracted_skills": saved["skills"],
            "text_length": len(saved["text"]),
            "warning": None if saved["text"].strip() else "No text extracted. Scanned documents require OCR, which is not supported."}


@router.get("/{student_id}/resume")
def resume_info(student_id: int, db: DB):
    student = get_or_404(db, Student, student_id)
    if not student.resume_storage_name:
        raise HTTPException(404, "Student has no uploaded resume")
    return {"student_id": student.id, "filename": student.resume_filename, "text": student.resume_text,
            "extracted_skills": student.extracted_skills}


@router.get("/{student_id}/resume/download")
def download_resume(student_id: int, db: DB):
    student = get_or_404(db, Student, student_id)
    if not student.resume_storage_name or not file_path(student.resume_storage_name).is_file():
        raise HTTPException(404, "Resume file not found")
    return FileResponse(file_path(student.resume_storage_name), filename=student.resume_filename, media_type="application/octet-stream")
