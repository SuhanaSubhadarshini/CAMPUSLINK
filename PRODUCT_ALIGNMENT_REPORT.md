# CAMPUSLINK product alignment report

## 1. What was wrong

The previous UI put company/job creation and standalone score screens ahead of
opportunity discovery. Navigation included unavailable Drive Planner and Assistant
pages, and the dashboard repeated generic totals and charts. Working matching,
profiles and offers were present, but opportunity provenance/availability and a
student interest stage were missing. The audit is in PRODUCT_ALIGNMENT_AUDIT.md.

## 2. Removed or simplified

Removed the Drive Planner and Assistant screens and their navigation. Removed the
hero placement-rate decoration, company orbit initials and redundant journey strip.
The home dashboard now has four relevant metrics rather than seven generic cards
plus duplicated analytics. Company/job creation moved into officer Admin Tools.
There are no canned chatbot replies, fake recommendations, market trends, hiring
predictions or frontend fallback records. Fictional backend seed data stays labeled.

## 3. Redesigned sections

Dashboard leads with "Find the right opportunity. Find the right candidate."
Opportunities is prominent and filterable. Details combine requirements, provenance,
eligibility, explanations and gaps. Jobs for Me and Suitable Candidates use backend
results. Applications / Placements completes the lifecycle. Role-specific navigation
keeps student and officer tasks readable while preserving the existing palette,
rounded cards, responsive layouts and profile/resume editor.

## 4. Primary flow

Discover open opportunities -> inspect requirements -> choose student profile ->
check eligibility -> explain fit and gaps -> express interest -> officer selection
-> offer -> joining. Company/job data entry is an administrative fallback.

## 5. Backend changes

Added opportunity discovery/read/manual-create/JSON-import routes and a reusable
opportunity_service.ingest boundary. Added application list/create/status routes.
Extended Job schemas and SQLite with source/reference/URL, nullable vacancy count,
UTC creation/import timestamp and open/closed status. Added Application with unique
student/job, timestamps and editable stages. Restricted deleting referenced records
and changing the company of jobs with applications. Added source-reference database
uniqueness and opportunity/application analytics. No dependencies added.

## 6. Frontend changes

index.html reorganizes the screens. app.js retains shared transport and existing
profile/matching/offer behavior, now loads /opportunities and renders meaningful
home metrics. workflows.js retains arbitrary profiles/roles/skills and uses open
opportunities for discovery. opportunities.js supplies details, backend filters,
role presentation, import/availability management and interest/stage workflows.
Existing style.css is extended; no framework/build step was introduced.

## 7. Opportunity data architecture

Job remains the sole opportunity table, linked to the existing Company. No duplicate
Opportunity table exists. Sources: demo, manual, json_import, legacy. The backend
assigns the source; supplied source references and HTTP(S) URLs describe provenance.
Imports use existing company IDs and commit all 1-100 validated entries atomically.
Non-null references are unique per company/source, including concurrent writes.
JSON is supported; CSV and external providers are future adapters, not implemented.
Unknown vacancy counts and old dates remain null. Vacancy counts are reported data,
not an automatic inventory decremented by hires. Closing preserves historical offers.

Startup migrations are additive and idempotent. Known legacy seed identity/description
combinations are labeled demo; other old records retain unknown provenance as legacy.
A pre-change SQLite snapshot is backend/campuslink.before-opportunities.db.
A final comparison confirmed every original value in 11 students, 5 companies,
7 jobs and 4 placements is unchanged. User-created records were retained alongside
seed data. Test applications did not enter the working database.

## 8. Matching workflow

The original backend formula is unchanged: skills 45%, CGPA 15%, coding 15%,
aptitude 10%, communication 10%, portfolio 5%. Eligibility checks minimum CGPA,
specified graduation year and every required skill. Suitable Candidates evaluates
all students and ranks eligible ones by backend fit. Jobs for Me evaluates all open
opportunities, ranks eligible ones by fit, and lists unmet requirements afterward
without presenting an ineligible fit score. Three workers bound browser requests.
Scores, weights, contributions and skill gaps come from the existing APIs. Partial
failures are reported and can be refreshed. No JavaScript scoring formula was added.

