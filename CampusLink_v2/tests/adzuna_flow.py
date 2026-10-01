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
    server=subprocess.Popen([str(ROOT/"backend/.venv/Scripts/python.exe"),str(Path(__file__).with_name("adzuna_fixture.py")),str(Path(tmp)/"stop"),str(test_port)],cwd=ROOT/"backend",env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
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
            nav("students");page.locator('[data-student="1"]').click()
            page.locator('#editProfile').click()
            expect(page.locator('#recordForm [name="professional_experience_years"]')).to_have_value('')
            page.locator('#recordForm [name="professional_experience_years"]').fill('0')
            page.locator('#saveRecord').click();expect(page.locator('#editorDialog')).not_to_be_visible()
            assert page.request.get(f'http://127.0.0.1:{test_port}/api/v1/students/1').json()['professional_experience_years']==0
            page.locator('#editProfile').click()
            expect(page.locator('#recordForm [name="professional_experience_years"]')).to_have_value('0')
            page.locator('#recordForm [name="professional_experience_years"]').fill('')
            page.locator('#saveRecord').click();expect(page.locator('#editorDialog')).not_to_be_visible()
            assert page.request.get(f'http://127.0.0.1:{test_port}/api/v1/students/1').json()['professional_experience_years'] is None
            nav("jobs")
            real=page.locator('#jobList [data-source-group="external"]')
            demo=page.locator('#jobList [data-source-group="demo"]')
            expect(real).to_contain_text('No saved external opportunities')
            assert not demo.evaluate('(e)=>e.open')
            assert page.locator('#jobList .gap-card:visible').count()==0
            assert demo.locator('.gap-card').count()==6
            assert demo.locator('.source-demo').count()==6
            demo.locator('summary').click()
            assert demo.locator('.gap-card:visible').count()==6
            demo.locator('summary').click()
            assert page.evaluate('state.dashboard.opportunity_sources.adzuna||0')==0
            assert not [r for r in requests if '/external/adzuna' in r[1]]
            page.locator('#externalSearchForm button').click()
            expect(page.locator('#externalState')).to_contain_text('Searching Adzuna')
            expect(page.locator('#externalResults .external-card')).to_have_count(1)
            expect(page.locator('#externalResults')).to_contain_text('Source: Adzuna')
            assert page.locator('#externalResults img[alt="Adzuna"]').count()==1
            link=page.locator('#externalResults a',has_text='View Original Listing').get_attribute('href')
            assert link.startswith('https://www.adzuna.in/land/ad/') and 'browser-test-id' not in link
            assert page.evaluate('state.jobs.length')==6
            page.locator('[data-external-import="0"]').click()
            expect(page.locator('#opportunity')).to_be_visible()
            expect(page.locator('#opportunityAnalysis')).to_contain_text('Provisional fit score:')
            expect(page.locator('#opportunityDetail')).to_contain_text('Fixture Python Engineer')
            expect(page.locator('#opportunityDetail')).to_contain_text('automated interpretations')
            jid=page.evaluate('state.jobId')
            assert page.evaluate('state.jobs.length')==7
            assert page.locator('#opportunityAnalysis tbody tr').count()==6
            expect(page.locator('#opportunityAnalysis')).to_contain_text('Docker')
            expect(page.locator('#opportunityAnalysis')).to_contain_text('Eligibility unverified')
            expect(page.locator('#opportunityAnalysis')).to_contain_text('Skill coverage unavailable')
            assert page.locator('#expressInterest').count()==0
            fit=page.request.get(f'http://127.0.0.1:{test_port}/api/v1/matching/fit?student_id=1&job_id={jid}').json()
            assert fit['skill_match_percentage'] is None and fit['provisional']
            assert fit['eligibility']['status']=='UNVERIFIED'
            dashboard=page.request.get(f'http://127.0.0.1:{test_port}/api/v1/analytics/dashboard').json()
            assert dashboard['unverified_matches']==dashboard['total_students']
            nav('home')
            external_metric=page.locator('#dashboardContent .insight-card').filter(has=page.locator('span',has_text='Real external opportunities'))
            expect(external_metric.locator('strong')).to_have_text('1')
            expect(page.locator('.latest-external')).to_contain_text('Fixture Python Engineer')
            assert page.locator('.latest-external .source-demo').count()==0
            expect(page.locator('.matching-insight')).to_contain_text('All stored matching data (includes demo opportunities)')
            nav('jobs')
            expect(real.locator('[data-card-match]')).to_contain_text('Eligibility unverified')
            expect(real.locator('[data-card-match]')).to_contain_text('Skill coverage unavailable')
            expect(real.locator('[data-card-match]')).to_contain_text(f"{fit['overall_fit_score']:.1f}%")
            assert real.locator('.source-demo').count()==0
            assert not demo.evaluate('(e)=>e.open')
            assert page.locator('#jobList .gap-card:visible').count()==1
            assert real.locator('a',has_text='View Original Listing').get_attribute('href')==link
            # Changing the profile must replace the card's backend result.
            nav('students');page.locator('[data-student="2"]').click();nav('jobs')
            second_fit=page.request.get(f'http://127.0.0.1:{test_port}/api/v1/matching/fit?student_id=2&job_id={jid}').json()
            expect(real.locator('[data-card-match]')).to_contain_text(f"{second_fit['overall_fit_score']:.1f}%")
            nav('students');page.locator('[data-student="1"]').click()
            nav('discovery');expect(page.locator('#discoveryState')).to_contain_text('jobs evaluated.',timeout=20000)
            expect(page.locator('#discoveryResults')).to_contain_text('Fixture Python Engineer')
            expect(page.locator('#discoveryResults')).to_contain_text('Adzuna')
            assert page.locator('#discoveryResults [data-source-group]').first.get_attribute('data-source-group')=='external'
            assert not page.locator('#discoveryResults [data-source-group="demo"]').evaluate('(e)=>e.open')
            expect(page.locator('#discoveryResults [data-source-group="demo"] summary')).to_contain_text('6 samples')
            assert page.locator('#discoveryResults [data-source-group="external"] .discovery-card').count()==1
            expect(page.locator('#discoveryResults [data-source-group="external"] .discovery-card')).to_contain_text('Provisional match:')
            expect(page.locator('#discoveryResults [data-source-group="external"] [data-match-group="Eligibility Unverified"]')).to_contain_text('Fixture Python Engineer')
            expect(page.locator('#discoveryResults [data-source-group="external"] [data-match-group="Eligible Matches"]')).not_to_contain_text('Fixture Python Engineer')
            page.locator('#roleSelect').select_option('officer');nav('jobs')
            page.locator('[data-candidates="'+str(jid)+'"]').click()
            expect(page.locator('#discoveryState')).to_contain_text('eligible candidates.',timeout=20000)
            expect(page.locator('#discoveryResults')).to_contain_text('No eligible candidates found')
            nav('jobs');page.locator('[data-external-import="0"]').click()
            expect(page.locator('#opportunity')).to_be_visible()
            expect(page.locator('#opportunityAnalysis')).to_contain_text('Provisional fit score:')
            assert page.evaluate('state.jobId')==jid and page.evaluate('state.jobs.length')==7
            records=page.request.get(f'http://127.0.0.1:{test_port}/api/v1/applications').json()
            assert len(records)==0
            page.reload(wait_until='networkidle');nav('jobs')
            expect(page.locator('#jobList')).to_contain_text('Fixture Python Engineer')
            assert page.locator('#jobList [data-job]').count()==7
            page.set_viewport_size({'width':390,'height':844})
            page.locator('#externalSearchForm button').click()
            expect(page.locator('#externalResults')).to_contain_text('Fixture Python Engineer')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(ART/'adzuna-mobile.png'),full_page=True)
            assert not errors,errors
            assert not console,console
            assert not [r for r in requests if r[2]>=400],requests
            assert 'browser-test-key' not in page.content() and 'browser-test-id' not in page.content()
            (ART/'adzuna-results.json').write_text(json.dumps({'result':'PASS','provider':'mocked, no live API in tests','checks':['explicit search/import','external first with no demo fallback','source-specific dashboard counts','collapsed labeled demos','profile-specific card matches','source and sanitized original URL','keyword skills','eligibility/fit/gaps','unverified interest blocked','Jobs for Me','Suitable Candidates','dedup refresh','persistence','demo retained','mobile','no console errors']},indent=2))
            print('PASS: Adzuna browser search/import, provenance, matching, gaps, unverified exclusion, Jobs for Me, candidates, dedup refresh, persistence, mobile, no credential exposure or console errors.')
            # Deliberate error/empty responses are test-only and need no real credentials.
            error_page=context.new_page();error_js=[]
            error_page.on('pageerror',lambda e:error_js.append(str(e)))
            error_page.route('http://127.0.0.1:8000/**',lambda r:r.continue_(url=r.request.url.replace(':8000/',f':{test_port}/')))
            error_page.goto(os.getenv('CAMPUSLINK_FRONTEND_URL','http://127.0.0.1:5500'),wait_until='networkidle')
            error_page.locator('[data-section="jobs"]').click()
            frontend_origin=page.evaluate('location.origin')
            pattern='**/api/v1/opportunities/external/adzuna?*'
            for status,message in [(503,'Adzuna is not configured.'),(429,'Adzuna rate limit reached.')]:
                error_page.route(pattern,lambda r,request,status=status,message=message:r.fulfill(status=status,content_type='application/json',body=json.dumps({'detail':message}),headers={'Access-Control-Allow-Origin':frontend_origin}))
                error_page.locator('#externalSearchForm button').click()
                expect(error_page.locator('#externalState')).to_contain_text(message)
                expect(error_page.locator('#externalSearchForm button')).to_be_enabled()
                error_page.unroute(pattern)
            error_page.route(pattern,lambda r:r.fulfill(status=200,content_type='application/json',body=json.dumps({'results':[],'skipped':0,'cached':False}),headers={'Access-Control-Allow-Origin':frontend_origin}))
            error_page.locator('#externalSearchForm button').click()
            expect(error_page.locator('#externalState')).to_contain_text('No usable listings returned')
            assert not error_js,error_js
            print('PASS: loading, unavailable, rate-limit, empty results and recovery controls.')
            browser.close()
    finally:
        (Path(tmp)/"stop").touch()
        server.wait(timeout=15);log.close()
