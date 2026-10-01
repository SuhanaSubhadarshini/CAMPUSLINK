"""Browser integration checks. Writes target a temporary backend database only.
Requires the actual frontend at :5500, backend at :8000, and Python Playwright.
Run from the workspace root with .frontend-test-env/Scripts/python.exe.
"""
import socket
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path(__file__).parent / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)
CHROME = os.getenv("CAMPUSLINK_BROWSER", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
URL = os.getenv("CAMPUSLINK_FRONTEND_URL", "http://127.0.0.1:5500")
from urllib.parse import urlsplit
FRONTEND_ORIGIN = "{0.scheme}://{0.netloc}".format(urlsplit(URL))
API = "http://127.0.0.1:8000"
checks = []

def record(message):
    checks.append(message)
    print("PASS:", message, flush=True)

def nav(page, section):
    if section in ["companies","readiness","roadmap"]:
        page.evaluate("go", section)
    else:
        page.locator('.nav-item[data-section="' + section + '"]').click()
    expect(page.locator("#" + section)).to_be_visible()

def match(page, sid, jid):
    nav(page, "matches")
    page.locator("#matchStudent").select_option(str(sid))
    page.locator("#matchJob").select_option(str(jid))
    page.locator("#fitBtn").click()
    expect(page.locator("#matchingResult")).to_contain_text("Overall Fit Score")

def capture(page, filename):
    page.evaluate("window.scrollTo({top:0,behavior:'instant'})")
    page.screenshot(path=str(ARTIFACTS / filename), full_page=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True)
    context = browser.new_context(viewport={"width":1440,"height":1000}, reduced_motion="reduce")
    page = context.new_page()
    errors, console_errors, requests = [], [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("response", lambda r: requests.append((r.request.method, r.url, r.status)) if ":8000/" in r.url else None)
    page.goto(URL, wait_until="networkidle")
    expect(page.locator("#connectionStatus")).to_have_text("Backend online")
    page.locator("#roleSelect").select_option("officer")
    expect(page.locator("#dashboardContent")).to_contain_text("Real external opportunities")
    assert page.locator("#studentList [data-student]").count() == len(page.request.get(API+"/api/v1/students?limit=500").json())
    assert page.locator("#jobList [data-job]").count() == len(page.request.get(API+"/api/v1/opportunities?limit=500").json())
    assert page.locator("#companyList [data-company]").count() == len(page.request.get(API+"/api/v1/companies?limit=500").json())
    assert page.locator("#placementList .offer-card").count() == len(page.request.get(API+"/api/v1/placements?limit=500").json())
    capture(page, "desktop-dashboard.png")
    record("Real dashboard, students, jobs, companies, placements and health load through browser CORS")
    nav(page,"students")
    page.locator('[data-student="1"]').click()
    expect(page.locator("#studentProfile")).to_contain_text("Ananya Mishra")
    page.locator('#studentProfile [data-go="jobs"]').click()
    page.locator('#jobList [data-job="1"]').click()
    expect(page.locator("#opportunityAnalysis")).to_contain_text("Fit score: 90.6")
    nav(page,"matches")
    page.locator("#eligibilityBtn").click()
    expect(page.locator("#matchingResult .status-pill:not(.source-badge)")).to_have_text("Eligible")
    expect(page.locator("#matchingResult .source-demo")).to_have_text("DEMO")
    page.locator("#fitBtn").click()
    expect(page.locator("#matchingResult")).to_contain_text("90.6 / 100")
    page.locator('#matchingResult [data-go="readiness"]').click()
    assert page.locator("#readinessResult .factor").count()==6
    expect(page.locator("#readinessResult")).to_contain_text("Contribution: 45.00 points")
    capture(page,"desktop-fit.png")
    record("Exact demo flow and backend fit 90.6 with all six components")
    match(page,6,2)
    expect(page.locator("#matchingResult .status-pill:not(.source-badge)")).to_have_text("Not eligible")
    nav(page,"roadmap")
    expect(page.locator("#gapResult")).to_contain_text("React")
    expect(page.locator("#gapResult")).to_contain_text("high priority")
    nav(page,"matches")
    page.locator("#matchStudent").select_option("10")
    expect(page.locator("#matchingResult")).to_be_empty()
    page.locator("#fitBtn").click()
    expect(page.locator("#matchingResult")).to_contain_text("graduation_year")
    record("Missing React gap, failed eligibility, and stale results cleared on selection changes")
    nav(page,"companies")
    page.locator('[data-company="1"]').click()
    expect(page.locator("#companyModal")).to_be_visible()
    expect(page.locator("#modalCompany")).to_have_text("Odisha Techworks")
    page.keyboard.press("Escape")
    expect(page.locator("#companyModal")).not_to_be_visible()
    nav(page,"offers")
    page.locator("#placementFilter").select_option("selected")
    expect(page.locator("#placementList")).to_contain_text("No placement records")
    record("Company profile modal and selected-student offer empty state")
    assert not errors, errors
    assert not console_errors, console_errors
    assert all(status<400 for _,_,status in requests), requests
    record("No console errors, JavaScript exceptions or failed API requests on the live demo flow")

    # Mutation tests run the current backend in an isolated temporary directory.
    with tempfile.TemporaryDirectory(prefix="campuslink-ui-") as tmp:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1",0)); test_port=listener.getsockname()[1]
        env=os.environ.copy()
        env.update(DATABASE_URL="sqlite:///"+(Path(tmp)/"test.db").as_posix(),UPLOAD_DIR=str(Path(tmp)/"uploads"),SEED_DEMO="true")
        log=open(Path(tmp)/"server.log","w")
        server=subprocess.Popen([str(ROOT/"backend/.venv/Scripts/python.exe"),str(Path(__file__).with_name("api_fixture.py")),str(Path(tmp)/"stop"),str(test_port)],
            cwd=ROOT/"backend",env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{test_port}/health",timeout=1)
                    break
                except Exception: time.sleep(.1)
            else: raise RuntimeError("Temporary backend did not start")
            test=context.new_page()
            write_errors=[]
            test.on("pageerror",lambda e:write_errors.append(str(e)))
            test.route(API+"/**",lambda route:route.continue_(url=route.request.url.replace(":8000/",f":{test_port}/")))
            test.goto(URL,wait_until="networkidle")
            nav(test,"students")
            test.locator('[data-student="6"]').click()
            test.locator("#resumeFile").set_input_files({"name":"resume.txt","mimeType":"text/plain","buffer":b"Python SQL React.js FastAPI"})
            test.locator('#resumeForm button').click()
            expect(test.locator("#resumeState")).to_contain_text("Resume uploaded")
            expect(test.locator("#resumeState")).to_contain_text("React")
            with test.expect_download() as download:
                test.locator("#downloadResume").click()
            assert Path(download.value.path()).read_bytes()==b"Python SQL React.js FastAPI"
            match(test,6,2)
            expect(test.locator("#matchingResult")).to_contain_text("100.0%")
            record("Real multipart TXT upload, extracted skills, binary download and refreshed skill coverage")
            nav(test,"offers")
            test.locator("#placementStudent").select_option("6")
            test.locator("#placementJob").select_option("6")
            test.locator('#placementForm input[name="package"]').fill("1.8")
            test.locator('#placementForm button').click()
            expect(test.locator("#placementFormState")).to_contain_text("created")
            expect(test.locator("#placementList .offer-card")).to_have_count(5)
            offer=test.locator('[data-placement-status="5"]')
            offer.locator("select").select_option("accepted")
            offer.locator("button").click()
            expect(test.locator("#statusMessage5")).to_have_text("Status saved.")
            expect(test.locator('#placementList .offer-card').last).to_contain_text("accepted")
            test.reload(wait_until="networkidle")
            expect(test.locator('[data-placement-status="5"] select')).to_have_value("accepted")
            test.locator("#placementStudent").select_option("6")
            test.locator("#placementJob").select_option("6")
            test.locator('#placementForm button').click()
            expect(test.locator("#placementFormState")).to_contain_text("Conflicting record")
            record("Real offer creation, persisted status PATCH, and useful 409 duplicate error")
            assert not write_errors,write_errors
            test.close()
        finally:
            (Path(tmp)/"stop").touch()
            server.wait(timeout=15);log.close()

    # Failure and empty states are intentionally injected only into test pages.
    broken=context.new_page()
    broken.route(API+"/**",lambda route:route.abort())
    broken.goto(URL,wait_until="networkidle")
    for id in ["dashboardState","analyticsState","studentsState","jobsState","companiesState","placementState","matchingState","readinessState","gapState"]:
        expect(broken.locator("#"+id)).to_contain_text("Unable to connect")
    broken.unroute(API+"/**")
    broken.locator('#dashboardState [data-retry]').click()
    expect(broken.locator("#dashboardContent")).to_contain_text("Students")
    record("Offline errors on every API-driven view, plus dashboard retry recovery")
    broken.close()
    empty=context.new_page()
    for resource in ["students","opportunities","companies","placements"]:
        empty.route(API+"/api/v1/"+resource+"?*",lambda route:route.fulfill(status=200,content_type="application/json",body="[]",headers={"Access-Control-Allow-Origin":FRONTEND_ORIGIN}))
    empty.goto(URL,wait_until="networkidle")
    for id in ["studentsState","jobsState","companiesState","placementState"]:
        expect(empty.locator("#"+id)).to_contain_text("No ")
    expect(empty.locator("#fitBtn")).to_be_disabled()
    record("Empty resource lists do not fall back to fake records or enable matching")
    empty.close()
    # Mobile navigation must expose all pages without horizontal document overflow.
    mobile=browser.new_context(viewport={"width":390,"height":844},is_mobile=True,device_scale_factor=1,reduced_motion="reduce")
    m=mobile.new_page();mobile_errors=[];m.on("pageerror",lambda e:mobile_errors.append(str(e)))
    m.goto(URL,wait_until="networkidle")
    m.locator("#roleSelect").select_option("officer")
    for section in ["home","students","jobs","companies","matches","offers","analytics","admin"]:
        nav(m,section)
        if section=="students":m.locator('[data-student="1"]').click()
        assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth"),section
    match(m,1,1)
    nav(m,"readiness")
    assert m.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    capture(m,"mobile-fit.png")
    assert not mobile_errors,mobile_errors
    record("390px mobile layout, all navigation items accessible, no horizontal overflow or JS errors")
    mobile.close();context.close();browser.close()
(ARTIFACTS/"results.json").write_text(json.dumps({"checks":checks,"live_api_responses":requests},indent=2),encoding="utf-8")
print("ALL",len(checks),"BROWSER CHECK GROUPS PASSED")
