# CAMPUSLINK Backend

Demo-ready campus-to-corporate placement management API for the BPUT hackathon. Built with Python 3, FastAPI, SQLAlchemy, SQLite, Pydantic and Pandas. Resume parsing uses python-multipart, pypdf and python-docx. scikit-learn is installed as requested but is deliberately not used: this version uses transparent scoring, not a trained hiring model.

## Run from the workspace (PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The virtual environment is already installed in this workspace. On subsequent runs, only the final command is needed from `backend/`. No activation or PowerShell execution policy change is required. On macOS/Linux use `.venv/bin/python` in place of `.\.venv\Scripts\python.exe`. `requirements-lock.txt` records the tested versions on Python 3.13; `requirements.txt` lists direct dependency ranges. SQLAlchemy 2.0 and Pandas 2.x avoid compiled-library loading failures encountered on this Windows machine with newer major/minor versions.

- Server: http://127.0.0.1:8000
- Swagger interactive API: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI contract: http://127.0.0.1:8000/openapi.json

SQLite tables initialize on startup. A completely empty database receives 10 fictional students, 4 fictional companies, 6 jobs and 4 offers. Existing data is never overwritten or reseeded. Default files are `backend/campuslink.db` and `backend/uploads/`, regardless of the working directory. To disable seeding set `$env:SEED_DEMO = 'false'` before starting. See `.env.example` for settings; it is a template, not an automatically loaded file. Run `python -m app.seed` from backend to seed an empty database manually.

## Structure

```text
backend/
  app/
    main.py             # FastAPI, startup, CORS, system endpoints
    database.py         # SQLAlchemy sessions and SQLite foreign keys
    models.py           # Student, Company, Job, Placement
    schemas.py          # Request/response validation
    seed.py             # Idempotent demo seeding
    routes/             # students, companies, jobs, matching, resumes,
                        # placements, analytics, common helpers
    services/           # matching, analytics, resume handling, skill extraction
      skill_dictionary.json
  tests/                # Isolated integration tests
  requirements.txt
  .env.example
  .gitignore
```

## APIs

All resource endpoints use `/api/v1`. Lists return JSON arrays with `skip=0&limit=100` defaults (maximum limit 500). Updates use PATCH with only changed fields. IDs are integers. Unknown fields and invalid inputs return 422, missing records 404, duplicate values or restricted deletes 409. Creation returns 201 and deletion returns 204 with no body.

| Method | Path | Purpose |
|---|---|---|
| GET | `/`, `/health` | Project information and database health |
| GET, POST | `/api/v1/students` | List/create students |
| GET, PATCH, DELETE | `/api/v1/students/{id}` | Read/update/delete student |
| GET, POST | `/api/v1/companies` | List/create companies |
| GET, PATCH, DELETE | `/api/v1/companies/{id}` | Read/update/delete company |
| GET, POST | `/api/v1/jobs` | List/create jobs; optional `company_id` filter |
| GET, PATCH, DELETE | `/api/v1/jobs/{id}` | Read/update/delete job |
| GET | `/api/v1/matching/eligibility?student_id=1&job_id=1` | Basic eligibility |
| GET | `/api/v1/matching/fit?student_id=1&job_id=1` | Explainable fit score |
| GET | `/api/v1/matching/skill-gap?student_id=6&job_id=2` | Skills and learning priorities |
| POST, GET | `/api/v1/students/{id}/resume` | Upload resume / read extracted text |
| GET | `/api/v1/students/{id}/resume/download` | Download stored resume |
| GET, POST | `/api/v1/placements` | List/create offers; optional `student_id` filter |
| PATCH | `/api/v1/placements/{id}/status` | Set offer status |
| GET | `/api/v1/analytics/dashboard` | Main dashboard with all aggregates |
| GET | `/api/v1/analytics/skills` | Skill supply, demand and gaps |
| GET | `/api/v1/analytics/eligibility` | Eligible student count per job |

Example student JSON:

```json
{
  "name": "Demo Student", "email": "demo@example.com", "phone": "9000000011",
  "department": "CSE", "graduation_year": 2026, "cgpa": 8.2,
  "skills": ["Python", "SQL"], "certifications": ["Python fundamentals"],
  "projects": ["Campus portal"], "coding_score": 80,
  "aptitude_score": 75, "communication_score": 85
}
```

CGPA ranges from 0–10; assessment scores from 0–100. Skills, certifications and projects are arrays of strings. Student email and company name are unique. Jobs reference `company_id` and responses include the company object. `graduation_year: null` means any year is eligible. `salary_stipend` is display text such as `6 LPA` or `INR 15000/month`. Job types: `full-time`, `internship`, `part-time`, `contract`.

Placements require `student_id`, `company_id` and `job_id` from the same company. `package` is annual INR lakhs (LPA), not monthly stipend. Dates use `YYYY-MM-DD`. Status is `offered`, `accepted`, `joined`, `rejected` or `withdrawn`. Each student/job pair has one record. Student/job/company deletion is blocked when it would orphan records; a job with placements cannot move companies.

