# Adzuna external opportunity integration

## 1. Files changed

Backend: app/config.py (new), app/services/adzuna_service.py (new),
app/routes/adzuna.py (new), app/main.py, app/database.py, app/models.py,
app/schemas.py, .env.example, .gitignore, README.md, FRONTEND_API_GUIDE.md,
tests/conftest.py, tests/test_adzuna.py (new), tests/live_adzuna.py (new).

Frontend: index.html, js/app.js, js/workflows.js, js/opportunities.js,
js/external.js (new), css/style.css, README.txt, assets/adzuna-logo.png and
assets/ADZUNA_ATTRIBUTION.md (new), tests/adzuna_fixture.py and tests/adzuna_flow.py (new).
Root: .gitignore and this report. backend/.env is local ignored configuration;
backend/campuslink.before-adzuna.db is the local pre-migration backup. No package added.

## 2. New API endpoints

| Method | Endpoint | Behavior |
|---|---|---|
| GET | /api/v1/opportunities/external/adzuna | Read-only search: query, location, page, limit. India API; defaults software engineer / India / 1 / 10; max 20 per page. |
| POST | /api/v1/opportunities/import/adzuna | Explicit import/refresh of 1-20 references using the returned search_token. Returns created/updated counts and stored JobRead records. |

Search does not create companies/jobs. Import accepts only references from its recent
server-held result set, not arbitrary client-supplied listing data. Search tokens
expire after five minutes, can be evicted after 32 cached searches, and do not survive
restart. Identical searches reuse cached data without provider calls. A five-second
cooldown limits unique searches; a provider 429 sets a 60-second cooldown. No retries,
background scheduler, polling, Redis or extra provider. Cache/limits are per process.

## 3. Credential loading and protection

Backend config loads backend/.env, with existing shell environment taking precedence.
Only backend environment ADZUNA_APP_ID/ADZUNA_APP_KEY are read by the provider adapter.
The already-existing root .env contained these settings; only those entries were
copied into backend/.env without printing their values. Root .env is not loaded at
runtime. Restart after editing backend/.env. Empty .env.example placeholders and
root/backend ignore rules protect dotenv files. No credentials appear in frontend,
HTML, test fixtures, documentation, API output or application logging.

The HTTPS provider origin/path is fixed; redirects are disabled, request time is
bounded to 12 seconds and response size to 2 MiB. Standard-library transport avoids
HTTP client request-URL logging. Raw provider error bodies and exception messages are
never returned. Missing config is safe 503; authentication/access rejection is safe
503; rate limits 429; provider failures 502; timeout/connection failures 504.

A live discovery found that Adzuna places the APP ID in redirect_url's utm_source.
The adapter removes credential-bearing tracking/auth parameters before cache/storage/
response. It preserves the provider redirect destination and other tokens. Records
that echo credentials elsewhere are skipped. This intentional URL sanitization takes
precedence over byte-for-byte preservation of a URL containing a credential.

## 4. Normalization and storage

Job remains the single opportunity table; Company is reused. No new table. One
nullable JSON external_metadata column preserves source posting date, contract/time,
category, detected keywords, provider ID/country, source employer and last fetch time.
Job.created_at is local import time; source posted_at is separate and may be null.
The source label is adzuna and reference is in:<provider-id>. HTML markup is stripped
from snippets and rendered with escaping. A record without a usable title, company,
ID or safe original URL is skipped rather than assigned invented data.

A company name is matched with Unicode NFKC, casefold and collapsed whitespace.
New companies contain only the provided name; existing profile details are untouched.
Source names/categories are not treated as verified corporate information.
Unknown job type is represented as unknown, not invented full-time employment.
Vacancy counts remain null because the documented API does not supply a vacancy count.
Salary is not imported; this avoids presenting estimates/currency assumptions as pay.
No CGPA/year restrictions are inferred. New search listings are initially open;
there is no date-based expiry, automatic closure or guarantee that a vacancy remains.

## 5. Duplicate prevention and refresh

A country-prefixed stable source reference identifies the Job independently of its
company spelling. The existing source/company/reference constraint remains; a partial
unique Adzuna-reference index and BEGIN IMMEDIATE serialize database upserts.
Refresh updates source facts on the same ID and preserves company association, original
import date, officer-edited requirements, open/closed status and lifecycle records.
Preferred skill signals update only if still equal to the last extracted set.
Changing provider company names is reflected as Source employer in the details while
historical Job/Placement relationships stay intact. Refresh never deletes applications,
placements, companies or demo rows, and never reopens a manually closed listing.

## 6. Skills and honest matching limitations

The adapter reuses deterministic dictionary extraction and adds explicit technical
terms Deep Learning, TensorFlow and PyTorch locally. Resume extraction is unchanged.
Mentions from description snippets become preferred signals, not asserted mandatory
requirements. required_skills starts empty. Source notice explains the distinction.
No LLM, trained model or separate ranking formula was introduced.

