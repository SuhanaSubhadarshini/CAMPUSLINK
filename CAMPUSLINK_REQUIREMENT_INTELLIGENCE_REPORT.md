# CAMPUSLINK requirement intelligence report

## Result

External opportunities with missing mandatory requirements no longer receive 100%
required-skill coverage or verified eligibility. The backend makes one tri-state
decision, used by eligibility, fit, skill gaps, applications and dashboard analytics.
The frontend groups unverified results separately and labels their fit provisional.
No dependency, paid service, LLM, scraping, polling or architecture rewrite was added.

## Files changed

Backend:
- `backend/app/services/requirement_extractor.py` (new): deterministic extraction,
  evidence, extraction statuses, normalized requirement access and metadata backfill.
- `backend/app/services/skill_dictionary.json`: additional named technologies and aliases.
- `backend/app/models.py`, `schemas.py`, `database.py`: nullable professional experience.
- `backend/app/main.py`: idempotent external requirement backfill at startup.
- `backend/app/services/adzuna_service.py`: retain complete available provider text,
  extract at search/import, refresh automatic requirements safely, supported search hints.
- `backend/app/services/matching_service.py`: central tri-state checks and unavailable coverage.
- `backend/app/services/analytics_service.py`: verified/unverified/not-eligible counts.
- `backend/app/routes/adzuna.py`, `applications.py`: search parameters and unverified-interest rejection.

Frontend:
- `CampusLink_v2/js/app.js`: status helpers, score availability, dashboard counts and profile experience.
- `CampusLink_v2/js/workflows.js`: nullable experience editor, separate unverified group,
  provisional fits and eligible-only candidate rankings.
- `CampusLink_v2/js/opportunities.js`: consistent details, skill gaps and interest controls.
- `CampusLink_v2/js/external.js`: expandable extracted requirements, evidence and original text.
- `CampusLink_v2/index.html`: keyword focus and sorting controls.
- `CampusLink_v2/css/style.css`: amber status and details styling; bounded form tracks prevent
  long external job titles expanding the mobile viewport and blocking navigation.

Tests and documentation:
- `backend/tests/test_requirement_intelligence.py` (new), `test_adzuna.py`,
  `test_dynamic_profiles.py`; `CampusLink_v2/tests/adzuna_flow.py`, `polish_flow.py`.
- `backend/FRONTEND_API_GUIDE.md`, `CampusLink_v2/README.txt`, this report.
- Browser results/screenshots and migration evidence in `CampusLink_v2/tests/artifacts/`.

## Database changes and preservation

Added nullable FLOAT `students.professional_experience_years`, validated as a finite
number from 0 to 80. Missing values remain null. Explicit zero means no professional
experience; projects, certificates and college attendance do not infer experience.
Existing student records are not assigned zero.

Job remains the sole opportunity table. The existing nullable JSON
`external_metadata` stores `original_description` and `requirement_analysis`:
version, extraction status, technical/required/preferred skills, experience bounds,
category, education, branches, batches, warnings and evidence. Unknown required
skills/education/bounds/restrictions are null in this analysis. Existing list fields
remain compatible; their emptiness no longer implies verified external requirements.

SQLite migrations and external backfill are additive and idempotent. Old external
records are analyzed on startup; they also have an on-read extraction fallback.
Existing configured job values, primary keys, source URLs, company associations,
applications and offers are preserved. Backfill changes only external metadata:
analysis, retained available description and the formerly misleading notice.
Explicit re-import keeps the existing ID, status and historical links; automatically
extracted arrays refresh when not subsequently edited by an officer.

Pre-change snapshot: `backend/campuslink.before-requirement-intelligence.db`.
The final comparison preserved all original values in 11 students, 6 companies,
8 jobs and 4 placements (0 applications). Only the additive experience column and
external analysis/notice metadata changed. Existing experience values remain null.
Evidence: `CampusLink_v2/tests/artifacts/requirement-migration.json`.

For listings imported before this upgrade, only their already stored available
text can be retained; prior truncation/HTML normalization cannot be reversed.
New searches retain the full description supplied within the existing bounded
provider response, before display normalization. Extraction never replaces it
with a generated summary. Explicit refresh stores the latest provider description;
this is not a historical archive of every version.

## Extraction rules

