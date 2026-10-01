"""Read-only asset/routing/CORS checks against the actual Live Server engine.
Set CAMPUSLINK_FRONTEND_URL to the URL opened by VS Code Live Server.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

base=os.getenv('CAMPUSLINK_FRONTEND_URL','http://127.0.0.1:5501/CampusLink_v2/index.html')
parts=urlsplit(base)
origin=f'{parts.scheme}://{parts.netloc}'
folder=parts.path.rsplit('/',1)[0]+'/' if parts.path.endswith('.html') else parts.path.rstrip('/')+'/'
urls=[origin+folder,origin+folder+'index.html',origin.replace('127.0.0.1','localhost')+folder+'index.html']
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.getenv('CAMPUSLINK_BROWSER',r'C:\Program Files\Google\Chrome\Application\chrome.exe'),headless=True)
    for url in dict.fromkeys(urls):
        context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        page=context.new_page();errors=[];failed=[];responses=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('requestfailed',lambda r:failed.append(r.url) if r.failure!='net::ERR_ABORTED' else None)
        page.on('response',lambda r:responses.append((r.url,r.status)))
        page.goto(url,wait_until='networkidle')
        expect(page.locator('#connectionStatus')).to_have_text('Backend online')
        expect(page.locator('#dashboardContent')).to_contain_text('Real external opportunities')
        assert page.locator('script').evaluate_all('(xs)=>xs.some(x=>x.textContent.includes("WebSocket"))'),'Not served by Live Server'
        for relative in ['css/style.css','js/app.js','js/workflows.js','js/opportunities.js','js/external.js','assets/adzuna-logo.png']:
            assert page.request.get(origin+folder+relative).status==200,relative
        page.locator('[data-section="jobs"]').click()
        assert urlsplit(page.url).path==urlsplit(url).path
        assert page.url.endswith('#jobs')
        page.reload(wait_until='networkidle');expect(page.locator('#jobs')).to_be_visible()
        expect(page.locator('#jobList [data-source-group="external"]')).to_be_visible()
        if page.locator('#jobList [data-source-group="demo"]').count():
            assert not page.locator('#jobList [data-source-group="demo"]').evaluate('(e)=>e.open')
        assert not errors,errors
        assert not failed,failed
        assert not [(u,status) for u,status in responses if status>=400],responses
        results.append({'url':url,'result':'PASS','checks':['Live Server injection','real backend/CORS','relative assets','hash navigation/reload','source grouping','no console or network errors']})
        context.close()
    browser.close()
Path(__file__).with_name('artifacts').joinpath('live-server-results.json').write_text(json.dumps(results,indent=2))
print('PASS: Live Server directory/index URLs on 127.0.0.1 and localhost; assets, CORS, backend, navigation and console checks.')
