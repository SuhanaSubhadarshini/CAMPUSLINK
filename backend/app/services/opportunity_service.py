"""Local opportunity ingestion boundary. External providers can validate JobCreate here."""
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Company, Job


def ingest(db, records, source):
    items = []
    references = set()
    for record in records:
        if db.get(Company, record.company_id) is None:
            raise HTTPException(404, f"Company {record.company_id} not found")
        if record.source_reference:
            key = (record.company_id, record.source_reference)
            if key in references or db.scalar(select(Job.id).where(
                Job.company_id == record.company_id, Job.source == source,
                Job.source_reference == record.source_reference).limit(1)):
                raise HTTPException(409, "Duplicate source reference for this company and source")
            references.add(key)
        items.append(Job(**record.model_dump(), source=source))
    db.add_all(items)
    return items
