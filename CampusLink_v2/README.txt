CAMPUSLINK - Opportunity Discovery and Explainable Matching

LIVE SERVER (recommended in VS Code)
Open the CAMPUSLINK workspace root in VS Code. Start the existing backend first:
  cd backend
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
Then right-click CampusLink_v2/index.html -> Open with Live Server.
Workspace settings use loopback host 127.0.0.1, project root /, and port 5501
(to avoid the existing standalone server on 5500).
  http://127.0.0.1:5501/CampusLink_v2/index.html
  http://127.0.0.1:5501/CampusLink_v2/
Use the port shown by Live Server if it chooses another available port.
HTTP localhost and 127.0.0.1 development ports are allowed by backend CORS.
Live Server serves the frontend only; it does not start FastAPI. Restart an older
backend process after applying CORS changes. No Node/npm/Vite build is required.
Assets and scripts are relative; hash navigation preserves the directory path.
No file://, remote/LAN host, or HTTPS support is implied by this local setup.
See ../CAMPUSLINK_LIVE_SERVER_REPORT.md for diagnostics and verification.

ALTERNATIVE STATIC SERVER (PowerShell, workspace root; two terminals)
  cd backend
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

  # Second terminal, workspace root:
  python -m http.server 5500 --bind 127.0.0.1 --directory CampusLink_v2

Open http://127.0.0.1:5500
API documentation: http://127.0.0.1:8000/docs
API base: http://127.0.0.1:8000/api/v1
Use HTTP, not file://. Runtime dependencies are already installed in backend/.venv.
The frontend remains plain HTML/CSS/JavaScript with no build step.

STUDENT JOURNEY
1. Create/select a profile. Custom skills and career titles are unrestricted.
2. Explore Real Opportunities first. Search Adzuna by keyword/location, explicitly
   import a listing, then view its match and original job. Advanced search is expandable.
   Placement-cell records are separate; fictional Demo Opportunities are collapsed
   for students and remain available for controlled demonstrations. Filters apply
   to saved records by role/company, location, type and source.
3. Jobs for Me analyzes all open opportunities, grouping external first, then
   placement-cell records and demo examples. Eligibility groups remain distinct
   within each source. Match percentages are backend fit scores, not hiring odds.
   Ineligible results can show fit, but a score never overrides unmet requirements.
4. Open an opportunity: requirements, provenance, known openings, eligibility,
   six score components, eligibility, matched/missing skills and provisional labels.
5. Express interest. This is a local application for the placement cell; it does
   not send email, contact an employer or submit to an external website.
6. View application stages and offers/joining under Applications / Placements.
7. Upload a resume and review extracted skills in Edit profile. Matching uses
   saved manual plus extracted skills. Uploading again replaces extracted skills.

PLACEMENT OFFICER JOURNEY
Select Placement Officer using View as. This changes the interface, not access rights.
Open Opportunities -> Find Suitable Candidates. Only eligible students are ranked.
View Explanation opens actual opportunity/fit/gap details for that candidate.
Applications / Placements -> shortlist -> interview -> selected -> Record offer.
Offers support offered/accepted/joined/rejected/withdrawn. Statuses are editable;
there is no enforced recruitment state machine. Dates/package are set on creation.
Applications link to the existing offer by student/job; offers are not duplicated.

ADMIN / SOURCE INGESTION
Admin Tools contains manual opportunity creation, company creation/directory,
JSON import and open/close management. Company directory displays company IDs.
Import an object with an opportunities array (1-100 entries):
  {"opportunities":[{"company_id":1,"title":"Your actual role",
    "required_skills":["Your actual skill"],"source_reference":"unique-feed-id",
    "vacancy_count":3,"location":"Remote"}]}
Use actual company IDs and facts; this is a format example, not a live vacancy.
Company must exist. All entries validate before committing. Duplicate nonempty
references within company/source return 409; no partial import is saved. Omit
vacancy_count when unknown. Do not submit zero. source_url must use HTTP(S).
Sources are assigned by the backend: adzuna, demo, manual, json_import, or legacy for
existing local records with unknown provenance. JSON import records may describe
company/placement-cell feeds through source_reference and source_url. There is
no scraping. Adzuna is the only external API source. File import supports JSON only, not CSV.

DATA AND HONEST LIMITS
Job remains the only opportunity table, with additive source/reference/URL,
nullable vacancy count, recorded/imported timestamp, and open/closed status.
The application table stores interest and officer stages. No duplicate jobs table.
Existing rows/IDs survive migration. Unknown old dates and vacancies stay null.
Recognizable legacy seed records are labeled demo; other old records are legacy.
Snapshot before these changes: backend/campuslink.before-opportunities.db.
SEED_DEMO=true seeds only a completely empty database. Set false for empty starts.
There are no frontend fake records, recommendations, market trends or vacancy counts.
Dashboard separates saved open Adzuna counts and external matching pairs from all
stored totals. Stored opportunity, profile and placement totals explicitly include
demo data. Latest Real Opportunities never falls back to fictional vacancies.
Other placement-cell and demo records appear in separate expandable sections.
Analytics retains actual skill supply/demand/gaps and offer/department statistics.
Skill analytics includes all stored jobs, including closed jobs; it is not a market trend.
No authentication: role/profile choices are selections, not protected accounts.
Matching is the existing weighted heuristic, not a trained or validated model.
Configured manual/demo eligibility uses CGPA, graduation year and required skills.
External listings additionally check extracted experience, degree, branch and batch
requirements. Career preference ranking is not implemented. Resume recognition
is dictionary-based; custom skills can always be added/corrected manually.
Scans use three workers and scale with records; this is a small-dataset prototype.
No notifications, external employer delivery, OCR or chatbot. Adzuna is queried on demand; no continuous live feed is claimed.

