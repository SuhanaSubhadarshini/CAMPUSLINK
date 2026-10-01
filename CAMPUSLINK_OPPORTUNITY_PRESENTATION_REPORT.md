# CAMPUSLINK opportunity presentation report

## What changed

Student Opportunities, Jobs for Me and Skill Gaps now present **Real Opportunities**
first, using the backend's existing `source` field. External listings show company,
location, known type, backend match percentage, eligibility, matched/missing skills,
match details, Adzuna attribution and the original listing link. Without a selected
profile, the card asks for one instead of inventing a match.

Jobs for Me groups by provenance before eligibility. Within each source, eligible,
unverified and unmet-requirement groups remain distinct. A high demo score cannot
move a fictional job above real external listings. Scores remain independent of
eligibility, including when an ineligible candidate views an explanation.

## Classification and data preservation

| Existing source | Presentation |
| --- | --- |
| `adzuna` | Real Opportunities; REAL / EXTERNAL - Adzuna badge |
| `demo` | Demo Opportunities; DEMO badge and fictional-sample explanation |
| `manual`, `json_import`, `legacy` | Separate Placement Cell Opportunities; source label and externally unverified availability |

Demo sections are collapsed for students and accessible for controlled demonstrations.
Officers can see them expanded; an explicit demo-source filter also opens the section.
No job titles, company names or IDs determine classification. No manual/legacy record
is relabeled as a verified external vacancy.

**No backend changes, migration, deletion or new dependency.** File fingerprints
confirmed all 28 backend Python/JSON implementation files were unchanged. Database checks confirmed all 11 students,
6 companies, 8 jobs, 5 placements and 0 applications remain. All business fields and
six demo jobs are intact. Starting the existing backend applied its pending
requirement-intelligence metadata refresh to the one Adzuna row: analysis version
2 became 3 and the old notice was updated. Reversing only those two metadata fields
in memory exactly reconstructed the pre-task jobs fingerprint. Every other value
and all other table fingerprints are unchanged. No new migration was introduced.
Evidence: `CampusLink_v2/tests/artifacts/opportunity-presentation-preservation.json`.

## Dashboard and presentation

The primary count includes saved open Adzuna opportunities only. External matching
counts use existing backend per-job eligibility totals for those open Adzuna jobs.
All-source totals explicitly disclose demo profiles/opportunities/offers. Officer
analytics is labeled as all stored data, including demonstrations, not verified
real-world placement statistics.

Latest Real Opportunities uses open external records and never falls back to demo
vacancies. Placement-cell and demo records appear in separate expandable sections.
Demo/source badges also follow standalone match explanations, candidate views,
job selectors, skill gaps, applications and offers.

Advanced search controls are expandable. Students do not see source reference IDs
or import timestamps in normal opportunity details. Officer source-record details
remain expandable. Requirement evidence stays under an explanation disclosure.
Saved listings are not a promise of current availability; the original link remains
prominent. No new vacancy data, companies, activities or statistics were generated.

## Files changed

- `CampusLink_v2/js/opportunities.js`: shared source grouping/badges, external-card
  backend match loading, source-aware details, skills and application presentation.
- `CampusLink_v2/js/workflows.js`: source-first Jobs for Me, fit display for all
  eligibility states and candidate provenance.
- `CampusLink_v2/js/app.js`: source-specific dashboard, explicitly scoped analytics,
  profile-change refresh, and provenance on match/offer views and selectors.
- `CampusLink_v2/js/external.js`: cleaner expandable source analysis and import wording.
- `CampusLink_v2/index.html`, `css/style.css`: secondary demos, primary cards,
  compact search options, responsive source sections and card spacing.
- `CampusLink_v2/tests/browser_smoke.py`, `dynamic_flow.py`, `polish_flow.py`,
  `adzuna_flow.py`: precise source/eligibility selectors and stronger hierarchy checks.
- `CampusLink_v2/README.txt`, `tests/VERIFICATION.md`, this report and test artifacts.

## Verification

| Check | Result |
| --- | --- |
| All backend tests | 54 passed |
| Browser smoke | All 10 groups passed |
| Dynamic profile/browser flow | Tests A-G passed |
| Opportunity lifecycle/browser flow | Passed |
| Presentation/polish browser flow | Passed |
| Mocked Adzuna search/import browser flow | Passed |
| Four JavaScript syntax checks | Passed |
| API contract | 38 operations verified; 50 JSON examples parse |
| Backend fingerprints / record preservation | Backend unchanged; all records preserved; only the existing startup metadata refresh described above |

Browser tests retain exact eligible/not-eligible assertions and demo scores 90.6
and 56.3. Tests were adapted to distinguish the new source badge from the eligibility
badge and to assert eligibility groups within their source section; no assertions
were removed to conceal failures.

Additional assertions verify: no real-job fallback when only demo data exists;
all six demo records still accessible; demos collapsed by default; external import
requires explicit selection; external count excludes demos; external cards update
when the profile changes; real listings precede demo matches; unverified stays out
of verified eligible groups; missing requirements never produce 100% coverage;
original URL/attribution, dedup, reload and mobile behavior remain intact.

Browser mutations use isolated temporary databases and uploads. Adzuna search/import
was tested with mocked provider responses, without live provider calls or working
imports. The existing real imported opportunity was also checked visually. Screenshots
are `real-opportunities-desktop.png`, `real-opportunities-mobile.png` and
`real-opportunities-dashboard.png` under `CampusLink_v2/tests/artifacts/`.

Adzuna integration and requirement intelligence are preserved. Matching weights
remain 45/15/15/10/10/5; no scoring formula exists in the new frontend presentation.
Incomplete descriptions remain UNVERIFIED unless a known requirement fails.
No authentication was added; officer/student selection remains a presentation choice.
The pre-existing Starlette TestClient/httpx deprecation warning remains.