Shared skill normalization retains custom profile skills and canonicalizes known
aliases. The dictionary now includes Deep Learning, TensorFlow, PyTorch, Generative
AI, LLM, RAG, Azure and Kubernetes. Boundary matching avoids detecting C in ordinary
words. Canonical PyTorch casing is reflected in the existing custom-skills test.

Required/essential/must/proficiency clauses and recognized requirement sections
supply mandatory skills. Preferred/optional/nice-to-have clauses and unqualified
mentions supply preferred signals. Negation, alternatives and unsupported mandatory
clauses trigger review instead of assuming they are satisfied.

Experience detects fresher/no-experience wording, zero, single minimums, plus signs,
ranges with hyphen/en dash/to, and maximum/up-to wording. Complementary minimum and
maximum statements combine; conflicting ranges or alternative requirements remain
ambiguous. Unspecified experience is never zero. Bounds are inclusive.

Education recognizes B.Tech/B.E., M.Tech/M.E., MCA, Bachelor, Master and Doctorate
patterns. Engineering degree equivalence and generic Bachelor/Master requirements
are handled conservatively. Branch recognition includes Computer Science/CSE,
Information Technology, Electronics/ECE, Mechanical, Civil and Electrical. Relevant
or equivalent disciplines require review. Unsupported student degree/branch aliases
remain unverified instead of being guessed.

Explicit batch/graduation clauses provide years and bounded year ranges; posting
dates do not. Complex before/after comparisons require review. Categories use
explicit internship/employment terms, entry-level keywords, experience and provider
employment fields. They are descriptive classifications, not eligibility guarantees.

Evidence retains the source clause and explicit-versus-keyword method. Separate
field evidence covers experience, education, branch and batch; category is labeled
keyword/source. COMPLETE requires recognized required skills, experience and
education without unresolved ambiguity or snippet incompleteness. PARTIAL has some
usable requirements; INSUFFICIENT_DATA has none. This is qualitative rule confidence,
not a statistical probability.

## Eligibility and scoring decisions

- ELIGIBLE: configured/recognized mandatory checks pass with no unresolved critical check.
- NOT_ELIGIBLE: at least one known mandatory check fails, even if others remain unknown.
- UNVERIFIED: no known failure, but critical requirements or student information remain unknown.

Checks include configured CGPA/year/skills and external experience, education,
explicit branches/batches and extraction completeness. Missing student experience
is unknown; explicit zero fails a positive minimum. The compatibility `eligible`
boolean is true only for ELIGIBLE. Responses explain known failures, unknowns and
individual check statuses. Application creation rejects unverified eligibility with
409; existing applications/offers are retained.

Adzuna's current API descriptions are snippets. They cannot establish completeness,
so matching detected requirements alone never makes an Adzuna snippet verified.
They yield UNVERIFIED or a known NOT_ELIGIBLE failure. There is no new manual
verification/override workflow claiming to resolve missing source text.

Manual/demo/JSON-configured opportunities retain their explicit configuration
semantics, including no required skills meaning no configured skill restriction.
Demo fit remains 90.6; the existing Suhana/profile opportunity remains 56.3.

Weights remain skills 45%, CGPA 15%, coding 15%, aptitude 10%, communication 10%,
portfolio 5%. Defined skill coverage retains the 80% required/20% preferred formula.
For external missing required skills, coverage and skill-component score are null,
`available=false`, contribution=0. Weights are not redistributed. This minimal
correction removes the undefined-coverage bonus; other components remain explainable.
Fit is provisional when eligibility is unverified or skill coverage is unavailable.
A fit score never overrides eligibility.

## API contract changes

No endpoints were added or renamed. All 38 documented method/path operations still
match OpenAPI. Student POST/PATCH/read supports professional_experience_years.
Existing matching responses add status/checks/unknown_requirements/requirement_analysis;
fit adds provisional; gaps add eligibility, eligibility_status, coverage_available
and coverage_note. Consumers must accept nullable skill coverage/component score.

Dashboard eligible_matches now means verified student/open-job pairs;
unverified_matches and not_eligible_matches complete the partition. Per-job
eligibility analytics adds unverified_students and not_eligible_students and still
includes closed jobs. Skill demand includes recognized external mandatory skills.