## Matching and analytics

Eligibility requires minimum CGPA, exact graduation year when specified, and all required skills. Preferred skills do not affect eligibility. Known aliases such as `React.js`/`React` and `JS`/`JavaScript` are normalized; unknown skills compare case-insensitively.

Fit score is the weighted sum of:

| Component | Weight | Component score (0–100) |
|---|---:|---|
| Skills | 45% | 80% required coverage + 20% preferred coverage |
| CGPA | 15% | CGPA × 10 |
| Coding | 15% | Reported coding score |
| Aptitude | 10% | Reported aptitude score |
| Communication | 10% | Reported communication score |
| Portfolio | 5% | min(30 × projects + 20 × certifications, 100) |

If no preferred skills are listed, skills use required coverage alone. No required skills means 100% required coverage. Missing assessment scores default to zero. Portfolio counts do not verify relevance or quality. The response includes contributions, strengths, suggestions and the separate eligibility result. **This is a hackathon heuristic, not a scientifically validated hiring model.** It should support discussion, not make hiring decisions.

Dashboard `placed_students` counts distinct students with accepted/joined offers. Placement rate uses all students as denominator. Offered records alone do not count as placed. Average package covers accepted/joined offers. Top skills include manual and extracted skills; demand counts required skills once per job. Skill gaps report how many students lack each demanded skill, not an estimate of vacancies. Recent entries mean highest creation IDs. Pandas computes CGPA and department aggregates.

Demo: student 1/job 1 is eligible with a 90.60 score; student 10/job 1 fails CGPA, year and skills; student 6/job 2 lacks React. Initial dashboard has 3 placed students, 30% placement rate and 7.86 average CGPA.

## Resume handling

Send multipart form data with field `file` to the upload endpoint. Supports UTF-8 TXT, unencrypted PDF up to 30 pages, and DOCX. Maximum file size is 5 MiB; DOCX expanded content is limited to 20 MiB. UUID storage names prevent filename collisions and path traversal. Invalid formats return a clear error. Text is capped at 200,000 characters. Scanned/image PDFs can be stored but return an OCR warning if no text is available.

Uploads replace `extracted_skills` and the previous resume, keeping manual `skills` unchanged. Matching and analytics use the union. Edit `app/services/skill_dictionary.json` and restart to configure aliases. Skill extraction is isolated for a future LLM adapter; no keys or external service are needed. Dictionary matches are heuristic and do not understand negation or prove proficiency.

## Frontend connection

Serve the frontend over HTTP, for example VS Code Live Server on port 5500. Default CORS origins: `http://localhost:3000`, `http://localhost:5173`, `http://localhost:5500`, `http://127.0.0.1:5500`. Set comma-separated `CORS_ORIGINS` in the server environment for other origins. Do not open HTML through `file://`.

```javascript
const API = 'http://127.0.0.1:8000/api/v1';
async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) throw new Error(JSON.stringify(await response.json()));
  return response.status === 204 ? null : response.json();
}
const dashboard = await request('/analytics/dashboard');
const students = await request('/students');
const fit = await request('/matching/fit?student_id=1&job_id=1');
await request('/students/1', {
  method: 'PATCH', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({communication_score: 85})
});
// fileInput is your <input type="file"> element. Let fetch set multipart headers.
const form = new FormData();
form.append('file', fileInput.files[0]);
await request('/students/1/resume', {method: 'POST', body: form});
```

Use Swagger or `/openapi.json` as the contract. Populate dashboard cards from the summary endpoint, lists from resource endpoints, and pass selected student/job IDs to matching endpoints. Render user-entered text with `textContent`, not raw HTML.

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use a temporary SQLite database and upload directory, covering startup, seed idempotency, CRUD, validation, foreign-key conflicts, eligibility, exact score calculation, skill gaps, placement deduplication, analytics, CORS and resumes. They never modify the demo database.

With the server running on port 8000, run `.\.venv\Scripts\python.exe tests/live_smoke.py` for live HTTP verification. It creates temporary student/company/job records and deletes them afterward. The integration suite now contains 29 passing tests; the installed Starlette version emits one upstream warning about future TestClient HTTPX support.

## MVP limitations

No authentication/authorization, OCR, malware scanning, general migration framework or trained ML model. This is a local single-server demo; do not expose real student data publicly. Upload parsing is synchronous with basic size limits, not a hardened document-processing sandbox. Concurrent edits are last-write-wins. Analytics loads the small dataset in memory. Startup applies the documented additive profile and opportunity upgrades and creates the application table; other model changes require migrations. Back up the database and uploads together. Add authentication and migrations before using real institutional data.

