from types import SimpleNamespace
import pytest
from app.services.requirement_extractor import extract_requirements, backfill
from app.services.matching_service import eligibility, skill_gap, match


def student(**extra):
    values=dict(id=1,skills=['Python'],extracted_skills=[],degree='B.Tech',department='CSE',graduation_year=2026,cgpa=8,professional_experience_years=0,coding_score=80,aptitude_score=80,communication_score=80,projects=[],certifications=[])
    values.update(extra)
    return SimpleNamespace(**values)


def job(description='', **extra):
    values=dict(id=1,title='Engineer',description=description,source='adzuna',external_metadata={'description_is_snippet':False},job_type='unknown',required_skills=[],preferred_skills=[],minimum_cgpa=0,graduation_year=None)
    values.update(extra)
    return SimpleNamespace(**values)


def full(experience='0 years experience required', degree='B.Tech'):
    return f'Python required. {experience}. {degree} degree required.'


def test_empty_external_not_eligible_or_perfect():
    j=job()
    e=eligibility(student(),j)
    assert e['status']=='UNVERIFIED' and not e['eligible']
    assert skill_gap(student(),j)['skill_match_percentage'] is None
    f=match(student(),j)
    assert f['provisional'] and f['explanation']['components']['skills']['score'] is None
    assert f['explanation']['components']['skills']['contribution']==0
    assert [c['weight_percent'] for c in f['explanation']['components'].values()]==[45,15,15,10,10,5]


@pytest.mark.parametrize('description,profile,status',[
    (full(),{},'ELIGIBLE'),
    (full('No experience required; freshers welcome'),{},'ELIGIBLE'),
    (full('3 years professional experience required'),{},'NOT_ELIGIBLE'),
    (full('3 years professional experience required'),{'professional_experience_years':None},'UNVERIFIED'),
    (full(),{'skills':[]},'NOT_ELIGIBLE'),
    (full(),{'degree':'B.E.'},'ELIGIBLE'),
    (full('0 years experience required','MCA'),{},'NOT_ELIGIBLE'),
    (full('Some experience required'),{},'UNVERIFIED'),
    ('Python or Java required. 0 years experience required. B.Tech degree required.',{},'UNVERIFIED'),
    (full()+' Graduation batch 2025 only.',{},'NOT_ELIGIBLE'),
    (full()+' Mechanical engineering branch required.',{},'NOT_ELIGIBLE'),
    (full()+' Relevant field required.',{},'UNVERIFIED'),
])
def test_decisions(description,profile,status):
    e=eligibility(student(**profile),job(description))
    assert e['status']==status
    assert e['eligible']==(status=='ELIGIBLE')
    assert skill_gap(student(**profile),job(description))['eligibility_status']==status


@pytest.mark.parametrize('phrase,bounds', [('0-1 years experience',(0,1)),('1\u20132 years experience',(1,2)),('2 to 3 years experience',(2,3)),('3-5 years experience',(3,5)),('5+ years experience',(5,None)),('Minimum 2 years experience',(2,None)),('Maximum 4 years experience',(None,4))])
def test_experience_ranges(phrase,bounds):
    a=extract_requirements(phrase)
    assert (a['minimum_experience'],a['maximum_experience'])==bounds


def test_evidence_boundaries_optional_and_posting_date():
    a=extract_requirements('Python required. Docker preferred. Excellent communication. Posted 2026-09-20. 3-5 years experience required. B.Tech degree required.',title='Python Engineer')
    assert a['required_skills']==['Python'] and 'Docker' in a['preferred_skills']
    assert 'C' not in a['technical_skills'] and a['graduation_years'] is None
    assert a['job_category']=='Experienced professional'
    assert any(e['method']=='explicit' for e in a['evidence'])
    assert extract_requirements('Python','Java Intern')['job_category']=='Internship'
    assert extract_requirements('Python','Python Engineer')['job_category']=='Unknown'
    assert extract_requirements(full(),snippet=True)['status']=='PARTIAL'