IMPORTANT: existing matching semantics give 100% required coverage when the required
list is empty. With no CGPA/year restrictions, a student can pass configured eligibility
without having verified full employer requirements. The UI explicitly warns of this
on external cards, details, Jobs for Me and candidate ranking. An officer can use the
existing job PATCH API to review requirements. Unknown requirements must not be
presented as proof of suitability or employer approval.

## 7. Existing workflow integration

Imported open jobs automatically appear through the existing /opportunities list.
Jobs for Me, Suitable Candidates, eligibility, fit components, gaps, local interest,
offers and joining all use existing endpoints and the unchanged matching engine.
Every displayed external advert has Jobs by Adzuna linked-logo attribution and source
labels; original links are prominent. Search results stay distinct from stored
opportunities and demo records. Import & Analyze is explicit, and later imports reuse
the record. No employer application or message is sent by Express interest.
Dashboard metrics are unchanged and count stored records only, not search results.

## 8. Verification

- 29 backend tests passed, including configuration, normalization, cache/cooldown,
  unknown fields, malformed data, safe errors, credential echoes/tracking removal,
  duplicates, preserved company details, existing matching and application/offer links.
- All existing backend tests still pass. One existing Starlette TestClient/httpx
  deprecation warning remains.
- Existing browser smoke: all 10 groups passed.
- Dynamic browser Tests A-G passed.
- Opportunity lifecycle browser suite passed.
- Final polish browser suite passed, including Suhana's unchanged 56.3 demo.
- New Adzuna browser suite uses a test-only provider fixture and temporary SQLite:
  loading/search, source/link, import, fit/gaps/interest, Jobs for Me, candidates,
  refresh deduplication, persistence, retained demo, mobile and console checks.
  Deliberately injected unavailable/rate-limit/empty responses test recovery states.
- All four JavaScript files pass syntax checks.
- API guide: 38 operations match OpenAPI; all 50 JSON examples parse.
- Live HTTP smoke passed. Credential-value scan of frontend/backend source, docs,
  artifacts and placeholders passed without printing any secret values.
- Database comparison with pre-change snapshot found all original rows unchanged;
  live searches did not persist anything. Matching, resume skill extraction and
  application/placement route hashes remained unchanged.

Normal automated tests use empty or synthetic credentials and mocked provider transport.
They never call live Adzuna. The optional live_adzuna.py requires an explicit --live.

## 9. Live search outcome

Manually verified through the running backend on 2026-09-30:
query "python developer", location "India", page 1, limit 3.
HTTP 200, three usable listings, zero skipped, provider total_available 5240.
Returned titles: "Data scentist, python", "Associate Engineering Director", and
"Full Stack Python Engineer". Locations: Mumbai/Maharashtra, Hyderabad/Telangana,
and Bangalore/Karnataka. Provider spelling is preserved here. A senior role appeared;
there is no entry-level-only filter. These are observations from that search, not
hardcoded frontend content or guarantees that the same listings remain available.
The credentials-in-tracking issue was corrected and verified on all three URLs.
Live import was not performed on the working DB; imports/lifecycle were tested in
isolated databases. No fake jobs were inserted into the demo database.

## 10. Run and remaining limitations

Existing commands from the workspace root, in separate PowerShell terminals:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
python -m http.server 5500 --bind 127.0.0.1 --directory CampusLink_v2
```

Open http://127.0.0.1:5500 -> Opportunities -> External Job Opportunities.
The running backend already loaded the credentials during reload. Future dotenv
changes require restart. No frontend credentials or direct provider requests.

Tests from workspace root:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/verify_frontend_contract.py
.\.venv\Scripts\python.exe tests/live_smoke.py
# Optional: consumes one real provider request, no DB writes
.\.venv\Scripts\python.exe tests/live_adzuna.py --live --query "python developer" --location India
cd ..
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/browser_smoke.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/dynamic_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/opportunity_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/polish_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/adzuna_flow.py
```

India API only. Remote is passed as a geographic search, not a remote-only filter.
No all-internet coverage, continuous real-time feed, entry-level guarantee, automated
employer submission, authentication, salary prediction or automatic vacancy expiry.
Matching based on truncated descriptions remains provisional. Public deployment
would need access control/quota protection; this remains the existing local demo.

Official implementation references:
- https://developer.adzuna.com/docs/search
- https://developer.adzuna.com/activedocs
- https://developer.adzuna.com/swagger/spec/test2.json
- https://developer.adzuna.com/docs/terms_of_service

The official specification includes India and the used keyword/location/pagination
parameters. Attribution is implemented with the official logo. Adzuna's terms govern
publication and ongoing institutional analysis; non-publishing institutional use may
require a licence beyond the trial period. No claim of unrestricted ongoing use.
