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
            def fill(name,value):page.locator('#recordForm [name="'+name+'"]').fill(str(value))
            def skill(name,value):
                page.locator("#tagInput-"+name).fill(value);page.locator("#tagInput-"+name).press("Enter")
            def save():
                page.locator("#saveRecord").click()
                expect(page.locator("#editorDialog")).not_to_be_visible(timeout=15000)
            nav("students");page.locator("#addStudent").click()
            fill("name","Test Dynamic Student");fill("email","dynamic.browser@example.com");fill("degree","B.Tech");fill("department","CSE")
            fill("cgpa","8.2");fill("graduation_year","2026");fill("preferred_role","Computer Vision Engineer")
            for key,value in [("coding_score",85),("aptitude_score",80),("communication_score",82)]:fill(key,value)
            for s in ["Computer Vision","PyTorch","OpenCV"]:skill("skills",s)
            fill("projects","Custom vision project");save()
            expect(page.locator("#studentProfile")).to_contain_text("Test Dynamic Student")
            expect(page.locator("#studentProfile")).to_contain_text("Computer Vision Engineer")
            sid=page.locator("#matchStudent").input_value()
            assert int(sid)>10
            page.locator("#roleSelect").select_option("officer");nav("admin");page.locator("#addJob").click()
            fill("title","Computer Vision Engineer")
            page.locator('#recordForm [name="company_id"]').select_option("new")
            fill("company_name","Dynamic Vision Labs");fill("company_industry","Computer Vision")
            fill("minimum_cgpa","7");fill("location","Bhubaneswar")
            for s in ["Computer Vision","PyTorch","OpenCV"]:skill("required_skills",s)
            save()
            card=page.locator("#jobList .gap-card").filter(has=page.locator("h3",has_text="Computer Vision Engineer"))
            jid=card.locator("[data-job]").get_attribute("data-job")
            assert int(jid)>6
            card.locator("[data-candidates]").click()
            expect(page.locator("#discoveryState")).to_contain_text("eligible candidates.",timeout=20000)
            expect(page.locator("#discoveryResults")).to_contain_text("Test Dynamic Student")
            expect(page.locator("#discoveryResults .discovery-card")).to_have_count(1)
            page.locator("#discoveryResults [data-explain-student]").click()
            expect(page.locator("#opportunity")).to_be_visible()
            expect(page.locator("#opportunityAnalysis")).to_contain_text("Fit score:")
            expect(page.locator("#readinessResult")).to_contain_text("Test Dynamic Student")
            assert page.locator("#readinessResult .factor").count()==6
            nav("students");page.locator("#suitableJobs").click()
            expect(page.locator("#discoveryState")).to_contain_text("jobs evaluated.",timeout=20000)
            expect(page.locator("#discoveryResults .discovery-card")).to_have_count(7)
            expect(page.locator("#discoveryResults .discovery-card").first).to_contain_text("Computer Vision Engineer")
            # Correct skills and preference; a saved custom edit must affect eligibility/gaps.
            nav("students");page.locator("#editProfile").click()
            fill("preferred_role","Generative AI Engineer")
            page.get_by_role("button",name="Remove OpenCV",exact=True).click();save()
            nav("matches");page.locator("#matchStudent").select_option(sid);page.locator("#matchJob").select_option(jid)
            page.locator("#fitBtn").click()
            expect(page.locator("#matchingResult")).to_contain_text("66.7%")
            expect(page.locator("#matchingResult")).to_contain_text("opencv")
            expect(page.locator("#matchingResult .status-pill:not(.source-badge)")).to_have_text("Not eligible")
            page.reload(wait_until="networkidle")
            nav("students")
            expect(page.locator("#studentProfile")).to_contain_text("Test Dynamic Student")
            expect(page.locator("#studentProfile")).to_contain_text("Generative AI Engineer")
            nav("jobs")
            expect(page.locator("#jobList")).to_contain_text("Computer Vision Engineer")
            nav("home")
            expect(page.locator("#dashboardContent")).to_contain_text("Students")
            totals=page.evaluate("state.dashboard")
            assert (totals["total_students"],totals["total_companies"],totals["total_jobs"])==(11,5,7)
            # Resume extraction is reviewable: remove Python and retain a custom skill.
            nav("students")
            page.locator("#resumeFile").set_input_files({"name":"review.txt","mimeType":"text/plain","buffer":b"Python SQL"})
            page.locator("#resumeForm button").click()
            expect(page.locator("#resumeState")).to_contain_text("Resume uploaded")
            page.locator("#editProfile").click()
            page.get_by_role("button",name="Remove Python",exact=True).click()
            skill("skills","My Custom Research Skill");save()
            response=page.request.get(f"http://127.0.0.1:{test_port}/api/v1/students/"+sid).json()
            assert response["extracted_skills"]==["SQL"]
            assert "My Custom Research Skill" in response["skills"]
            # Mobile editor and custom inputs.
            page.set_viewport_size({"width":390,"height":844})
            page.locator("#editProfile").click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(ART/"mobile-profile-editor.png"),full_page=True)
            page.locator("#cancelEditor").click()
            # Live ranking after edit excludes the candidate until the missing skill is added back.
            nav("jobs");page.locator('[data-candidates="'+jid+'"]').click()
            expect(page.locator("#discoveryResults")).to_contain_text("No eligible candidates",timeout=20000)
            nav("students");page.locator("#editProfile").click();skill("skills","OpenCV");save()
            nav("jobs");page.locator('[data-candidates="'+jid+'"]').click()
            expect(page.locator("#discoveryResults")).to_contain_text("Test Dynamic Student",timeout=20000)
            page.set_viewport_size({"width":1440,"height":1000})
            page.screenshot(path=str(ART/"dynamic-candidates.png"),full_page=True)
            assert not errors,errors
            assert not console,console
            assert not [r for r in requests if r[2]>=400],requests
            (ART/"dynamic-results.json").write_text(json.dumps({"student_id":sid,"job_id":jid,"totals":totals,"javascript_errors":errors,"console_errors":console,"request_count":len(requests),"result":"PASS: create custom profile/company/job; eligibility/rank/explanation; suitable jobs; partial gaps; edits; resume review; reload persistence; mobile form"},indent=2),encoding="utf-8")
            print("PASS: Dynamic browser Tests A-G; new student",sid,"new job",jid,"custom company; edits, rankings, gaps, resume review, reload, mobile; no unexpected console errors.")
            browser.close()
    finally:
        (Path(tmp)/"stop").touch()
        server.wait(timeout=15);log.close()
