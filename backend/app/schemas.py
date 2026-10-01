from datetime import date, datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from .services.skill_extractor import clean_skill_names

Name = Annotated[str, Field(min_length=1, max_length=150)]
Score = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
CGPA = Annotated[float, Field(ge=0, le=10, allow_inf_nan=False)]
Year = Annotated[int, Field(ge=2000, le=2100)]
Status = Literal["offered", "accepted", "joined", "rejected", "withdrawn"]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    @field_validator("skills", "required_skills", "preferred_skills", "certifications", "projects", check_fields=False)
    @classmethod
    def clean_lists(cls, values):
        return list(dict.fromkeys(v.strip() for v in values if v.strip()))

    @field_validator("skills", "required_skills", "preferred_skills", "extracted_skills", check_fields=False)
    @classmethod
    def clean_skills(cls, values):
        return clean_skill_names(values)

    @field_validator("created_at", "updated_at", check_fields=False)
    @classmethod
    def utc_timestamp(cls, value):
        # SQLite stores naive datetimes; these application timestamps are always UTC.
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value

    @field_validator("email", check_fields=False)
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class StudentCreate(Schema):
    name: Name
    email: EmailStr
    phone: str = Field(default="", max_length=25)
    department: Name
    degree: str = Field(default="", max_length=150)
    preferred_role: str = Field(default="", max_length=150)
    professional_experience_years: float | None = Field(default=None, ge=0, le=80, allow_inf_nan=False)
    graduation_year: Year
    cgpa: CGPA
    skills: list[str] = Field(default_factory=list, max_length=100)
    certifications: list[str] = Field(default_factory=list, max_length=100)
    projects: list[str] = Field(default_factory=list, max_length=100)
    coding_score: Score = 0
    aptitude_score: Score = 0
    communication_score: Score = 0


class StudentRead(StudentCreate):
    id: int
    resume_filename: str | None
    extracted_skills: list[str]


class CompanyCreate(Schema):
    name: Name
    industry: str = ""
    location: str = ""
    website: str = ""
    description: str = ""


class CompanyRead(CompanyCreate):
    id: int


class JobCreate(Schema):
    company_id: int = Field(gt=0)
    title: Name
    description: str = ""
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_skills: list[str] = Field(default_factory=list, max_length=100)
    minimum_cgpa: CGPA = 0
    graduation_year: Year | None = None
    location: str = ""
    salary_stipend: str = ""
    job_type: Literal["full-time", "internship", "part-time", "contract", "unknown"] = "full-time"


    vacancy_count: int | None = Field(default=None, ge=1)
    source_reference: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=2000, pattern=r"^https?://[^\s]+$")
    status: Literal["open", "closed"] = "open"


class JobRead(JobCreate):
    external_metadata: dict | None = None
    source: str
    created_at: datetime | None
    id: int
    company: CompanyRead


class PlacementCreate(Schema):
    student_id: int = Field(gt=0)
    company_id: int = Field(gt=0)
    job_id: int = Field(gt=0)
    status: Status = "offered"
    offer_date: date | None = None
    joining_date: date | None = None
    package: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def dates_in_order(self):
        if self.offer_date and self.joining_date and self.joining_date < self.offer_date:
            raise ValueError("joining_date must be on or after offer_date")
        return self


class PlacementRead(PlacementCreate):
    id: int


class PlacementStatus(Schema):
    status: Status


# Updates retain each field's original validation. Omitted fields are unchanged;
# explicit null is accepted only for fields that are nullable on creation.
def partial_schema(name, base):
    from pydantic import create_model
    from copy import deepcopy
    fields = {}
    for key, info in base.model_fields.items():
        copied = deepcopy(info)
        copied.default = None
        copied.default_factory = None
        fields[key] = (info.annotation, copied)
    return create_model(name, __base__=Schema, **fields)


class StudentEditable(StudentCreate):
    # Allow users to correct resume extraction, without changing the stored file.
    extracted_skills: list[str] = Field(default_factory=list, max_length=100)


StudentUpdate = partial_schema("StudentUpdate", StudentEditable)
CompanyUpdate = partial_schema("CompanyUpdate", CompanyCreate)
JobUpdate = partial_schema("JobUpdate", JobCreate)


class OpportunityImport(Schema):
    opportunities: list[JobCreate] = Field(min_length=1, max_length=100)


ApplicationStage = Literal["interested", "shortlisted", "interview", "selected", "rejected", "withdrawn"]


class ApplicationCreate(Schema):
    student_id: int = Field(gt=0)
    job_id: int = Field(gt=0)


class ApplicationStatus(Schema):
    status: ApplicationStage


class ApplicationRead(ApplicationCreate):
    id: int
    status: ApplicationStage
    created_at: datetime
    updated_at: datetime
    student_name: str
    job_title: str
    company_name: str
    placement_id: int | None
    placement_status: str | None


class AdzunaImport(Schema):
    search_token: str = Field(min_length=20, max_length=100)
    references: list[str] = Field(min_length=1, max_length=20)
