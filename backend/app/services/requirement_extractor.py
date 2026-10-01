"""Conservative deterministic extraction. Unknown is distinct from no restriction."""
import html
import re
from .skill_extractor import extract_skills, normalize_skills

VERSION = 3
EXTERNAL_NOTICE = ("Extracted requirements are automated interpretations of a provider snippet. "
                   "Please review the original listing before making an application decision.")
DEGREES = {
    'B.Tech/B.E.': r'\bb\.?\s*tech\b|\bb\.\s*e\.?|(?-i:\bBE\b)|bachelor(?:s|\x27s)? of (?:technology|engineering)',
    'M.Tech/M.E.': r'\bm\.?\s*tech\b|\bm\.\s*e\.?|(?-i:\bME\b)|master(?:s|\x27s)? of (?:technology|engineering)',
    'MCA': r'\bmca\b|master(?:s|\x27s)? of computer applications',
    'Bachelor': r'\bbachelor(?:s|\x27s|\u2019s)?\b|\bb\.?\s*(?:sc|ca|com|a)\b',
    'Doctorate': r'\bph\.?d\.?|\bdoctorate\b',
    'Master': r'\bmaster(?:s|\x27s|\u2019s)?\b|\bm\.?\s*(?:sc|ba|com|a)\b',
}
BRANCHES = {'Computer Science': r'\bcomputer science\b|\bcse\b|\bcs(?:\b|\()',
            'Information Technology': r'\binformation technology\b',
            'Electronics': r'\belectronics(?: and communication)?\b|\bece\b',
            'Mechanical': r'\bmechanical(?: engineering)?\b',
            'Civil': r'\bcivil engineering\b', 'Electrical': r'\belectrical engineering\b'}
OPTIONAL = r'\b(preferred|desirable|nice.to.have|optional|advantage|bonus|plus|useful)\b'
MANDATORY = r'\b(must|required|requirements|essential|mandatory|minimum|proficiency|proficient|need|requires)\b'


def degrees(text):
    found = [name for name, pattern in DEGREES.items() if re.search(pattern, text or '', re.I)]
    if 'B.Tech/B.E.' in found and 'Bachelor' in found:
        found.remove('Bachelor')
    if set(found) & {'M.Tech/M.E.', 'MCA'} and 'Master' in found:
        found.remove('Master')
    return found


def branches(text):
    return [name for name, pattern in BRANCHES.items() if re.search(pattern, text or '', re.I)]