Adzuna search adds sort_by=date|relevance and focus=all|fresher|internship|junior.
Focus uses official what_or keyword hints; location still uses where. The official
specification has no native experience-range filter, so none is claimed:
https://developer.adzuna.com/swagger/spec/test2.json
Manual search and explicit selected import, cache bounds, cooldowns, provider URL
sanitization, attribution and server-only credentials remain in place.

The API guide's matching/dashboard response examples were refreshed using an
isolated seeded backend. External examples describe illustrative provider fixtures.

## Frontend behavior

Eligible is green, not eligible red, and unverified amber. Jobs for Me has a separate
unverified group; Suitable Candidates ranks only verified eligible students.
Details and skill gaps use the backend decision. Unknown coverage displays
"Skill coverage unavailable" and "No required skills extracted". Provisional fits
retain all six components; unavailable skills display explicitly rather than 0/100.

Expandable source details show technical/required skills, experience, education,
branch/batch, category, extraction status, warnings, evidence and original available
text. Adzuna attribution and the original link remain visible. Unknown external CGPA
is not presented as an asserted zero requirement. Profile editing distinguishes
blank professional experience from zero. Dashboard shows all three matching counts.
Student/officer navigation, manual opportunity flows, resume handling and offers remain.

## Tests executed and results

- Backend pytest: **54 passed**. Covers all 14 requested acceptance cases, plus
  ranges, ambiguity, branches, batches, aliases, boundaries, nullable experience,
  conflicting constraints, unknown coverage, weights, supported search parameters,
  migration/backfill idempotency and dashboard partitioning. Adzuna calls are mocked.
- Browser smoke: **all 10 groups passed**, including 90.6 demo fit, resumes,
  placements, offline/empty/retry behavior and all mobile navigation.
- Dynamic browser: **Tests A-G passed** (custom profiles/skills, both matching
  directions, edits, resume review, reload and mobile).
- Opportunity browser: **passed** (manual JSON import, eligibility, interest,
  application stages, offers/joining, closing, persistence and dashboard).
- Polish browser: **passed**, including Suhana's existing 56.3 fit and four groups.
- Mocked Adzuna browser: **passed**, including empty mandatory requirements,
  null coverage, provisional fit, blocked interest, unverified group, eligible
  candidate exclusion, true zero versus blank experience persistence, dedup,
  attribution, URL preservation, reload/mobile and error/empty states.
- All four JavaScript files passed syntax checks using installed Playwright's Node.
- API contract: **38 operations verified; 50 JSON examples parse**.
- Live HTTP smoke: **passed** (CRUD cleanup, health, matching, gaps and analytics).
- Working database comparison: **passed**, as described above.
- Existing imported external record: live browser confirms UNVERIFIED, visible
  requirement details and preserved original URL. Desktop screenshot was visually
  inspected: `CampusLink_v2/tests/artifacts/requirement-intelligence-desktop.png`.

One pre-existing Starlette TestClient/httpx deprecation warning remains. No dependency
was installed to suppress it. Browser write tests use temporary databases and uploads
with cooperative fixture shutdown. Live smoke cleans up its temporary CRUD records.
No real Adzuna search or live import was performed for this upgrade. Original external
links were checked for retained destinations; no live employer application was made.

## Known limitations

Rule extraction is conservative and incomplete for arbitrary prose, languages,
complex alternatives, compound skill-specific experience and unrecognized aliases.
Unknown education remains critical; even an apparent absence of a degree requirement
is not treated as verified unrestricted education. Branch/year fields not extracted
remain null, not invented restrictions. Snippets may omit additional mandatory
requirements; no current Adzuna snippet is certified complete. No full-listing
scraper, external verification service, review state machine or employer submission
was added. Professional experience and assessment inputs remain self-reported.
No authentication or authorization was introduced; role switching is presentation.
Small-dataset matching scans are not a large-scale recommendation engine.

## Exact run commands

From `C:\Users\SUHANA\Music\CAMPUSLINK`, use two PowerShell terminals.
Do not start duplicate servers if these ports already serve the app.

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Second terminal from the workspace root:

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory CampusLink_v2
```

Open http://127.0.0.1:5500. API docs: http://127.0.0.1:8000/docs.
Use existing backend environment configuration; never put credentials in frontend files.

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
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/polish_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/adzuna_flow.py
```