## 9. Student workflow

Select/create profile -> enter arbitrary degree/branch/preferred role and skills ->
review resume extraction -> Jobs for Me or Opportunities -> details and explanation
-> Express interest -> follow applications and offers. Saved custom profile values
and selected profile survive reload. Resume upload/download and extraction correction
remain functional. Preferred role is informational, not an eligibility restriction.

## 10. Placement workflow

An eligible student can express interest once per open opportunity. Officers can
set interested, shortlisted, interview, selected, rejected or withdrawn. A selected
application exposes Record offer with student/job prefilled. Existing Placement
handles offered/accepted/joined/rejected/withdrawn. Application responses join that
offer by student/job and show current offer status. No duplicated offer is created.
Stages are editable rather than enforcing a strict state machine. Existing direct
offer creation remains available for officer-entered historical records.

## 11. Tests performed

- Existing backend CRUD, validation, scoring, eligibility, resumes, placements,
  analytics, CORS, custom profiles and migration tests.
- New backend import atomicity, source labels, filters/pagination, reference
  deduplication, invalid vacancy/URL input, availability, interest eligibility,
  application/offer linkage, conflicts, real aggregates and legacy migration tests.
- Existing browser smoke: live loading/CORS, exact 90.6 demo fit, six components,
  missing skills, stale-selection clearing, company modal, empty/offline/retry,
  real resume upload/download, offer/status persistence, duplicate error and mobile.
- Dynamic browser: custom student/company/opportunity, both matching directions,
  candidate exclusion after editing skills, partial gaps, resume correction,
  reload persistence, dashboard totals and mobile editor.
- New opportunity browser: JSON import, source/count display, filters, backend
  score/requirements, interest persistence, shortlist/interview/selected, offer/joined
  linkage, closing/discovery exclusion, real dashboard counts and mobile Admin Tools.
- All three JavaScript files passed syntax checks. Browser suites assert no
  unexpected console errors or JavaScript exceptions.
- Live HTTP smoke and API guide/OpenAPI method-path plus JSON validation.
- Desktop dashboard screenshot was visually inspected; browser mobile checks verify
  no horizontal document overflow at 390px.

## 12. Results

13 backend tests passed. All 10 browser smoke groups passed. Dynamic browser Tests
A-G passed. The opportunity lifecycle browser suite passed. Live HTTP smoke passed.
All 36 documented operations match current OpenAPI; all 47 JSON examples parse.
One existing upstream Starlette TestClient/httpx deprecation warning remains; no
new dependency was installed to suppress it. Tests that persist browser changes
use isolated temporary SQLite/upload directories and cooperative server shutdown.
Screenshots and structured results are in CampusLink_v2/tests/artifacts/.

## 13. What cannot be claimed

No live external vacancy feed, scraping, employer notification/submission, CSV import,
authentication/authorization, trained ML model, hiring prediction, OCR or chatbot.
Role/profile selection changes the interface only. Matching and resume extraction
are transparent heuristics. Degree/branch restrictions and preference-based ranking
are absent. Analytics describes stored records; skill demand/gaps include closed
jobs and are not market trends. Source contents are not externally verified.
There is no automatic vacancy expiration or slot reservation. Application stages
are current status, not an audited event history. Small-dataset scans are not a
large-scale recommendation service. Placement editing remains status-only.

## 14. Exact run commands

From C:\Users\SUHANA\Music\CAMPUSLINK, use two PowerShell terminals:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Second terminal from the workspace root:

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory CampusLink_v2
```

Open http://127.0.0.1:5500. API docs: http://127.0.0.1:8000/docs.
The existing installed environments are sufficient; do not start duplicate servers
if these ports already serve the app. No frontend build command is needed.

Verification from the workspace root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/verify_frontend_contract.py
.\.venv\Scripts\python.exe tests/live_smoke.py
cd ..
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/browser_smoke.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/dynamic_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/opportunity_flow.py
```

The API contract is backend/FRONTEND_API_GUIDE.md; frontend usage and import format
are in CampusLink_v2/README.txt. Both document the actual implemented endpoints.