def extract_requirements(description, title='', job_type='unknown', snippet=False):
    text = html.unescape(re.sub(r'<[^>]*>', '\n', description or ''))
    # Preserve degree abbreviations and decimal numbers when splitting sentences.
    clauses = [x.strip() for x in re.split(r'[;\n]|(?<=[a-z0-9])\.(?=\s+[A-Z])', text) if x.strip()]
    required, preferred, evidence, warnings = set(), set(), [], []
    exp_bounds, education, branch, years = [], set(), set(), set()
    ambiguous = False
    field_evidence = {k: [] for k in ('experience', 'education', 'branch', 'graduation_years')}
    section = None
    for clause in clauses:
        if re.fullmatch(r'(?:required skills|requirements|essential skills|minimum qualifications)\s*:', clause, re.I):
            section = 'required'
            continue
        if re.fullmatch(r'(?:preferred skills|nice.to.have|desirable)\s*:', clause, re.I):
            section = 'optional'
            continue
        if re.fullmatch(r'(?:responsibilities|benefits|about us)\s*:', clause, re.I):
            section = None
            continue
        optional = section == 'optional' or bool(re.search(OPTIONAL, clause, re.I))
        mandatory = (section == 'required' or bool(re.search(MANDATORY, clause, re.I))) and not optional
        found = extract_skills(clause)
        uncertain = bool(re.search(r'\bor\b|\bnot required\b|\bnot mandatory\b', clause, re.I))
        if mandatory and found and not uncertain:
            required.update(found)
        else:
            preferred.update(found)
        if mandatory and uncertain:
            ambiguous = True
            warnings.append('Alternative or negated requirements need review: ' + clause)
        evidence.append({'text': clause, 'skills': found, 'method': 'explicit' if mandatory and not uncertain else 'keyword', 'mandatory': mandatory and not uncertain})
        if optional:
            continue
        if re.search(r'\bexperience\b|\bfresher', clause, re.I):
            field_evidence['experience'].append({'text': clause, 'method': 'explicit'})
            if re.search(r'\bor\b|depending on|negotiable', clause, re.I):
                ambiguous = True
                warnings.append('Alternative experience requirements need review: ' + clause)
                continue
            ranges = re.findall(r'(\d+(?:\.\d+)?)\s*(?:-|\u2013|\u2014|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)', clause, re.I)
            if ranges:
                exp_bounds.extend((float(lo), float(hi)) for lo, hi in ranges)
            elif re.search(r'no (?:prior |professional |work )?experience (?:is )?required|\bfreshers?\b', clause, re.I):
                exp_bounds.append((0.0, None))
                for n in re.findall(r'(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)', clause, re.I):
                    if float(n) > 0:
                        exp_bounds.append((float(n), None))
            else:
                nums = re.findall(r'(\d+(?:\.\d+)?)\s*(\+)?\s*(?:years?|yrs?)', clause, re.I)
                for number, plus in nums:
                    n = float(number)
                    exp_bounds.append((None, n) if re.search(r'\b(maximum|up to|at most)\b', clause, re.I) else (n, None))
                if not nums:
                    warnings.append('Experience requirement is ambiguous: ' + clause)
                    ambiguous = True
        detected_degrees = degrees(clause)
        if detected_degrees and not uncertain and (mandatory or re.search(r'\bdegree\b|\bgraduates?\b|\bqualification', clause, re.I)):
            field_evidence['education'].append({'text': clause, 'method': 'explicit'})
            education.update(detected_degrees)
            branch.update(branches(clause))
            if branches(clause):
                field_evidence['branch'].append({'text': clause, 'method': 'explicit'})
        if re.search(r'\bbranch(?:es)?\b', clause, re.I) and mandatory and not uncertain:
            branch.update(branches(clause))
            if branches(clause):
                field_evidence['branch'].append({'text': clause, 'method': 'explicit'})
        if re.search(r'\b(batch|graduat(?:ion|ing|es|e)|pass(?:ing|out))\b', clause, re.I):
            if re.search(r'\b(before|after|later|earlier|since|prior)\b', clause, re.I):
                ambiguous = True
                warnings.append('Graduation year comparison requires review: ' + clause)
                continue
            field_evidence['graduation_years'].append({'text': clause, 'method': 'explicit'})
            for start, end in re.findall(r'\b(20\d{2})\s*(?:-|\u2013|to)\s*(20\d{2})\b', clause):
                if int(start) <= int(end):
                    years.update(range(int(start), int(end)+1))
                else:
                    ambiguous = True
            years.update(int(x) for x in re.findall(r'\b20\d{2}\b', clause))
        if mandatory and (re.search(r'\b(clearance|citizenship|licen[sc]e|authorization|certification|cgpa|gpa|diploma)\b', clause, re.I) or not (found or detected_degrees or branches(clause) or re.search(r'\b(experience|fresher|batch|graduation)\b', clause, re.I))):
            ambiguous = True
            warnings.append('Mandatory clause includes requirements needing manual review: ' + clause)
        if re.search(r'\b(?:relevant|related) (?:field|discipline)\b|\bor equivalent\b', clause, re.I):
            ambiguous = True
            warnings.append('Equivalent or relevant disciplines require manual review.')
    bounds = list(dict.fromkeys(exp_bounds))
    if len(bounds) == 2 and sum(lo is not None for lo, hi in bounds) == 1 and sum(hi is not None for lo, hi in bounds) == 1:
        bounds = [(next(lo for lo, hi in bounds if lo is not None), next(hi for lo, hi in bounds if hi is not None))]
    if len(bounds) > 1 or any(lo is not None and hi is not None and lo > hi for lo, hi in bounds):
        warnings.append('Multiple or conflicting experience requirements need review.')
        ambiguous = True
        bounds = []
    low, high = bounds[0] if bounds else (None, None)
    if not required:
        warnings.append('No required skills extracted; mandatory skill coverage is unavailable.')
    if not bounds:
        warnings.append('Experience requirement: Not verified')
    if not education:
        warnings.append('Education requirement: Not verified')
    if snippet:
        warnings.append('The provider supplies a description snippet; omitted requirements cannot be verified.')
    if not text.strip():
        warnings.append('Job description is missing.')
    kind = 'Unknown'
    combined = title + ' ' + text
    if re.search(r'\bintern(?:ship)?\b', combined, re.I) or job_type == 'internship':
        kind = 'Internship'
    elif re.search(r'\b(fresher|graduate|entry.level|junior)\b', combined, re.I):
        kind = 'Graduate / Entry-level'
    elif low is not None and low > 0:
        kind = 'Experienced professional'
    elif re.search(r'\bfull.time\b', combined, re.I):
        kind = 'Full-time'
    elif re.search(r'\bpart.time\b', combined, re.I):
        kind = 'Part-time'
    elif re.search(r'\bcontract(?:ual)?\b', combined, re.I):
        kind = 'Contract'
    elif job_type in ('full-time', 'part-time', 'contract'):
        kind = {'full-time':'Full-time','part-time':'Part-time','contract':'Contract'}[job_type]
    complete = bool(required and bounds and education and not ambiguous and not snippet)
    usable = bool(required or bounds or education or branch or years)
    return {'version': VERSION, 'status': 'COMPLETE' if complete else 'PARTIAL' if usable else 'INSUFFICIENT_DATA',
            'technical_skills': extract_skills(text), 'required_skills': sorted(required) or None,
            'preferred_skills': sorted(preferred - required), 'minimum_experience': low, 'maximum_experience': high,
            'experience_detected': bool(bounds), 'education_requirements': sorted(education) or None,
            'branch_restrictions': sorted(branch) or None, 'graduation_years': sorted(years) or None,
            'job_category': kind, 'category_method': 'keyword/source', 'warnings': list(dict.fromkeys(warnings)),
            'field_evidence': field_evidence, 'evidence': evidence, 'ambiguous': ambiguous, 'description_is_snippet': snippet}


def external_analysis(job):
    if job.source != 'adzuna':
        return None
    meta = job.external_metadata or {}
    analysis = meta.get('requirement_analysis')
    return analysis if analysis and analysis.get('version') == VERSION else extract_requirements(meta.get('original_description', job.description), job.title, job.job_type, meta.get('description_is_snippet', True))


def required_skills(job):
    analysis = external_analysis(job)
    return normalize_skills((job.required_skills or []) + ((analysis['required_skills'] or []) if analysis else []))


def backfill(db):
    from sqlalchemy import select
    from ..models import Job
    for job in db.scalars(select(Job).where(Job.source == 'adzuna')):
        meta = dict(job.external_metadata or {})
        if (meta.get('requirement_analysis') or {}).get('version') == VERSION:
            continue
        meta.setdefault('original_description', job.description)
        meta['notice'] = EXTERNAL_NOTICE
        meta['requirement_analysis'] = extract_requirements(meta['original_description'], job.title, job.job_type, meta.get('description_is_snippet', True))
        job.external_metadata = meta
    db.commit()