Implementation references: [FastAPI file uploads](https://fastapi.tiangolo.com/tutorial/request-files/), [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/), [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).


## User-driven profile additions

Student create/read/PATCH include optional degree and preferred_role strings
(default empty; max 150 characters). The existing department field stores branch.
Career preference is informational and does not modify eligibility or scoring.

Student PATCH also accepts extracted_skills (string array, max 100) so users can
review/correct resume extraction. A later upload replaces that array. Manual and
extracted skills are combined for matching. Skill writes canonicalize known
aliases, collapse whitespace and deduplicate case-insensitively; arbitrary custom
skills remain accepted. Custom skill comparison is case-insensitive.

Startup adds missing degree/preferred_role columns to older SQLite databases
without deleting or reseeding records. This is a narrowly scoped additive upgrade,
not a general migration system. Back up SQLite before other schema changes.

The v2 frontend includes profile create/update, company/job creation, Find Best
Candidates and Find Suitable Jobs using the existing resource and matching APIs.
No new matching endpoint or scoring model is needed.


## Opportunity discovery and student interest

The frontend now consumes `GET /api/v1/opportunities`, defaulting to open records.
The existing Job/Company tables are reused. Job includes nullable vacancy_count,
source_reference/source_url, UTC created_at and open/closed status. Source is
assigned by ingestion: demo, manual, json_import; legacy identifies existing
records with unknown source. Old unknown dates/counts remain null. Initial demo
vacancies are fictional and labeled; Adzuna is now an optional external source (see below); no scraping is used.

`POST /api/v1/opportunities` creates manual opportunities; `POST
/api/v1/opportunities/import` accepts an opportunities array of 1-100 JobCreate
objects. Ingestion validates every company and commits atomically. A non-null
reference is unique per company/source. SQLite enforces this against concurrent
imports. Use existing `PATCH /api/v1/jobs/{job_id}` to close/reopen or edit fields.

`POST /api/v1/applications` records an eligible student's interest in an open job.
One application per student/job; GET lists/filter/paginates; PATCH of its /status
sets interested/shortlisted/interview/selected/rejected/withdrawn. Stage changes
are not constrained to a sequence. Responses join the existing placement by
student/job to report its ID and current offer status. No email/employer delivery.
Foreign keys protect application-linked students/jobs; company reassignment is
blocked once a job has applications or placements. Original placement APIs remain.

Dashboard adds available_opportunities, eligible_matches (student/open-job pairs),
known_vacancies, opportunities_without_vacancy_count, opportunity_sources,
application_statistics and latest_opportunities. Existing analytics fields remain;
skill demand/gap aggregates include closed jobs and are not labor-market claims.
Matching weights/eligibility rules are unchanged. No dependencies were added.

See ../CampusLink_v2/README.txt for exact run commands, role workflows, imports
and browser tests; ../PRODUCT_ALIGNMENT_REPORT.md for the audit and verification.


## Adzuna (optional, backend only)

`app/config.py` loads backend/.env before settings are read, without overriding shell
variables. Supported dotenv values are NAME=value or quoted values; no interpolation.
Use the empty ADZUNA_APP_ID/ADZUNA_APP_KEY placeholders in .env.example. Restart after
editing .env. Missing values disable only external search/import with a safe 503.
The root .env is not a runtime configuration source. Never expose provider URLs with
credentials in application logs. This integration uses a fixed HTTPS origin, disables
redirects and bounds response size/time; it never returns raw provider errors.

GET /api/v1/opportunities/external/adzuna searches India with query/location/page/limit
(max 20). No DB writes. A five-minute in-memory cache returns an opaque import token.
POST /api/v1/opportunities/import/adzuna imports 1-20 selected references from that
token. Expired/evicted/restarted tokens return 409; search again. Local cooldown 5s,
provider 429 cooldown 60s, no retries/polling/background work. Cache/rate limits are
per process, not shared across workers; run the existing single-worker demo.

Job is reused. One nullable JSON external_metadata column retains provider facts
(posting date, contract/category, detected skills, fetch time). A partial unique
Adzuna reference index plus SQLite BEGIN IMMEDIATE protects stable-ID upserts across
company-name changes/concurrent requests. Existing source/reference uniqueness remains.
Company names compare with NFKC/casefold/collapsed whitespace. Existing company data,
job company association, manual requirements and status are preserved during refresh.
Unedited preferred-skill signals update with refreshed description keywords. There
is no expiration inference, automatic closing or vacancy inventory decrement.

Skill extraction reuses the dictionary with explicit Deep Learning/TensorFlow/PyTorch
terms in the provider adapter. It does not modify resume extraction or the matching
formula. Keywords populate preferred_skills; required_skills remain unverified/empty.
No CGPA/year restrictions are invented. Existing engine semantics can then yield
100% required coverage; the frontend displays a warning on external results. No
salary/vacancy values are guessed. job_type adds unknown for absent provider data.

The provider embeds app ID in utm_source on redirect URLs: credential-bearing tracking
parameters are removed before caching/storing/returning, retaining the redirect path
and other provider tokens. Upstream records echoing credentials in other fields are
skipped. External ads carry Jobs by Adzuna linked logo attribution.

Tests: tests/test_adzuna.py uses mocked transport, never real credentials/network.
All normal backend tests override Adzuna credentials with empty/test values.
The optional tests/live_adzuna.py requires --live and reads only; it is not a pytest test.
See ../ADZUNA_INTEGRATION_REPORT.md for live verification, frontend tests and limitations.
