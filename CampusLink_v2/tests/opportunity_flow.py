"""Real browser + unchanged API transport; temporary SQLite for create/edit tests."""
import socket
import json,os,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
ART=Path(__file__).parent/"artifacts";ART.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="campuslink-dynamic-") as tmp:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1",0)); test_port=listener.getsockname()[1]
    env=os.environ.copy()
    env.update(DATABASE_URL="sqlite:///"+(Path(tmp)/"dynamic.db").as_posix(),UPLOAD_DIR=str(Path(tmp)/"uploads"),SEED_DEMO="true")
    log=open(Path(tmp)/"server.log","w")
    server=subprocess.Popen([str(ROOT/"backend/.venv/Scripts/python.exe"),str(Path(__file__).with_name("api_fixture.py")),str(Path(tmp)/"stop"),str(test_port)],cwd=ROOT/"backend",env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        for _ in range(100):
            try:urllib.request.urlopen(f"http://127.0.0.1:{test_port}/health",timeout=1);break
            except Exception:time.sleep(.1)
        else:raise RuntimeError("Test backend failed to start")
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.getenv("CAMPUSLINK_BROWSER",r"C:\Program Files\Google\Chrome\Application\chrome.exe"),headless=True)
            context=browser.new_context(viewport={"width":1440,"height":1000},reduced_motion="reduce")
            page=context.new_page();errors=[];console=[];requests=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("console",lambda m:console.append(m.text) if m.type=="error" else None)
            page.on("response",lambda r:requests.append([r.request.method,r.url,r.status]) if f":{test_port}/" in r.url else None)
            page.route("http://127.0.0.1:8000/**",lambda r:r.continue_(url=r.request.url.replace(":8000/",f":{test_port}/")))
            page.goto(os.getenv("CAMPUSLINK_FRONTEND_URL","http://127.0.0.1:5500"),wait_until="networkidle")
            def nav(id):page.locator('.nav-item[data-section="'+id+'"]').click()
            nav("students");page.locator('[data-student="7"]').click()
            assert not page.locator('[data-section="admin"]').is_visible()
            page.locator("#roleSelect").select_option("officer");nav("admin")
            payload={"opportunities":[{"company_id":1,"title":"Imported Research Opportunity","required_skills":["Python","SQL"],"preferred_skills":["Custom Research Skill"],"minimum_cgpa":7,"vacancy_count":4,"source_reference":"browser-feed-1","location":"Remote"}]}
            page.locator("#importJSON").fill(json.dumps(payload));page.locator('#importForm button').click()
            expect(page.locator("#importState")).to_contain_text("1 opportunities imported")
            expect(page.locator("#adminOpportunities")).to_contain_text("Imported Research Opportunity")
            imported=page.request.get(f"http://127.0.0.1:{test_port}/api/v1/opportunities?source=json_import").json()[0];jid=imported["id"]
            assert imported["vacancy_count"]==4 and imported["created_at"]
            nav("home");expect(page.locator("#dashboardContent")).to_contain_text("Imported Research Opportunity")
            assert page.evaluate("state.dashboard.available_opportunities")==7
            page.locator("#roleSelect").select_option("student")
            nav("jobs");page.locator('#opportunityFilters [name="source"]').select_option("json_import")
            page.locator('#opportunityFilters [type="submit"]').click()
            expect(page.locator('#jobList .gap-card')).to_have_count(1)
            page.locator('#jobList [data-job]').click()
            expect(page.locator('#opportunityAnalysis')).to_contain_text("Fit score:")
            expect(page.locator('#opportunityDetail')).to_contain_text("JSON import")
            expect(page.locator('#opportunityAnalysis')).to_contain_text("custom research skill")
            assert page.locator('#opportunityAnalysis tbody tr').count()==6
            fit=page.request.get(f"http://127.0.0.1:{test_port}/api/v1/matching/fit?student_id=7&job_id={jid}").json()
            expect(page.locator('#opportunityAnalysis')).to_contain_text(f'{fit["overall_fit_score"]:.1f}')
            page.locator('#expressInterest').click();expect(page.locator('#interestState')).to_contain_text("Interest recorded")
            nav("offers");expect(page.locator('#applicationList')).to_contain_text("interested")
            assert not page.locator('#placementForm').is_visible()
            page.reload(wait_until="networkidle");expect(page.locator('#applicationList')).to_contain_text("Imported Research Opportunity")
            page.locator('#roleSelect').select_option("officer")
            for stage in ["shortlisted","interview","selected"]:
                page.locator('#applicationList select').select_option(stage)
                page.locator('#applicationList form button').click()
                expect(page.locator('#applicationState')).not_to_contain_text("Loading")
                expect(page.locator('#applicationList select')).to_have_value(stage)
                page.wait_for_function("applications[0]?.status === '"+stage+"'")
            page.locator('[data-offer-student]').click()
            expect(page.locator('#placementStudent')).to_have_value("7")
            expect(page.locator('#placementJob')).to_have_value(str(jid))
            page.locator('#placementForm [name="package"]').fill("8")
            page.locator('#placementForm button').click();expect(page.locator('#placementFormState')).to_contain_text("created")
            offer=page.locator('[data-placement-status="5"]');offer.locator('select').select_option("joined");offer.locator('button').click()
            expect(page.locator('#applicationList')).to_contain_text("Offer: joined")
            page.reload(wait_until="networkidle");expect(page.locator('#applicationList')).to_contain_text("Offer: joined")
            nav("home");assert page.evaluate("state.dashboard.placed_students")==4
            assert page.evaluate("state.dashboard.application_statistics.selected")==1
            nav("admin");page.locator('[data-availability="'+str(jid)+'"]').click()
            expect(page.locator('[data-availability="'+str(jid)+'"]')).to_have_text("Reopen")
            nav("jobs");page.locator('#opportunityFilters [name="source"]').select_option("json_import")
            page.locator('#opportunityFilters [type="submit"]').click();expect(page.locator('#jobList')).to_contain_text("No available opportunities")
            page.locator('#opportunityFilters [name="source"]').select_option("")
            page.locator('#opportunityFilters [type="submit"]').click();expect(page.locator('#jobList .gap-card')).to_have_count(6)
            nav("home");assert page.evaluate("state.dashboard.available_opportunities")==6
            assert page.locator('#drives,#assistant').count()==0
            assert page.locator('#dashboardContent .insight-card').count()==4
            page.set_viewport_size({"width":390,"height":844});nav("admin")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(ART/"opportunity-admin-mobile.png"),full_page=True)
            assert not errors,errors
            assert not console,console
            assert not [r for r in requests if r[2]>=400],requests
            (ART/"opportunity-results.json").write_text(json.dumps({"result":"PASS","checks":["JSON import/provenance/vacancies","backend filters","eligible details and exact backend score","real skill gaps","student interest persistence","officer stages","offer and joined linkage","closed opportunity exclusion","real dashboard counters","role navigation","mobile layout","no fabricated screens","no console errors"]},indent=2))
            print("PASS: Opportunity import, filtering, analysis, interest, shortlist/interview/selected, offer/joining, persistence, dashboard, closing and mobile; no console errors.")
            browser.close()
    finally:
        (Path(tmp)/"stop").touch()
        server.wait(timeout=15);log.close()