def test_manual_behavior_unchanged():
    j=job(source='manual')
    assert eligibility(student(),j)['status']=='ELIGIBLE'
    assert skill_gap(student(),j)['skill_match_percentage']==100


def test_api_counts_nullable_profile_migration_and_persistence(client):
    from app.database import SessionLocal,initialize_database
    from app.models import Job
    prefix='/api/v1'
    before=client.get(prefix+'/analytics/dashboard').json()
    with SessionLocal() as db:
        row=Job(company_id=1,title='Unknown external',source='adzuna',source_reference='in:intelligence-test',source_url='https://www.adzuna.in/land/ad/test',description='Original unchanged')
        db.add(row);db.commit();jid=row.id
        backfill(db);backfill(db)
        assert row.description=='Original unchanged'
        assert row.external_metadata['original_description']==row.description
    initialize_database();initialize_database()
    s=client.get(prefix+'/students/1').json()
    assert s['professional_experience_years'] is None
    assert client.patch(prefix+'/students/1',json={'professional_experience_years':0}).json()['professional_experience_years']==0
    assert client.patch(prefix+'/students/1',json={'professional_experience_years':None}).json()['professional_experience_years'] is None
    assert client.patch(prefix+'/students/1',json={'professional_experience_years':-1}).status_code==422
    after=client.get(prefix+'/analytics/dashboard').json()
    assert after['eligible_matches']==before['eligible_matches']
    assert after['unverified_matches']==before['unverified_matches']+after['total_students']
    assert sum(after[k] for k in ['eligible_matches','unverified_matches','not_eligible_matches'])==after['total_students']*after['available_opportunities']
    assert client.post(prefix+'/applications',json={'student_id':1,'job_id':jid}).status_code==409
    assert client.get(prefix+'/matching/fit?student_id=1&job_id=1').json()['overall_fit_score']==90.6

def test_conservative_edge_cases():
    from app.services.requirement_extractor import degrees
    assert degrees('You must be motivated; contact me')==[]
    assert degrees('Bachelor of Technology')==['B.Tech/B.E.']
    a=extract_requirements('Requirements:\nPython\nSQL\nPreferred skills:\nDocker')
    assert a['required_skills']==['Python','SQL'] and a['preferred_skills']==['Docker']
    a=extract_requirements('Minimum 2 years experience; Maximum 5 years experience')
    assert (a['minimum_experience'],a['maximum_experience'])==(2,5)
    assert extract_requirements('Batch 2025-2027')['graduation_years']==[2025,2026,2027]
    for text in [full()+' Security clearance required.',full('3 or 5 years experience required'),full()+' Graduation after 2026 required.',full()+' Quantum studies branch required.']:
        assert eligibility(student(),job(text))['status']=='UNVERIFIED'
    assert eligibility(student(degree='MCA'),job('Python required. 0 years experience required. B.Tech degree not required.'))['status']=='UNVERIFIED'


def test_supported_search_controls(client,monkeypatch):
    from app.services import adzuna_service as service
    service._cache.clear()
    monkeypatch.setenv('ADZUNA_APP_ID','test-search-id')
    monkeypatch.setenv('ADZUNA_APP_KEY','test-search-key')
    monkeypatch.setattr(service,'_next_request',0)
    calls=[]
    def fetch(params):
        calls.append(params)
        return {'results':[],'count':0}
    monkeypatch.setattr(service,'_fetch',fetch)
    result=client.get('/api/v1/opportunities/external/adzuna?query=python&focus=fresher&sort_by=relevance&location=Pune')
    assert result.status_code==200
    assert calls[0]['what_or']=='fresher graduate entry-level'
    assert calls[0]['sort_by']=='relevance' and calls[0]['where']=='Pune'
    assert not any('experience' in key for key in calls[0])
    assert client.get('/api/v1/opportunities/external/adzuna?focus=invented').status_code==422
    service._cache.clear()
