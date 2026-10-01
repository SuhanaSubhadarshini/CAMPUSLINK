from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str] = mapped_column(String(25), default="")
    department: Mapped[str] = mapped_column(String(100))
    degree: Mapped[str] = mapped_column(String(150), default="", server_default="")
    preferred_role: Mapped[str] = mapped_column(String(150), default="", server_default="")
    professional_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    graduation_year: Mapped[int]
    cgpa: Mapped[float] = mapped_column(Float)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    certifications: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    coding_score: Mapped[float] = mapped_column(default=0)
    aptitude_score: Mapped[float] = mapped_column(default=0)
    communication_score: Mapped[float] = mapped_column(default=0)
    resume_filename: Mapped[str | None]
    resume_storage_name: Mapped[str | None]
    resume_text: Mapped[str | None] = mapped_column(Text)
    extracted_skills: Mapped[list] = mapped_column(JSON, default=list)
    placements: Mapped[list["Placement"]] = relationship(back_populates="student", passive_deletes="all")


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    industry: Mapped[str] = mapped_column(default="")
    location: Mapped[str] = mapped_column(default="")
    website: Mapped[str] = mapped_column(default="")
    description: Mapped[str] = mapped_column(Text, default="")
    jobs: Mapped[list["Job"]] = relationship(back_populates="company", passive_deletes="all")
    placements: Mapped[list["Placement"]] = relationship(back_populates="company", passive_deletes="all")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("company_id", "source", "source_reference", name="uq_opportunity_source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    title: Mapped[str]
    description: Mapped[str] = mapped_column(Text, default="")
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list)
    minimum_cgpa: Mapped[float] = mapped_column(default=0)
    graduation_year: Mapped[int | None]
    location: Mapped[str] = mapped_column(default="")
    salary_stipend: Mapped[str] = mapped_column(default="")
    job_type: Mapped[str] = mapped_column(default="full-time")
    vacancy_count: Mapped[int | None]
    source: Mapped[str] = mapped_column(default="manual", server_default="legacy")
    source_reference: Mapped[str | None]
    external_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str | None]
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(default="open", server_default="open")
    company: Mapped[Company] = relationship(back_populates="jobs")
    placements: Mapped[list["Placement"]] = relationship(back_populates="job", passive_deletes="all")


class Placement(Base):
    __tablename__ = "placements"
    __table_args__ = (UniqueConstraint("student_id", "job_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(default="offered")
    offer_date: Mapped[date | None] = mapped_column(Date)
    joining_date: Mapped[date | None] = mapped_column(Date)
    package: Mapped[float] = mapped_column(default=0)
    student: Mapped[Student] = relationship(back_populates="placements")
    company: Mapped[Company] = relationship(back_populates="placements")
    job: Mapped[Job] = relationship(back_populates="placements")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("student_id", "job_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(default="interested")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