TESTS (workspace root, servers running)
  cd backend
  .\.venv\Scripts\python.exe -m pytest -q
  .\.venv\Scripts\python.exe tests/verify_frontend_contract.py
  .\.venv\Scripts\python.exe tests/live_smoke.py
  cd ..
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/browser_smoke.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/dynamic_flow.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/opportunity_flow.py

Browser tests use the already installed Playwright environment and Chrome.
CAMPUSLINK_BROWSER can select another installed Chromium browser executable.
All persistent browser mutations target temporary SQLite databases. The live HTTP
smoke creates and deletes its own temporary rows. Existing user rows are preserved.
Screenshots/results are in tests/artifacts/. Detailed report: ../PRODUCT_ALIGNMENT_REPORT.md.
Frontend API contract: ../backend/FRONTEND_API_GUIDE.md.


ADZUNA EXTERNAL SOURCE
Backend loads backend/.env (shell environment takes precedence). Set ADZUNA_APP_ID
and ADZUNA_APP_KEY there; never put either in frontend files or API requests.
Restart the backend after changing .env. Root .env is not loaded at runtime.
The existing root credential entries were copied to ignored backend/.env without
printing them. .env.example has empty placeholders. No new dependency is needed.

Opportunities -> External Job Opportunities -> enter keyword/location/page/limit
-> Search current jobs -> inspect real provider results -> Import to CampusLink &
Analyze. Search makes no database writes. Import is explicit and bounded; repeated
imports refresh the same ID. Stored records appear in ordinary Opportunities,
Jobs for Me, Suitable Candidates, Skill Gaps and the existing interest workflow.
Closed records stay closed on refresh. Applications/offers remain linked.

The first provider is Adzuna's India API. India means country-wide. Other locations
are passed through; Remote does not guarantee a remote-only search. Empty provider
results stay empty. Search results are cached for five minutes, max 32 searches
per process; unique searches have a five-second cooldown, provider 429 a 60-second
cooldown. There is no polling, scheduler or automatic bulk import. Import selected
results before their token expires; after a restart/search-cache eviction, search again.

Adzuna supplies snippets, not necessarily complete requirements. Mandatory clauses
produce required skills; optional and unqualified keyword mentions are preferred
signals. Experience, education, branches and explicit batches are extracted with
warnings and evidence. The original available description is retained.
Empty external required skills produce unavailable (null) coverage, never 100%.
Known failures yield NOT_ELIGIBLE; unresolved requirements yield UNVERIFIED.
Snippets remain unverified even when all detected requirements pass. Jobs for Me
shows a separate amber group; Suitable Candidates ranks only verified matches.
Provisional fit retains the six original weights. An unavailable skill component
contributes zero, without redistributing weights. Review the original listing.
Student professional experience is editable: blank is unknown; explicit 0 means
no professional experience. Projects and certificates never supply experience.
Dashboard separates verified, unverified and not-eligible student/open-job pairs.
Career search hints use supported Adzuna keyword search plus date/relevance sorting.
They are not verified experience filters; no native experience-range filter exists.
No salary or vacancy count is invented. Source date/category/contract are retained
in external_metadata; created_at remains the local import date. Unknown type is unknown.

Each external advert shows Jobs by Adzuna attribution. View Original Listing retains
the provider redirect destination; credential-bearing tracking (including app ID in
utm_source) is removed so credentials never reach the browser. Interest stays local
and does not apply on the employer's website. No estimate of hiring probability.

API: GET /api/v1/opportunities/external/adzuna?query=python&location=India&page=1&limit=5
API: POST /api/v1/opportunities/import/adzuna with search_token and references.
See backend/FRONTEND_API_GUIDE.md and ADZUNA_INTEGRATION_REPORT.md for the contract.

New mocked browser suite (no real provider calls):
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/adzuna_flow.py
Optional, explicit live read-only backend check from backend/:
  .\.venv\Scripts\python.exe tests/live_adzuna.py --live --query "python developer" --location India

Adzuna source documentation and attribution/licensing conditions:
https://developer.adzuna.com/docs/search
https://developer.adzuna.com/docs/terms_of_service
Ongoing institutional analysis may need an Adzuna licence beyond its trial terms.

Requirement upgrade details: CAMPUSLINK_REQUIREMENT_INTELLIGENCE_REPORT.md.

Source hierarchy / preservation / test report: ../CAMPUSLINK_OPPORTUNITY_PRESENTATION_REPORT.md.

RUN EXISTING BROWSER SUITES AGAINST LIVE SERVER
  $env:CAMPUSLINK_FRONTEND_URL='http://127.0.0.1:5501/CampusLink_v2/index.html'
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/browser_smoke.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/dynamic_flow.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/opportunity_flow.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/polish_flow.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/adzuna_flow.py
  .frontend-test-env\Scripts\python.exe CampusLink_v2/tests/live_server_smoke.py
