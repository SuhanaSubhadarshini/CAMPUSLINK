from . import config  # Load backend/.env before reading environment defaults.
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'campuslink.db').as_posix()}")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database():
    """Create tables and apply idempotent additive SQLite migrations."""
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(students)")}
        # Fixed statements only; no user-supplied SQL identifiers.
        if "degree" not in columns:
            connection.exec_driver_sql("ALTER TABLE students ADD COLUMN degree VARCHAR(150) NOT NULL DEFAULT ''")
        if "preferred_role" not in columns:
            connection.exec_driver_sql("ALTER TABLE students ADD COLUMN preferred_role VARCHAR(150) NOT NULL DEFAULT ''")
        if "professional_experience_years" not in columns:
            connection.exec_driver_sql("ALTER TABLE students ADD COLUMN professional_experience_years FLOAT")
        job_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(jobs)")}
        additions = {"vacancy_count": "INTEGER", "source": "VARCHAR NOT NULL DEFAULT 'legacy'",
                     "source_reference": "VARCHAR", "source_url": "VARCHAR", "created_at": "DATETIME",
                     "status": "VARCHAR NOT NULL DEFAULT 'open'", "external_metadata": "JSON"}
        for column, definition in additions.items():
            if column not in job_columns:
                connection.exec_driver_sql(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_opportunity_source ON jobs (company_id, source, source_reference)")
        connection.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_adzuna_reference ON jobs (source_reference) WHERE source = 'adzuna'")
        # Recognize only unchanged legacy seed records by their original identity and description.
        for title, company in [("Python Backend Developer", "Odisha Techworks"),
                               ("Frontend Developer", "Utkal Digital"), ("Data Analyst", "Mahanadi Analytics"),
                               ("Cloud Engineering Intern", "Kalinga Cloud Labs"),
                               ("Java Developer", "Odisha Techworks"), ("Web Development Intern", "Utkal Digital")]:
            connection.exec_driver_sql(
                "UPDATE jobs SET source='demo' WHERE source='legacy' AND title=? AND description=? "
                "AND company_id IN (SELECT id FROM companies WHERE name=? AND description=?)",
                (title, f"Build practical products as a {title.lower()}.", company,
                 "Fictional company for the CAMPUSLINK demo."))
        connection.commit()


def get_db():
    with SessionLocal() as session:
        yield session
