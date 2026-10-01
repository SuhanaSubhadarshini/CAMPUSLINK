from typing import Annotated
from fastapi import Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..database import get_db

DB = Annotated[Session, Depends(get_db)]


def get_or_404(db, model, item_id):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(404, f"{model.__name__} {item_id} not found")
    return item


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicting record: duplicate unique value or referenced record cannot be deleted.")
