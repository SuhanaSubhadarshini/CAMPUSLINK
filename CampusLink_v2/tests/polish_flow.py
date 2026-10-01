"""Read-only checks of final product presentation; no database writes."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ART=Path(__file__).parent/'artifacts'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.getenv('CAMPUSLINK_BROWSER',r'C:\Program Files\Google\Chrome\Application\chrome.exe'),headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    errors=[];console=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('console',lambda m:console.append(m.text) if m.type=='error' else None)
    page.goto(os.getenv('CAMPUSLINK_FRONTEND_URL','http://127.0.0.1:5500'),wait_until='networkidle')
    expect(page.locator('.hero')).to_contain_text('analyzes placement opportunities against student profiles')
    expect(page.locator('#dashboardContent')).to_contain_text('Matching Insight')
    d=page.evaluate('state.dashboard')
    expect(page.locator('.matching-insight')).to_contain_text(str(d['eligible_matches'])+' verified eligible student')
    expect(page.locator('[data-section="students"]')).to_contain_text('My Profile')
    assert page.evaluate('[assessmentText(null),assessmentText(undefined),assessmentText(0),assessmentText(85)]')==['Not assessed','Not assessed','0 / 100','85 / 100']
    assert page.evaluate('sourceLabel("legacy")')=='Placement database record'
    students=page.request.get('http://127.0.0.1:8000/api/v1/students?limit=500').json()
    jobs=page.request.get('http://127.0.0.1:8000/api/v1/opportunities?limit=500').json()
    s=next(s for s in students if 'suhana' in s['name'].lower())
    j=next(j for j in jobs if 'generative ai engineer' in j['title'].lower())
    current_fit=page.request.get(f"http://127.0.0.1:8000/api/v1/matching/fit?student_id={s['id']}&job_id={j['id']}").json()
    expected_score=page.evaluate('(n)=>n.toFixed(1)',current_fit['overall_fit_score'])
    assert current_fit['eligibility']['eligible']
    assert current_fit['skill_match_percentage']==100
    page.locator('[data-section="students"]').click();page.locator('[data-student="'+str(s['id'])+'"]').click()
    page.locator('[data-section="roadmap"]').click()
    expect(page.locator('#gapChoices [data-gap-job]')).to_have_count(len(jobs),timeout=20000)
    page.locator('[data-gap-job="'+str(j['id'])+'"]').click()
    expect(page.locator('#gapResult')).to_contain_text('100.0%')
    page.locator('[data-section="discovery"]').click()
    expect(page.locator('#discoveryState')).to_contain_text('jobs evaluated.',timeout=20000)
    source='external' if j['source']=='adzuna' else 'demo' if j['source']=='demo' else 'placement'
    source_group=page.locator('#discoveryResults [data-source-group="'+source+'"]')
    assert source_group.locator('.match-group').count()==4
    expect(source_group.locator('[data-match-group="Eligible Matches"]')).to_contain_text(j['title'])
    expect(source_group.locator('[data-match-group="Eligible Matches"]')).to_contain_text(expected_score+' / 100')
    assert page.locator('#discoveryResults [data-source-group]').first.get_attribute('data-source-group')=='external'
    assert not page.locator('#discoveryResults [data-source-group="demo"]').evaluate('(e)=>e.open')
    page.locator('#discoveryResults [data-job="'+str(j['id'])+'"]').click()
    expect(page.locator('#opportunityAnalysis')).to_contain_text('Fit score: '+expected_score+' / 100')
    expect(page.locator('#opportunityAnalysis')).to_contain_text('Eligible')
    expect(page.locator('#opportunityAnalysis')).to_contain_text('100.0%')
    page.locator('#roleSelect').select_option('officer')
    expect(page.locator('[data-section="students"]')).to_contain_text('Student Profiles')
    page.locator('[data-section="students"]').click()
    expect(page.locator('#students h1')).to_have_text('Student Profiles')
    page.set_viewport_size({'width':390,'height':844});page.locator('#roleSelect').select_option('student')
    for section in ['home','students','jobs','roadmap','offers']:
        page.locator('[data-section="'+section+'"]').click()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),section
    page.locator('[data-section="roadmap"]').click()
    expect(page.locator('#gapChoices [data-gap-job]')).to_have_count(len(jobs),timeout=20000)
    page.screenshot(path=str(ART/'polish-skill-gaps-mobile.png'),full_page=True)
    assert not errors,errors
    assert not console,console
    print('PASS: value proposition, actual insight counts, assessment null/zero handling, source label, role labels, grouped matching, direct gaps, current saved profile/backend score parity, mobile, no console errors.')
    browser.close()
