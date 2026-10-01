# Current verification: VS Code Live Server

65 backend tests pass. All five browser suites pass with
CAMPUSLINK_FRONTEND_URL=http://127.0.0.1:5501/CampusLink_v2/index.html.
Additional live_server_smoke.py verifies directory/index URLs, localhost and
127.0.0.1, assets, actual Live Server injection, hash navigation/reload and CORS.
Provider calls are mocked; browser writes use isolated databases.
The editable-profile polish check uses current backend score parity; the original
56.25 backend / 56.3 display scenario is preserved in an isolated regression.
See ../../CAMPUSLINK_LIVE_SERVER_REPORT.md for evidence, commands and limitations.

# Previous verification: external opportunities first

- 54 backend tests passed; backend implementation files are unchanged.
- All five browser suites passed: smoke (10 groups), dynamic (A-G), opportunity lifecycle,
  polish and the strengthened mocked Adzuna flow.
- Source separation, collapsed demo sections, demo access, external-only counts,
  source-first matching, all eligibility states, profile-dependent card matches,
  original URL/attribution, explicit import/dedup, mobile and console checks passed.
- Four JavaScript syntax checks passed; contract verifier confirms 38 operations
  and 50 parseable JSON examples.
- All original records preserved. Existing backend startup refreshed only the one
  external analysis version and notice from the prior requirement-intelligence upgrade.
- Detailed current report: ../../CAMPUSLINK_OPPORTUNITY_PRESENTATION_REPORT.md.
- Evidence: artifacts/opportunity-presentation-preservation.json and real-opportunities-*.png.

The previous verification notes below describe earlier milestones.

# Historical product-alignment verification

All checks passed after product alignment:

- Backend: 13 tests, including opportunity ingestion, application lifecycle and migrations.
- browser_smoke.py: all 10 check groups.
- dynamic_flow.py: Tests A-G covering custom profiles, arbitrary skills, both matching directions, resume review, persistence and mobile.
- opportunity_flow.py: import/filter/details, interest through selection/offer/joining, persistence, real dashboard updates, closing and mobile.
- All three frontend JavaScript files pass syntax checking.
- No unexpected browser console errors or JavaScript exceptions.
- Live HTTP smoke passes.
- verify_frontend_contract.py: all 36 operations match OpenAPI and all 47 JSON blocks parse.
- Database comparison with pre-change snapshot: original 11 students, 5 companies, 7 jobs and 4 placements preserved exactly.

The browser suites use installed Chrome and the existing separate Playwright environment. Persistent test writes target temporary SQLite databases; live smoke deletes its own records. One pre-existing Starlette TestClient/httpx deprecation warning remains.

See ../../PRODUCT_ALIGNMENT_REPORT.md for the complete report and exact commands. Screenshots/results are generated under artifacts/ (ignored).


## Historical Adzuna integration verification

29 backend tests pass. Existing browser_smoke, dynamic_flow, opportunity_flow and
polish_flow pass. New adzuna_flow passes with test-only mocked provider responses,
including explicit search/import, dedup refresh, existing matching/interest, mobile,
loading/unavailable/rate-limit/empty states and no unexpected console errors.
All four frontend scripts pass syntax checks. API contract: 38 operations and 50
parseable JSON examples. Live HTTP smoke passes. Manual live Adzuna India search
returned three usable listings; no live import was performed on the working DB.
Existing rows were preserved. See ../../ADZUNA_INTEGRATION_REPORT.md for details.
