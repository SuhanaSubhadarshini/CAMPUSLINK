# CAMPUSLINK Live Server compatibility report

## Root cause established by reproduction

The frontend's stylesheet, four classic scripts, Adzuna image and hash navigation
already use relative paths correctly. There are no ES-module imports, Vite/React
runtime requirements, npm build steps or domain-root asset paths to fix.

The installed Live Server 5.7.10 engine was started against the workspace root at
http://127.0.0.1:5501/CampusLink_v2/index.html. Before the fix, the page loaded all
scripts but produced seven CORS console errors: the backend allowed 5500, not 5501.
An HTTP Origin check confirmed the missing Access-Control-Allow-Origin response.
The frontend then displayed a misleading error insisting on frontend port 5500.

Port 5500 was already occupied by the earlier standalone static server, which serves
CampusLink_v2 as its root; /CampusLink_v2/index.html is therefore a 404 on that server.
It is not the same serving root as Live Server opened from the complete workspace.
No incorrect asset path was found, and asset paths were not unnecessarily changed.

## Minimal changes

- `.vscode/settings.json`: Live Server loopback host, workspace root `/`, port 5501,
  local-IP mode off. Backend/test/environment directories are excluded from live
  reload watching, preventing test artifacts and database changes from reloading pages.
- `backend/app/main.py`: CORS accepts full HTTP origins on localhost or 127.0.0.1
  with development ports. Existing explicit CORS_ORIGINS configuration, HTTP methods,
  headers and credentials-disabled policy remain. No wildcard origin, null origin,
  arbitrary hostname, LAN host or HTTPS origin is automatically enabled.
- `CampusLink_v2/js/app.js`: connection error explains how to start FastAPI and use
  Live Server without incorrectly requiring frontend port 5500. API URL remains
  http://127.0.0.1:8000/api/v1; health uses the same existing backend origin.
- `backend/tests/test_live_server_cors.py`: accepted/rejected-origin tests and an
  isolated fixed-profile score regression.
- All five `CampusLink_v2/tests/*_flow.py` / `browser_smoke.py` suites accept
  CAMPUSLINK_FRONTEND_URL, preserving their default URL and assertions. Mock CORS
  headers use the tested origin, not a hardcoded port or a URL containing a path.
- `CampusLink_v2/tests/live_server_smoke.py`: actual Live Server injection, relative
  asset, CORS, nested-path navigation/reload and console/network assertions.
- `CampusLink_v2/README.txt`, `backend/FRONTEND_API_GUIDE.md`,
  `CampusLink_v2/tests/VERIFICATION.md`, and this report document the setup.

The presentation test previously assumed an editable working profile always scored
56.3. That profile currently scores 84.3 with its current stored inputs. It now
asserts exact UI/backend score parity without changing the user's profile. The
original inputs have their own isolated test asserting backend score 56.25 (56.3
when displayed), 100% configured skill coverage, ELIGIBLE, and unchanged weights.
The original seeded 90.6 regression also remains. No test was removed or disabled.

No UI redesign, backend business-logic change, dependency, migration, record deletion,
matching/eligibility change, fake runtime response or provider change was introduced.

## Run through VS Code

Open `C:\Users\SUHANA\Music\CAMPUSLINK` as the VS Code workspace. In a terminal:

```powershell
cd C:\Users\SUHANA\Music\CAMPUSLINK\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If the backend already runs, use that process; restart it if it has not picked up
the new CORS configuration. Live Server itself does not launch FastAPI.

Right-click `CampusLink_v2/index.html` -> **Open with Live Server**.
Workspace URL:

http://127.0.0.1:5501/CampusLink_v2/index.html

The directory form also works:

http://127.0.0.1:5501/CampusLink_v2/

If Live Server chooses a different free port, use the URL it opens. HTTP loopback
ports are supported without another CORS edit. If only the frontend folder is opened
as the workspace, its served URL is `/index.html` or `/`; relative assets still work.
Do not use file://. No frontend build command is required.

## Verification results

- **65 backend tests passed**: the existing 54, ten CORS cases and one preserved
  configured-profile score regression. One pre-existing TestClient/httpx warning remains.
- **All five existing browser suites passed against port 5501 under /CampusLink_v2/index.html**:
  browser smoke (10 groups), dynamic flow (A-G), opportunity lifecycle, polish,
  mocked Adzuna search/import.
- Additional Live Server smoke passed on the directory URL, index.html URL, and
  localhost hostname. Confirmed injected Live Server WebSocket script, HTTP 200
  assets, real backend access, hash navigation/reload, source grouping, and no
  unexpected console, JavaScript, asset, module-loading, CORS or network errors.
- Existing flows cover dashboard metrics, external-first opportunity grouping,
  collapsed/labeled demos, profiles, both roles, Jobs for Me, eligible/not-eligible/
  unverified states, score explanations, gaps, resumes, applications and placements.
- Adzuna search/import uses mocked provider data in isolated temporary databases;
  attribution, original links, explicit import and duplicate handling are checked.
  No live Adzuna calls or working-database imports were made.
- API contract verifier and four JavaScript syntax checks passed.

The installed extension's actual `node_modules/live-server` engine was used,
including its injected reload script and workspace root/host/watch settings.
The VS Code context-menu click itself was not automated. The temporary verification
server is stopped after testing so VS Code can use its configured port.
Structured checks: `CampusLink_v2/tests/artifacts/live-server-results.json`.

Run browser verification from the workspace root while both servers run:

```powershell
$env:CAMPUSLINK_FRONTEND_URL='http://127.0.0.1:5501/CampusLink_v2/index.html'
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/browser_smoke.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/dynamic_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/opportunity_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/polish_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/adzuna_flow.py
.frontend-test-env\Scripts\python.exe CampusLink_v2/tests/live_server_smoke.py
```

## Remaining limits

FastAPI must run separately. This setup covers local HTTP loopback development,
not HTTPS, LAN/mobile-device hosting or deployment. Such origins require deliberate
backend configuration, and remote devices cannot reach this machine through their
own 127.0.0.1. Real Adzuna searches still depend on existing backend credentials and
provider availability. Requirement intelligence and provisional/unverified behavior
are unchanged. Live Server port changes also change browser localStorage origin,
so a selected profile/role may need to be selected again on a new port.
