# CAMPUSLINK Frontend API Guide

Inspected from current app/main.py, app/routes/, app/schemas.py and the matching, analytics and resume services. Successful examples below were captured by calling the actual app with an isolated seeded temporary database. JSON responses are complete, not pseudocode. Existing job examples include the additive metadata with null dates/counts representing migrated records; new-operation examples were captured after the opportunity update. IDs and values in your database may differ. List examples use limit=1 for brevity.

## FRONTEND BASE URL

http://127.0.0.1:8000/api/v1

```javascript
const API = 'http://127.0.0.1:8000/api/v1';
const SERVER = 'http://127.0.0.1:8000';
async function readJSON(response) {
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string'
      ? data.detail : JSON.stringify(data.detail ?? data));
  }
  return data;
}
```

## CORS

Default explicit frontend origins, exactly as implemented:

- `http://localhost:3000`
- `http://localhost:5173`
- `http://localhost:5500`
- `http://127.0.0.1:5500`

If set, the server environment variable CORS_ORIGINS replaces this explicit list using comma splitting. In addition, HTTP loopback development origins are accepted by `allow_origin_regex=r"http://(?:localhost|127\.0\.0\.1):[0-9]{1,5}"` (a full-origin match), allowing Live Server to use port 5501 or another local port. No wildcard origin, null origin, LAN address, HTTPS origin or unrelated domain is automatically allowed. Paths such as /CampusLink_v2/ are not part of an origin. Allowed methods: GET, POST, PATCH, DELETE, OPTIONS. Allowed headers: Content-Type, Authorization. allow_credentials=False. Allowing the Authorization header does not implement authentication. Serve the frontend from an allowed HTTP origin; file:// is not supported.

## Shared contract

- **Authentication: none on every documented endpoint.** No token, login or cookie required.
- JSON writes use Content-Type: application/json. Uploads use multipart form data.
- Lists are plain arrays (opportunities/applications descending by ID; other resources ascending), without a total-count envelope. Optional pagination: integer skip=0 (>=0), limit=100 (1-500).
- Updates use PATCH. Omitted fields stay unchanged; supplied arrays replace the existing array. Empty arrays clear fields.
- Unknown JSON fields are rejected. Strings are trimmed. Project/certification arrays remove blank strings and exact duplicates. Skill arrays normalize known aliases and whitespace, deduplicate case-insensitively, and allow arbitrary custom strings. Emails are lowercased.
- Resource creation returns 201; upload returns 200. GET/PATCH return 200. DELETE returns 204 with no body; do not parse JSON for 204.
- Invalid integer path/query values return 422. Lookup of a nonexistent record returns 404. Unknown list-filter IDs return empty arrays.
- Expected application errors have detail. Unexpected server failures are not guaranteed to be JSON; provide a generic network/server error state.
- Matching accepts stored student_id and job_id query parameters, not nested profile JSON.

### Error formats

404 example (model name and ID vary):

```json
{
  "detail": "Student 99999 not found"
}
```

409 shared database-conflict message:

```json
{
  "detail": "Conflicting record: duplicate unique value or referenced record cannot be deleted."
}
```

422 validation errors normally have a detail array containing type, loc, msg, input and sometimes ctx. loc identifies body, path or query and the field. Business-rule 422 errors may instead have a string detail. Handle both.

## Writable field reference

Each operation includes an exact valid request example; optional fields may be omitted.

### Student

Required on create: name, email, department, graduation_year, cgpa.
Optional professional_experience_years is a finite number from 0 to 80 or null (default null). Zero explicitly means no professional experience; null means unknown. POST and PATCH accept it. Projects, certifications and semesters never supply this value.

Optional degree and preferred_role are free-text strings, default empty, max 150 characters; PATCH supports both. department stores branch. Career preference is informational.
Optional: phone (default empty string, max 25 characters); skills, certifications, projects (default empty string arrays, max 100 entries each); coding_score, aptitude_score, communication_score (default 0).
Name/department: 1-150 characters after trimming. Email must be valid. Graduation year: 2000-2100. CGPA: finite 0-10. Scores: finite 0-100.
PATCH accepts any subset; explicit null is rejected. id and resume_filename are response-only. Student PATCH also accepts extracted_skills (max 100 strings) for reviewing/correcting extraction; a later resume upload replaces that list.

### Company

Required on create: name (1-150 characters). Optional industry, location, website, description default to empty strings. website is plain text, not a validated URL. PATCH accepts any subset; null is rejected.
Company name is unique; student email is unique.

### Job

Required on create: positive integer company_id and title (1-150 characters).
Optional description, location, salary_stipend default to empty strings; required_skills/preferred_skills default to empty string arrays (max 100 entries); minimum_cgpa is finite 0-10 (default 0); graduation_year is 2000-2100 or null (default null); job_type defaults to full-time.
Allowed job_type: full-time, internship, part-time, contract, unknown. Unknown is used when an external listing does not specify working time/type.
PATCH accepts any subset. graduation_year accepts null, meaning any year; vacancy_count, source_reference and source_url also accept null. salary_stipend is display text, not a numeric salary. Responses include a nested company; requests use company_id.

Additional Job / Opportunity fields: vacancy_count is an integer >=1 or null (unknown); source_reference is a string up to 500 characters or null; source_url is an HTTP(S) string up to 2000 characters or null; status is open (default) or closed. All are writable on create/PATCH. source and created_at are response-only. source is demo, manual, json_import, legacy or adzuna. Timestamps are UTC ISO 8601, or null for unknown old creation dates. Jobs created through the original jobs API have source manual. IDs are shared between jobs and opportunities.

### Placement: supported operations and fields

Required on create: positive integer student_id, company_id, job_id.
Optional status defaults to offered; offer_date/joining_date are YYYY-MM-DD or null (default null); package is a finite nonnegative number (default 0), measured in annual INR lakhs/LPA.
Statuses: offered, accepted, joined, rejected, withdrawn. Joining date cannot precede offer date when both exist. Company must match the job. A student/job pair can have only one record.
**Only create, list and status update exist. Placement get-by-ID, delete and general field updates are not implemented.** Do not display those actions.
Status PATCH requires status only; dates/package are not accepted and status transitions are not restricted.

## API operations

Actual 422 example (missing required job_id query parameter):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": [
        "query",
        "job_id"
      ],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

### List students

**GET `/api/v1/students`**

Purpose: Populate the students list.

Path parameters: None.

Query parameters: Optional skip: integer >=0, default 0; limit: integer 1-500, default 100. Example uses limit=1.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
[
  {
    "name": "Ananya Mishra",
    "email": "student1@example.com",
    "phone": "9000000001",
    "department": "CSE",
    "graduation_year": 2026,
    "cgpa": 8.7,
    "skills": [
      "Python",
      "SQL",
      "FastAPI",
      "Git"
    ],
    "certifications": [
      "Programming fundamentals"
    ],
    "projects": [
      "Campus event portal",
      "Placement tracker"
    ],
    "coding_score": 85.0,
    "aptitude_score": 80.0,
    "communication_score": 78.0,
    "id": 1,
    "resume_filename": null,
    "extracted_skills": [],
    "degree": "",
    "preferred_role": "",
    "professional_experience_years": null
  }
]
```

Important errors: 422 invalid pagination or integer filters.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students?skip=0&limit=1'));
```

### Create student

**POST `/api/v1/students`**

Purpose: Create a student record.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "name": "Demo Student",
  "email": "frontend.demo@example.com",
  "phone": "9000000011",
  "department": "CSE",
  "graduation_year": 2026,
  "cgpa": 8.2,
  "skills": [
    "Python",
    "SQL"
  ],
  "certifications": [
    "Python fundamentals"
  ],
  "projects": [
    "Campus portal"
  ],
  "coding_score": 80,
  "aptitude_score": 75,
  "communication_score": 85,
  "degree": "",
  "preferred_role": ""
}
```
Example successful response (**201**):

```json
{
  "name": "Demo Student",
  "email": "frontend.demo@example.com",
  "phone": "9000000011",
  "department": "CSE",
  "graduation_year": 2026,
  "cgpa": 8.2,
  "skills": [
    "Python",
    "SQL"
  ],
  "certifications": [
    "Python fundamentals"
  ],
  "projects": [
    "Campus portal"
  ],
  "coding_score": 80.0,
  "aptitude_score": 75.0,
  "communication_score": 85.0,
  "id": 11,
  "resume_filename": null,
  "extracted_skills": [],
  "degree": "",
  "preferred_role": "",
  "professional_experience_years": null
}
```

Important errors: 422 invalid/missing fields; 409 unique/reference conflict.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"name": "Demo Student", "email": "frontend.demo@example.com", "phone": "9000000011", "department": "CSE", "graduation_year": 2026, "cgpa": 8.2, "skills": ["Python", "SQL"], "certifications": ["Python fundamentals"], "projects": ["Campus portal"], "coding_score": 80, "aptitude_score": 75, "communication_score": 85})
}));
```

### Get student

**GET `/api/v1/students/{student_id}`**

Purpose: Load one student record.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "name": "Ananya Mishra",
  "email": "student1@example.com",
  "phone": "9000000001",
  "department": "CSE",
  "graduation_year": 2026,
  "cgpa": 8.7,
  "skills": [
    "Python",
    "SQL",
    "FastAPI",
    "Git"
  ],
  "certifications": [
    "Programming fundamentals"
  ],
  "projects": [
    "Campus event portal",
    "Placement tracker"
  ],
  "coding_score": 85.0,
  "aptitude_score": 80.0,
  "communication_score": 78.0,
  "id": 1,
  "resume_filename": null,
  "extracted_skills": [],
  "degree": "",
  "preferred_role": "",
  "professional_experience_years": null
}
```

Important errors: 404 record not found; 422 invalid path integer.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students/1'));
```

### Update student

**PATCH `/api/v1/students/{student_id}`**

Purpose: Update supplied student fields.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "communication_score": 90,
  "skills": [
    "Python",
    "SQL",
    "Git"
  ]
}
```
Example successful response (**200**):

```json
{
  "name": "Demo Student",
  "email": "frontend.demo@example.com",
  "phone": "9000000011",
  "department": "CSE",
  "graduation_year": 2026,
  "cgpa": 8.2,
  "skills": [
    "Python",
    "SQL",
    "Git"
  ],
  "certifications": [
    "Python fundamentals"
  ],
  "projects": [
    "Campus portal"
  ],
  "coding_score": 80.0,
  "aptitude_score": 75.0,
  "communication_score": 90.0,
  "id": 11,
  "resume_filename": null,
  "extracted_skills": [],
  "degree": "",
  "preferred_role": "",
  "professional_experience_years": null
}
```

Important errors: 404 record not found; 422 invalid fields/path; 409 unique/reference conflict.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students/11', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"communication_score": 90, "skills": ["Python", "SQL", "Git"]})
}));
```

### Delete student

**DELETE `/api/v1/students/{student_id}`**

Purpose: Delete a student record.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Successful response: **204 No Content**, empty body. No successful JSON response.

Important errors: 404 record not found; 422 invalid path; 409 when referenced by existing records.

Placement records prevent deletion. Successful deletion also attempts to remove the stored resume.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students/11', {method: 'DELETE'}));
```

### List companies

**GET `/api/v1/companies`**

Purpose: Populate the companies list.

Path parameters: None.

Query parameters: Optional skip: integer >=0, default 0; limit: integer 1-500, default 100. Example uses limit=1.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
[
  {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  }
]
```

Important errors: 422 invalid pagination or integer filters.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/companies?skip=0&limit=1'));
```

### Create company

**POST `/api/v1/companies`**

Purpose: Create a company record.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "name": "Frontend Demo Company",
  "industry": "Software",
  "location": "Bhubaneswar",
  "website": "https://example.com",
  "description": "Demo employer"
}
```
Example successful response (**201**):

```json
{
  "name": "Frontend Demo Company",
  "industry": "Software",
  "location": "Bhubaneswar",
  "website": "https://example.com",
  "description": "Demo employer",
  "id": 5
}
```

Important errors: 422 invalid/missing fields; 409 unique/reference conflict.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/companies', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"name": "Frontend Demo Company", "industry": "Software", "location": "Bhubaneswar", "website": "https://example.com", "description": "Demo employer"})
}));
```

### Get company

**GET `/api/v1/companies/{company_id}`**

Purpose: Load one company record.

Path parameters: company_id: required integer company ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "name": "Odisha Techworks",
  "industry": "Software services",
  "location": "Bhubaneswar",
  "website": "",
  "description": "Fictional company for the CAMPUSLINK demo.",
  "id": 1
}
```

Important errors: 404 record not found; 422 invalid path integer.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/companies/1'));
```

### Update company

**PATCH `/api/v1/companies/{company_id}`**

Purpose: Update supplied company fields.

Path parameters: company_id: required integer company ID.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "location": "Pune"
}
```
Example successful response (**200**):

```json
{
  "name": "Frontend Demo Company",
  "industry": "Software",
  "location": "Pune",
  "website": "https://example.com",
  "description": "Demo employer",
  "id": 5
}
```

Important errors: 404 record not found; 422 invalid fields/path; 409 unique/reference conflict.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/companies/5', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"location": "Pune"})
}));
```

### Delete company

**DELETE `/api/v1/companies/{company_id}`**

Purpose: Delete a company record.

Path parameters: company_id: required integer company ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Successful response: **204 No Content**, empty body. No successful JSON response.

Important errors: 404 record not found; 422 invalid path; 409 when referenced by existing records.

Existing jobs or placement records prevent deletion.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/companies/5', {method: 'DELETE'}));
```

### List jobs

**GET `/api/v1/jobs`**

Purpose: Populate the jobs list.

Path parameters: None.

Query parameters: Optional skip: integer >=0, default 0; limit: integer 1-500, default 100. Example uses limit=1. Optional company_id: integer company filter.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
[
  {
    "company_id": 1,
    "title": "Python Backend Developer",
    "description": "Build practical products as a python backend developer.",
    "required_skills": [
      "Python",
      "SQL"
    ],
    "preferred_skills": [
      "FastAPI",
      "Git"
    ],
    "minimum_cgpa": 7.0,
    "graduation_year": 2026,
    "location": "Bhubaneswar",
    "salary_stipend": "6 LPA",
    "job_type": "full-time",
    "id": 1,
    "company": {
      "name": "Odisha Techworks",
      "industry": "Software services",
      "location": "Bhubaneswar",
      "website": "",
      "description": "Fictional company for the CAMPUSLINK demo.",
      "id": 1
    },
    "vacancy_count": null,
    "source_reference": null,
    "source_url": null,
    "status": "open",
    "source": "demo",
    "created_at": null,
    "external_metadata": null
  }
]
```

Important errors: 422 invalid pagination or integer filters.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/jobs?skip=0&limit=1'));
```

### Create job

**POST `/api/v1/jobs`**

Purpose: Create a job record.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "company_id": 1,
  "title": "Frontend Demo Role",
  "description": "Build APIs",
  "required_skills": [
    "Python",
    "SQL"
  ],
  "preferred_skills": [
    "Git"
  ],
  "minimum_cgpa": 7,
  "graduation_year": 2026,
  "location": "Bhubaneswar",
  "salary_stipend": "6 LPA",
  "job_type": "full-time"
}
```
Example successful response (**201**):

```json
{
  "company_id": 1,
  "title": "Frontend Demo Role",
  "description": "Build APIs",
  "required_skills": [
    "Python",
    "SQL"
  ],
  "preferred_skills": [
    "Git"
  ],
  "minimum_cgpa": 7.0,
  "graduation_year": 2026,
  "location": "Bhubaneswar",
  "salary_stipend": "6 LPA",
  "job_type": "full-time",
  "id": 7,
  "company": {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  },
  "vacancy_count": null,
  "source_reference": null,
  "source_url": null,
  "status": "open",
  "source": "demo",
  "created_at": null,
  "external_metadata": null
}
```

Important errors: 422 invalid/missing fields; 409 unique/reference conflict. 404 company_id not found.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/jobs', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"company_id": 1, "title": "Frontend Demo Role", "description": "Build APIs", "required_skills": ["Python", "SQL"], "preferred_skills": ["Git"], "minimum_cgpa": 7, "graduation_year": 2026, "location": "Bhubaneswar", "salary_stipend": "6 LPA", "job_type": "full-time"})
}));
```

### Get job

**GET `/api/v1/jobs/{job_id}`**

Purpose: Load one job record.

Path parameters: job_id: required integer job ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "company_id": 1,
  "title": "Python Backend Developer",
  "description": "Build practical products as a python backend developer.",
  "required_skills": [
    "Python",
    "SQL"
  ],
  "preferred_skills": [
    "FastAPI",
    "Git"
  ],
  "minimum_cgpa": 7.0,
  "graduation_year": 2026,
  "location": "Bhubaneswar",
  "salary_stipend": "6 LPA",
  "job_type": "full-time",
  "id": 1,
  "company": {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  },
  "vacancy_count": null,
  "source_reference": null,
  "source_url": null,
  "status": "open",
  "source": "demo",
  "created_at": null,
  "external_metadata": null
}
```

Important errors: 404 record not found; 422 invalid path integer.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/jobs/1'));
```

### Update job

**PATCH `/api/v1/jobs/{job_id}`**

Purpose: Update supplied job fields.

Path parameters: job_id: required integer job ID.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "minimum_cgpa": 7.5,
  "graduation_year": null
}
```
Example successful response (**200**):

```json
{
  "company_id": 1,
  "title": "Frontend Demo Role",
  "description": "Build APIs",
  "required_skills": [
    "Python",
    "SQL"
  ],
  "preferred_skills": [
    "Git"
  ],
  "minimum_cgpa": 7.5,
  "graduation_year": null,
  "location": "Bhubaneswar",
  "salary_stipend": "6 LPA",
  "job_type": "full-time",
  "id": 7,
  "company": {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  },
  "vacancy_count": null,
  "source_reference": null,
  "source_url": null,
  "status": "open",
  "source": "demo",
  "created_at": null,
  "external_metadata": null
}
```

Important errors: 404 record not found; 422 invalid fields/path; 409 unique/reference conflict. 404 new company not found; 409 detail: "Cannot change the company of a job with placement records" when moving a job with offers.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/jobs/7', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"minimum_cgpa": 7.5, "graduation_year": null})
}));
```

### Delete job

**DELETE `/api/v1/jobs/{job_id}`**

Purpose: Delete a job record.

Path parameters: job_id: required integer job ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Successful response: **204 No Content**, empty body. No successful JSON response.

Important errors: 404 record not found; 422 invalid path; 409 when referenced by existing records.

Existing placement records prevent deletion.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/jobs/7', {method: 'DELETE'}));
```

### Student-job eligibility

**GET `/api/v1/matching/eligibility`**

Purpose: Check CGPA, graduation year and all required skills.

Path parameters: None.

Query parameters: Required student_id: integer; required job_id: integer. Both must identify existing records.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "student_id": 10,
  "job_id": 1,
  "eligible": false,
  "status": "NOT_ELIGIBLE",
  "reasons": [
    "cgpa: expected 7.0; actual 6.9.",
    "graduation_year: expected 2026; actual 2027.",
    "Missing required skills: Python, SQL"
  ],
  "missing_requirements": [
    {
      "requirement": "cgpa",
      "expected": 7.0,
      "actual": 6.9,
      "status": "NOT_ELIGIBLE"
    },
    {
      "requirement": "graduation_year",
      "expected": 2026,
      "actual": 2027,
      "status": "NOT_ELIGIBLE"
    },
    {
      "requirement": "required_skills",
      "missing": [
        "Python",
        "SQL"
      ]
    }
  ],
  "unknown_requirements": [],
  "checks": [
    {
      "requirement": "cgpa",
      "expected": 7.0,
      "actual": 6.9,
      "status": "NOT_ELIGIBLE"
    },
    {
      "requirement": "graduation_year",
      "expected": 2026,
      "actual": 2027,
      "status": "NOT_ELIGIBLE"
    },
    {
      "requirement": "required_skills",
      "expected": [
        "Python",
        "SQL"
      ],
      "actual": [
        "C",
        "Communication",
        "Excel"
      ],
      "status": "NOT_ELIGIBLE"
    }
  ],
  "requirement_analysis": null
}
```

Important errors: 404 student/job not found; 422 missing query parameters or invalid integers. An ineligible student still produces 200, not an HTTP error.

This example intentionally returns eligible: false. Passing responses have eligible: true, missing_requirements: [], and reasons: ["All basic eligibility requirements are satisfied."]. Null job graduation year allows any year. Preferred skills do not determine eligibility.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/matching/eligibility?student_id=10&job_id=1'));
```

### Candidate-job fit score

**GET `/api/v1/matching/fit`**

Purpose: Show 0-100 explainable fit and independent eligibility.

Path parameters: None.

Query parameters: Required student_id: integer; required job_id: integer. Both must identify existing records.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "student_id": 1,
  "job_id": 1,
  "matched_skills": [
    "Python",
    "SQL"
  ],
  "missing_skills": [],
  "skill_match_percentage": 100.0,
  "matched_preferred_skills": [
    "FastAPI",
    "Git"
  ],
  "missing_preferred_skills": [],
  "recommended_skills_to_learn": [],
  "priorities": [],
  "eligibility_status": "ELIGIBLE",
  "eligibility": {
    "student_id": 1,
    "job_id": 1,
    "eligible": true,
    "status": "ELIGIBLE",
    "reasons": [
      "All basic eligibility requirements are satisfied."
    ],
    "missing_requirements": [],
    "unknown_requirements": [],
    "checks": [
      {
        "requirement": "cgpa",
        "expected": 7.0,
        "actual": 8.7,
        "status": "ELIGIBLE"
      },
      {
        "requirement": "graduation_year",
        "expected": 2026,
        "actual": 2026,
        "status": "ELIGIBLE"
      },
      {
        "requirement": "required_skills",
        "expected": [
          "Python",
          "SQL"
        ],
        "actual": [
          "FastAPI",
          "Git",
          "Python",
          "SQL"
        ],
        "status": "ELIGIBLE"
      }
    ],
    "requirement_analysis": null
  },
  "coverage_available": true,
  "coverage_note": null,
  "overall_fit_score": 90.6,
  "provisional": false,
  "strengths": [
    "Required skills present: Python, SQL",
    "Strong self-reported coding score (85.0/100).",
    "Strong self-reported aptitude score (80.0/100).",
    "Strong self-reported communication score (78.0/100)."
  ],
  "improvement_suggestions": [],
  "explanation": {
    "components": {
      "skills": {
        "score": 100.0,
        "weight_percent": 45,
        "contribution": 45.0,
        "available": true
      },
      "cgpa": {
        "score": 87.0,
        "weight_percent": 15,
        "contribution": 13.05
      },
      "coding": {
        "score": 85.0,
        "weight_percent": 15,
        "contribution": 12.75
      },
      "aptitude": {
        "score": 80.0,
        "weight_percent": 10,
        "contribution": 8.0
      },
      "communication": {
        "score": 78.0,
        "weight_percent": 10,
        "contribution": 7.8
      },
      "portfolio": {
        "score": 80,
        "weight_percent": 5,
        "contribution": 4.0
      }
    },
    "formula": "Sum of component score * weight / 100. Skills = 80% required + 20% preferred coverage; with no preferred skills, use required coverage. Configured manual jobs with no required skills retain 100% coverage. External jobs with no required skills have unavailable coverage and zero skill contribution; weights are not redistributed. CGPA = CGPA * 10. Portfolio = min(30 * projects + 20 * certifications, 100).",
    "limitations": "Hackathon heuristic, not a validated hiring model. Scores and portfolio entries are self-reported; portfolio counts do not assess quality or relevance. Eligibility is independent of fit score. No trained ML model is used."
  }
}
```

Important errors: 404 student/job not found; 422 missing query parameters or invalid integers. An ineligible student still produces 200, not an HTTP error.

Weights: skills 45%, CGPA 15%, coding 15%, aptitude 10%, communication 10%, portfolio 5%. Skills combine 80% required and 20% preferred coverage (required coverage alone if no preferred skills). Manual/demo jobs with no configured required skills retain 100% coverage. External jobs with no extracted required skills return null coverage and zero skill contribution, without redistributing weights. CGPA is multiplied by 10. Portfolio is min(30 * projects + 20 * certifications, 100). This is a self-reported-data hackathon heuristic, not a validated hiring model. A high score does not imply eligibility.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/matching/fit?student_id=1&job_id=1'));
```

### Skill-gap analysis

**GET `/api/v1/matching/skill-gap`**

Purpose: Show matched/missing skills and learning priorities.

Path parameters: None.

Query parameters: Required student_id: integer; required job_id: integer. Both must identify existing records.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "student_id": 6,
  "job_id": 2,
  "matched_skills": [
    "JavaScript"
  ],
  "missing_skills": [
    "React"
  ],
  "skill_match_percentage": 50.0,
  "matched_preferred_skills": [
    "CSS",
    "HTML"
  ],
  "missing_preferred_skills": [],
  "recommended_skills_to_learn": [
    "React"
  ],
  "priorities": [
    {
      "skill": "React",
      "priority": "high",
      "reason": "Required by job"
    }
  ],
  "eligibility_status": "NOT_ELIGIBLE",
  "eligibility": {
    "student_id": 6,
    "job_id": 2,
    "eligible": false,
    "status": "NOT_ELIGIBLE",
    "reasons": [
      "cgpa: expected 7.0; actual 6.4.",
      "Missing required skills: React"
    ],
    "missing_requirements": [
      {
        "requirement": "cgpa",
        "expected": 7.0,
        "actual": 6.4,
        "status": "NOT_ELIGIBLE"
      },
      {
        "requirement": "required_skills",
        "missing": [
          "React"
        ]
      }
    ],
    "unknown_requirements": [],
    "checks": [
      {
        "requirement": "cgpa",
        "expected": 7.0,
        "actual": 6.4,
        "status": "NOT_ELIGIBLE"
      },
      {
        "requirement": "graduation_year",
        "expected": 2026,
        "actual": 2026,
        "status": "ELIGIBLE"
      },
      {
        "requirement": "required_skills",
        "expected": [
          "JavaScript",
          "React"
        ],
        "actual": [
          "CSS",
          "HTML",
          "JavaScript"
        ],
        "status": "NOT_ELIGIBLE"
      }
    ],
    "requirement_analysis": null
  },
  "coverage_available": true,
  "coverage_note": null
}
```

Important errors: 404 student/job not found; 422 missing query parameters or invalid integers. An ineligible student still produces 200, not an HTTP error.

matched_skills/missing_skills concern required skills. Preferred skills have separate arrays. Required gaps have high priority; preferred gaps have medium priority. All matching uses normalized aliases and the union of manual skills and extracted skills.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/matching/skill-gap?student_id=6&job_id=2'));
```

### Upload resume

**POST `/api/v1/students/{student_id}/resume`**

Purpose: Store/replace resume and extracted skills.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Request body: **multipart/form-data**, required field `file` (one file). No JSON body. Example resume.txt contains `Python and SQL`.

Example successful response (**200**):

```json
{
  "student_id": 6,
  "filename": "resume.txt",
  "extracted_skills": [
    "Python",
    "SQL"
  ],
  "text_length": 14,
  "warning": null
}
```

Important errors: 404 student not found; 413 detail: "Resume exceeds the 5 MiB limit"; 415 detail: "Supported resume formats: PDF, DOCX, TXT"; 422 missing file/invalid path, detail: "Resume is empty", or detail: "Unable to read resume. Use UTF-8 TXT, unencrypted PDF (up to 30 pages), or valid DOCX.".

PDF/DOCX/TXT extensions are case-insensitive. TXT must be UTF-8. PDFs must be unencrypted with at most 30 pages. DOCX expanded content is limited to 20 MiB. Text is capped at 200,000 characters. An image-only PDF can upload with warning: "No text extracted. Scanned documents require OCR, which is not supported." Manual skills stay unchanged; extracted_skills replace the old extracted list. Refresh matching after upload.

JavaScript fetch example (uses shared constants/helper):

```javascript
const studentId = 6;
const form = new FormData();
form.append('file', fileInput.files[0]); // fileInput is your file input element.
const result = await readJSON(await fetch(API + '/students/' + studentId + '/resume', {
  method: 'POST', body: form
}));
// Do not set Content-Type: the browser supplies the multipart boundary.
```

### Read resume information

**GET `/api/v1/students/{student_id}/resume`**

Purpose: Read filename, extracted text and skills.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "student_id": 6,
  "filename": "resume.txt",
  "text": "Python and SQL",
  "extracted_skills": [
    "Python",
    "SQL"
  ]
}
```

Important errors: 404 student not found or detail: "Student has no uploaded resume"; 422 invalid path integer.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/students/6/resume'));
```

### Download resume

**GET `/api/v1/students/{student_id}/resume/download`**

Purpose: Download original uploaded file.

Path parameters: student_id: required integer student ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Successful response: **200**, raw file bytes; Content-Type: application/octet-stream, attachment Content-Disposition. No successful JSON response. Example file bytes contain `Python and SQL`. Use response.blob(), not response.json().

Important errors: 404 student not found or detail: "Resume file not found"; 422 invalid path integer.

CORS does not expose Content-Disposition to cross-origin JavaScript. Use filename from resume information or resume_filename from the student response.

JavaScript fetch example (uses shared constants/helper):

```javascript
const studentId = 6;
const metadata = await readJSON(await fetch(API + '/students/' + studentId + '/resume'));
const response = await fetch(API + '/students/' + studentId + '/resume/download');
if (!response.ok) {
  const error = await response.json();
  throw new Error(JSON.stringify(error.detail));
}
const objectURL = URL.createObjectURL(await response.blob());
const link = document.createElement('a');
link.href = objectURL;
link.download = metadata.filename;
document.body.appendChild(link);
link.click();
link.remove();
setTimeout(() => URL.revokeObjectURL(objectURL), 1000);
```

### List placements

**GET `/api/v1/placements`**

Purpose: Show placement/offer information.

Path parameters: None.

Query parameters: Optional skip: integer >=0, default 0; limit: integer 1-500, default 100. Example uses limit=1. Optional student_id: integer filter.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
[
  {
    "student_id": 1,
    "company_id": 1,
    "job_id": 1,
    "status": "accepted",
    "offer_date": "2026-09-15",
    "joining_date": null,
    "package": 6.0,
    "id": 1
  }
]
```

Important errors: 422 invalid pagination or student_id integer.

Responses contain foreign-key IDs, not nested names. Join to loaded student/company/job lists. No single-record read operation exists.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/placements?student_id=1&skip=0&limit=1'));
```

### Create placement

**POST `/api/v1/placements`**

Purpose: Record an offer.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "student_id": 6,
  "company_id": 4,
  "job_id": 6,
  "status": "offered",
  "offer_date": "2026-09-29",
  "joining_date": "2026-10-15",
  "package": 1.8
}
```
Example successful response (**201**):

```json
{
  "student_id": 6,
  "company_id": 4,
  "job_id": 6,
  "status": "offered",
  "offer_date": "2026-09-29",
  "joining_date": "2026-10-15",
  "package": 1.8,
  "id": 5
}
```

Important errors: 404 student/company/job not found; 409 duplicate student/job pair; 422 invalid fields/dates or detail: "company_id must match the job's company".

The backend does not automatically check eligibility when recording offers. package is annual INR lakhs, not a monthly stipend.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/placements', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"student_id": 6, "company_id": 4, "job_id": 6, "status": "offered", "offer_date": "2026-09-29", "joining_date": "2026-10-15", "package": 1.8})
}));
```

### Update placement status

**PATCH `/api/v1/placements/{placement_id}/status`**

Purpose: Change offer status.

Path parameters: placement_id: required integer record ID.

Query parameters: None.

Authentication: **not required**.

Exact example JSON request body:

```json
{
  "status": "accepted"
}
```
Example successful response (**200**):

```json
{
  "student_id": 6,
  "company_id": 4,
  "job_id": 6,
  "status": "accepted",
  "offer_date": "2026-09-29",
  "joining_date": "2026-10-15",
  "package": 1.8,
  "id": 5
}
```

Important errors: 404 placement not found; 422 missing/invalid status, extra fields or invalid path integer.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/placements/5/status', {
  method: 'PATCH',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({"status": "accepted"})
}));
```

### Dashboard analytics

**GET `/api/v1/analytics/dashboard`**

Purpose: Populate dashboard counts, charts, recent activity and placement statistics.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "available_opportunities": 6,
  "known_vacancies": 0,
  "opportunities_without_vacancy_count": 6,
  "eligible_matches": 10,
  "unverified_matches": 0,
  "not_eligible_matches": 50,
  "opportunity_sources": {
    "demo": 6
  },
  "application_statistics": {},
  "latest_opportunities": [
    {
      "company_id": 4,
      "title": "Web Development Intern",
      "description": "Build practical products as a web development intern.",
      "required_skills": [
        "HTML",
        "CSS"
      ],
      "preferred_skills": [
        "JavaScript",
        "React"
      ],
      "minimum_cgpa": 6.0,
      "graduation_year": 2026,
      "location": "Hyderabad",
      "salary_stipend": "INR 15000/month",
      "job_type": "internship",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 6,
      "company": {
        "name": "Utkal Digital",
        "industry": "Web products",
        "location": "Hyderabad",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 4
      }
    },
    {
      "company_id": 1,
      "title": "Java Developer",
      "description": "Build practical products as a java developer.",
      "required_skills": [
        "Java",
        "SQL"
      ],
      "preferred_skills": [
        "Spring Boot",
        "Git"
      ],
      "minimum_cgpa": 7.5,
      "graduation_year": 2026,
      "location": "Bhubaneswar",
      "salary_stipend": "6.5 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 5,
      "company": {
        "name": "Odisha Techworks",
        "industry": "Software services",
        "location": "Bhubaneswar",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 1
      }
    },
    {
      "company_id": 3,
      "title": "Cloud Engineering Intern",
      "description": "Build practical products as a cloud engineering intern.",
      "required_skills": [
        "Python",
        "Linux"
      ],
      "preferred_skills": [
        "AWS",
        "Docker"
      ],
      "minimum_cgpa": 7.0,
      "graduation_year": 2026,
      "location": "Bengaluru",
      "salary_stipend": "INR 25000/month",
      "job_type": "internship",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 4,
      "company": {
        "name": "Kalinga Cloud Labs",
        "industry": "Cloud platforms",
        "location": "Bengaluru",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 3
      }
    },
    {
      "company_id": 2,
      "title": "Data Analyst",
      "description": "Build practical products as a data analyst.",
      "required_skills": [
        "Python",
        "SQL",
        "Pandas"
      ],
      "preferred_skills": [
        "Excel",
        "Power BI"
      ],
      "minimum_cgpa": 7.5,
      "graduation_year": 2026,
      "location": "Bhubaneswar",
      "salary_stipend": "7 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386841Z",
      "id": 3,
      "company": {
        "name": "Mahanadi Analytics",
        "industry": "Data analytics",
        "location": "Bhubaneswar",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 2
      }
    },
    {
      "company_id": 4,
      "title": "Frontend Developer",
      "description": "Build practical products as a frontend developer.",
      "required_skills": [
        "JavaScript",
        "React"
      ],
      "preferred_skills": [
        "HTML",
        "CSS"
      ],
      "minimum_cgpa": 7.0,
      "graduation_year": 2026,
      "location": "Hyderabad",
      "salary_stipend": "5.5 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386840Z",
      "id": 2,
      "company": {
        "name": "Utkal Digital",
        "industry": "Web products",
        "location": "Hyderabad",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 4
      }
    }
  ],
  "total_students": 10,
  "total_companies": 4,
  "total_jobs": 6,
  "placed_students": 3,
  "placement_rate": 30.0,
  "average_cgpa": 7.86,
  "top_skills": [
    {
      "skill": "Python",
      "count": 5
    },
    {
      "skill": "SQL",
      "count": 4
    },
    {
      "skill": "Git",
      "count": 3
    },
    {
      "skill": "JavaScript",
      "count": 3
    },
    {
      "skill": "CSS",
      "count": 2
    },
    {
      "skill": "HTML",
      "count": 2
    },
    {
      "skill": "React",
      "count": 2
    },
    {
      "skill": "Excel",
      "count": 2
    },
    {
      "skill": "FastAPI",
      "count": 1
    },
    {
      "skill": "Pandas",
      "count": 1
    }
  ],
  "most_demanded_skills": [
    {
      "skill": "Python",
      "count": 3
    },
    {
      "skill": "SQL",
      "count": 3
    },
    {
      "skill": "JavaScript",
      "count": 1
    },
    {
      "skill": "React",
      "count": 1
    },
    {
      "skill": "Pandas",
      "count": 1
    },
    {
      "skill": "Linux",
      "count": 1
    },
    {
      "skill": "Java",
      "count": 1
    },
    {
      "skill": "CSS",
      "count": 1
    },
    {
      "skill": "HTML",
      "count": 1
    }
  ],
  "recent_jobs": [
    {
      "company_id": 4,
      "title": "Web Development Intern",
      "description": "Build practical products as a web development intern.",
      "required_skills": [
        "HTML",
        "CSS"
      ],
      "preferred_skills": [
        "JavaScript",
        "React"
      ],
      "minimum_cgpa": 6.0,
      "graduation_year": 2026,
      "location": "Hyderabad",
      "salary_stipend": "INR 15000/month",
      "job_type": "internship",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 6,
      "company": {
        "name": "Utkal Digital",
        "industry": "Web products",
        "location": "Hyderabad",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 4
      }
    },
    {
      "company_id": 1,
      "title": "Java Developer",
      "description": "Build practical products as a java developer.",
      "required_skills": [
        "Java",
        "SQL"
      ],
      "preferred_skills": [
        "Spring Boot",
        "Git"
      ],
      "minimum_cgpa": 7.5,
      "graduation_year": 2026,
      "location": "Bhubaneswar",
      "salary_stipend": "6.5 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 5,
      "company": {
        "name": "Odisha Techworks",
        "industry": "Software services",
        "location": "Bhubaneswar",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 1
      }
    },
    {
      "company_id": 3,
      "title": "Cloud Engineering Intern",
      "description": "Build practical products as a cloud engineering intern.",
      "required_skills": [
        "Python",
        "Linux"
      ],
      "preferred_skills": [
        "AWS",
        "Docker"
      ],
      "minimum_cgpa": 7.0,
      "graduation_year": 2026,
      "location": "Bengaluru",
      "salary_stipend": "INR 25000/month",
      "job_type": "internship",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386842Z",
      "id": 4,
      "company": {
        "name": "Kalinga Cloud Labs",
        "industry": "Cloud platforms",
        "location": "Bengaluru",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 3
      }
    },
    {
      "company_id": 2,
      "title": "Data Analyst",
      "description": "Build practical products as a data analyst.",
      "required_skills": [
        "Python",
        "SQL",
        "Pandas"
      ],
      "preferred_skills": [
        "Excel",
        "Power BI"
      ],
      "minimum_cgpa": 7.5,
      "graduation_year": 2026,
      "location": "Bhubaneswar",
      "salary_stipend": "7 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386841Z",
      "id": 3,
      "company": {
        "name": "Mahanadi Analytics",
        "industry": "Data analytics",
        "location": "Bhubaneswar",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 2
      }
    },
    {
      "company_id": 4,
      "title": "Frontend Developer",
      "description": "Build practical products as a frontend developer.",
      "required_skills": [
        "JavaScript",
        "React"
      ],
      "preferred_skills": [
        "HTML",
        "CSS"
      ],
      "minimum_cgpa": 7.0,
      "graduation_year": 2026,
      "location": "Hyderabad",
      "salary_stipend": "5.5 LPA",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": null,
      "source_url": null,
      "status": "open",
      "external_metadata": null,
      "source": "demo",
      "created_at": "2026-09-30T17:04:37.386840Z",
      "id": 2,
      "company": {
        "name": "Utkal Digital",
        "industry": "Web products",
        "location": "Hyderabad",
        "website": "",
        "description": "Fictional company for the CAMPUSLINK demo.",
        "id": 4
      }
    }
  ],
  "recent_placements": [
    {
      "student_id": 9,
      "company_id": 4,
      "job_id": 2,
      "status": "accepted",
      "offer_date": "2026-09-15",
      "joining_date": null,
      "package": 5.5,
      "id": 4
    },
    {
      "student_id": 5,
      "company_id": 1,
      "job_id": 5,
      "status": "offered",
      "offer_date": "2026-09-15",
      "joining_date": null,
      "package": 6.5,
      "id": 3
    },
    {
      "student_id": 3,
      "company_id": 2,
      "job_id": 3,
      "status": "joined",
      "offer_date": "2026-09-15",
      "joining_date": null,
      "package": 7.0,
      "id": 2
    },
    {
      "student_id": 1,
      "company_id": 1,
      "job_id": 1,
      "status": "accepted",
      "offer_date": "2026-09-15",
      "joining_date": null,
      "package": 6.0,
      "id": 1
    }
  ],
  "eligible_students_per_job": [
    {
      "job_id": 1,
      "title": "Python Backend Developer",
      "eligible_students": 3,
      "unverified_students": 0,
      "not_eligible_students": 7
    },
    {
      "job_id": 2,
      "title": "Frontend Developer",
      "eligible_students": 2,
      "unverified_students": 0,
      "not_eligible_students": 8
    },
    {
      "job_id": 3,
      "title": "Data Analyst",
      "eligible_students": 1,
      "unverified_students": 0,
      "not_eligible_students": 9
    },
    {
      "job_id": 4,
      "title": "Cloud Engineering Intern",
      "eligible_students": 1,
      "unverified_students": 0,
      "not_eligible_students": 9
    },
    {
      "job_id": 5,
      "title": "Java Developer",
      "eligible_students": 1,
      "unverified_students": 0,
      "not_eligible_students": 9
    },
    {
      "job_id": 6,
      "title": "Web Development Intern",
      "eligible_students": 2,
      "unverified_students": 0,
      "not_eligible_students": 8
    }
  ],
  "skill_gaps": [
    {
      "skill": "Python",
      "jobs_requiring": 3,
      "students_with_skill": 5,
      "students_without_skill": 5
    },
    {
      "skill": "SQL",
      "jobs_requiring": 3,
      "students_with_skill": 4,
      "students_without_skill": 6
    },
    {
      "skill": "JavaScript",
      "jobs_requiring": 1,
      "students_with_skill": 3,
      "students_without_skill": 7
    },
    {
      "skill": "React",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    },
    {
      "skill": "Pandas",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "Linux",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "Java",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "CSS",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    },
    {
      "skill": "HTML",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    }
  ],
  "department_statistics": [
    {
      "department": "CSE",
      "students": 4,
      "average_cgpa": 8.07
    },
    {
      "department": "ECE",
      "students": 1,
      "average_cgpa": 7.2
    },
    {
      "department": "EEE",
      "students": 1,
      "average_cgpa": 7.6
    },
    {
      "department": "IT",
      "students": 3,
      "average_cgpa": 8.2
    },
    {
      "department": "Mechanical",
      "students": 1,
      "average_cgpa": 6.9
    }
  ],
  "placement_statistics": {
    "total_records": 4,
    "by_status": {
      "accepted": 2,
      "joined": 1,
      "offered": 1
    },
    "average_package_lpa": 6.17
  },
  "definitions": {
    "placed_students": "Distinct students with accepted or joined offers",
    "placement_rate": "Placed students / all students * 100",
    "package": "Annual INR lakhs (LPA)",
    "recent": "Last five records by creation ID",
    "skill_demand": "Required skills only; each job counted once per normalized skill"
  }
}
```

Important errors: No endpoint-specific handled errors; unexpected server failures may return 500.

No filters or pagination. placed_students counts distinct students with accepted/joined offers; rate divides by all students * 100. Average package covers accepted/joined offers, not distinct students. Top skills count normalized manual/extracted union once per student; demand counts required skills once per job. Top lists have at most 10 entries; tie order need not be stable. Skill gaps count students lacking demanded skills. Recent arrays hold up to 5 records, descending by creation ID, not date. by_status includes only present statuses; default absent statuses to zero. Empty databases return zero counts/averages and empty arrays.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/analytics/dashboard'));
```

### Skill analytics

**GET `/api/v1/analytics/skills`**

Purpose: Populate skill supply, demand and gap charts.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "top_skills": [
    {
      "skill": "Python",
      "count": 5
    },
    {
      "skill": "SQL",
      "count": 4
    },
    {
      "skill": "Git",
      "count": 3
    },
    {
      "skill": "JavaScript",
      "count": 3
    },
    {
      "skill": "CSS",
      "count": 2
    },
    {
      "skill": "HTML",
      "count": 2
    },
    {
      "skill": "React",
      "count": 2
    },
    {
      "skill": "Excel",
      "count": 2
    },
    {
      "skill": "FastAPI",
      "count": 1
    },
    {
      "skill": "Machine Learning",
      "count": 1
    }
  ],
  "most_demanded_skills": [
    {
      "skill": "Python",
      "count": 3
    },
    {
      "skill": "SQL",
      "count": 3
    },
    {
      "skill": "JavaScript",
      "count": 1
    },
    {
      "skill": "React",
      "count": 1
    },
    {
      "skill": "Pandas",
      "count": 1
    },
    {
      "skill": "Linux",
      "count": 1
    },
    {
      "skill": "Java",
      "count": 1
    },
    {
      "skill": "CSS",
      "count": 1
    },
    {
      "skill": "HTML",
      "count": 1
    }
  ],
  "skill_gaps": [
    {
      "skill": "Python",
      "jobs_requiring": 3,
      "students_with_skill": 5,
      "students_without_skill": 5
    },
    {
      "skill": "SQL",
      "jobs_requiring": 3,
      "students_with_skill": 4,
      "students_without_skill": 6
    },
    {
      "skill": "JavaScript",
      "jobs_requiring": 1,
      "students_with_skill": 3,
      "students_without_skill": 7
    },
    {
      "skill": "React",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    },
    {
      "skill": "Pandas",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "Linux",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "Java",
      "jobs_requiring": 1,
      "students_with_skill": 1,
      "students_without_skill": 9
    },
    {
      "skill": "CSS",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    },
    {
      "skill": "HTML",
      "jobs_requiring": 1,
      "students_with_skill": 2,
      "students_without_skill": 8
    }
  ]
}
```

Important errors: No endpoint-specific handled errors; unexpected server failures may return 500.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/analytics/skills'));
```

### Eligibility analytics

**GET `/api/v1/analytics/eligibility`**

Purpose: Show eligible student counts per job.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
[
  {
    "job_id": 1,
    "title": "Python Backend Developer",
    "eligible_students": 3,
    "unverified_students": 0,
    "not_eligible_students": 7
  },
  {
    "job_id": 2,
    "title": "Frontend Developer",
    "eligible_students": 2,
    "unverified_students": 0,
    "not_eligible_students": 8
  },
  {
    "job_id": 3,
    "title": "Data Analyst",
    "eligible_students": 1,
    "unverified_students": 0,
    "not_eligible_students": 9
  },
  {
    "job_id": 4,
    "title": "Cloud Engineering Intern",
    "eligible_students": 1,
    "unverified_students": 0,
    "not_eligible_students": 9
  },
  {
    "job_id": 5,
    "title": "Java Developer",
    "eligible_students": 1,
    "unverified_students": 0,
    "not_eligible_students": 9
  },
  {
    "job_id": 6,
    "title": "Web Development Intern",
    "eligible_students": 2,
    "unverified_students": 0,
    "not_eligible_students": 8
  }
]
```

Important errors: No endpoint-specific handled errors; unexpected server failures may return 500.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(API + '/analytics/eligibility'));
```

### Project information

**GET `/`**

Purpose: Show backend project/version/status.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "project": "CAMPUSLINK",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

Important errors: No endpoint-specific handled errors; unexpected server failures may return 500.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(SERVER + '/'));
```

### Health check

**GET `/health`**

Purpose: Check backend and database connectivity.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (**200**):

```json
{
  "status": "healthy",
  "service": "CAMPUSLINK Backend"
}
```

Important errors: No endpoint-specific handled errors; unexpected server failures may return 500.

JavaScript fetch example (uses shared constants/helper):

```javascript
const result = await readJSON(await fetch(SERVER + '/health'));
```

## Opportunity discovery and application operations

All routes below require **no authentication**. Role selection is presentation only. Adzuna search and selected import are implemented below. No scraping, CSV parser, employer messaging or trained model is implemented. External requirement extraction supports degree/branch checks; manual opportunity forms retain their configured skill, CGPA and year checks. JSON import accepts company/college data provided by the user, without verifying its provenance. Job availability does not decrement vacancy_count on an offer; vacancy_count is reported source information.

Close/reopen uses the existing **PATCH `/api/v1/jobs/{job_id}`** with `{"status":"closed"}` or `{"status":"open"}`. Closing hides it from default discovery but preserves applications/offers and historical matching. Company reassignment is rejected with 409 when applications or placements reference the job.

### Discover available opportunities

**GET `/api/v1/opportunities`**

Purpose: Populate the primary opportunity screen. Open jobs only by default.

Path parameters: None.

Query parameters: q (title/company substring), location (substring), job_type (exact), source (exact), status=open|closed|all (default open), skip=0, limit=100 (1-500).

Authentication: **not required**.

Request body: **none**.

Example successful response (200):

```json
[
  {
    "company_id": 4,
    "title": "Web Development Intern",
    "description": "Build practical products as a web development intern.",
    "required_skills": [
      "HTML",
      "CSS"
    ],
    "preferred_skills": [
      "JavaScript",
      "React"
    ],
    "minimum_cgpa": 6.0,
    "graduation_year": 2026,
    "location": "Hyderabad",
    "salary_stipend": "INR 15000/month",
    "job_type": "internship",
    "vacancy_count": null,
    "source_reference": null,
    "source_url": null,
    "status": "open",
    "source": "demo",
    "created_at": "2026-09-30T11:29:06.556263Z",
    "id": 6,
    "company": {
      "name": "Utkal Digital",
      "industry": "Web products",
      "location": "Hyderabad",
      "website": "",
      "description": "Fictional company for the CAMPUSLINK demo.",
      "id": 4
    },
    "external_metadata": null
  }
]
```

Important errors: 422 invalid pagination/status. Empty matches return [].

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/opportunities?source=demo&limit=1"));
```

### Read opportunity details

**GET `/api/v1/opportunities/{job_id}`**

Purpose: Show company, requirements, source, availability and known openings.

Path parameters: job_id: integer, the existing Job ID.

Query parameters: None.

Authentication: **not required**.

Request body: **none**.

Example successful response (200):

```json
{
  "company_id": 1,
  "title": "Example imported role",
  "description": "",
  "required_skills": [
    "Python",
    "SQL"
  ],
  "preferred_skills": [],
  "minimum_cgpa": 0.0,
  "graduation_year": null,
  "location": "",
  "salary_stipend": "",
  "job_type": "full-time",
  "vacancy_count": 3,
  "source_reference": "example-feed-001",
  "source_url": null,
  "status": "open",
  "source": "json_import",
  "created_at": "2026-09-30T11:29:06.624042Z",
  "id": 7,
  "company": {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  },
  "external_metadata": null
}
```

Important errors: 404 missing Job; 422 invalid ID.

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/opportunities/7"));
```

### Add manual opportunity

**POST `/api/v1/opportunities`**

Purpose: Placement officer fallback; source is assigned manual.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: ```json
{
  "company_id": 1,
  "title": "Example manually supplied role",
  "required_skills": [
    "Python"
  ]
}
```

Example successful response (201):

```json
{
  "company_id": 1,
  "title": "Example manually supplied role",
  "description": "",
  "required_skills": [
    "Python"
  ],
  "preferred_skills": [],
  "minimum_cgpa": 0.0,
  "graduation_year": null,
  "location": "",
  "salary_stipend": "",
  "job_type": "full-time",
  "vacancy_count": null,
  "source_reference": null,
  "source_url": null,
  "status": "open",
  "source": "manual",
  "created_at": "2026-09-30T11:29:06.634077Z",
  "id": 8,
  "company": {
    "name": "Odisha Techworks",
    "industry": "Software services",
    "location": "Bhubaneswar",
    "website": "",
    "description": "Fictional company for the CAMPUSLINK demo.",
    "id": 1
  },
  "external_metadata": null
}
```

Important errors: 404 missing company; 422 validation; 409 duplicate company/source/reference.

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/opportunities", {method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({"company_id": 1, "title": "Example manually supplied role", "required_skills": ["Python"]})}));
```

### Import opportunities

**POST `/api/v1/opportunities/import`**

Purpose: Atomic ingestion of 1-100 JobCreate records; source is assigned json_import.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: ```json
{
  "opportunities": [
    {
      "company_id": 1,
      "title": "Example imported role",
      "required_skills": [
        "Python",
        "SQL"
      ],
      "vacancy_count": 3,
      "source_reference": "example-feed-001"
    }
  ]
}
```

Example successful response (201):

```json
[
  {
    "company_id": 1,
    "title": "Example imported role",
    "description": "",
    "required_skills": [
      "Python",
      "SQL"
    ],
    "preferred_skills": [],
    "minimum_cgpa": 0.0,
    "graduation_year": null,
    "location": "",
    "salary_stipend": "",
    "job_type": "full-time",
    "vacancy_count": 3,
    "source_reference": "example-feed-001",
    "source_url": null,
    "status": "open",
    "source": "json_import",
    "created_at": "2026-09-30T11:29:06.624042Z",
    "id": 7,
    "company": {
      "name": "Odisha Techworks",
      "industry": "Software services",
      "location": "Bhubaneswar",
      "website": "",
      "description": "Fictional company for the CAMPUSLINK demo.",
      "id": 1
    },
    "external_metadata": null
  }
]
```

Important errors: 404 missing company; 422 invalid payload or batch length; 409 duplicate non-null reference per company/source (also within batch). No rows from a failed batch persist.

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/opportunities/import", {method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({"opportunities": [{"company_id": 1, "title": "Example imported role", "required_skills": ["Python", "SQL"], "vacancy_count": 3, "source_reference": "example-feed-001"}]})}));
```

### List applications

**GET `/api/v1/applications`**

Purpose: List interest/stages and linked offer status. Names are joined from current records.

Path parameters: None.

Query parameters: student_id and job_id optional integer filters; skip=0, limit=100 (1-500).

Authentication: **not required**.

Request body: **none**.

Example successful response (200):

```json
[
  {
    "student_id": 7,
    "job_id": 7,
    "id": 1,
    "status": "shortlisted",
    "created_at": "2026-09-30T11:29:06.646210Z",
    "updated_at": "2026-09-30T11:29:06.658229Z",
    "student_name": "Riya Behera",
    "job_title": "Example imported role",
    "company_name": "Odisha Techworks",
    "placement_id": null,
    "placement_status": null
  }
]
```

Important errors: 422 invalid query values. Empty matches return [].

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/applications?student_id=7"));
```

### Express interest

**POST `/api/v1/applications`**

Purpose: Record an eligible student's interest in an open opportunity; no external submission.

Path parameters: None.

Query parameters: None.

Authentication: **not required**.

Request body: ```json
{
  "student_id": 7,
  "job_id": 7
}
```

Example successful response (201):

```json
{
  "student_id": 7,
  "job_id": 7,
  "id": 1,
  "status": "interested",
  "created_at": "2026-09-30T11:29:06.646210Z",
  "updated_at": "2026-09-30T11:29:06.646213Z",
  "student_name": "Riya Behera",
  "job_title": "Example imported role",
  "company_name": "Odisha Techworks",
  "placement_id": null,
  "placement_status": null
}
```

Important errors: 404 missing student/job; 409 closed opportunity, failed eligibility, or duplicate student/job; 422 validation.

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/applications", {method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({"student_id": 7, "job_id": 7})}));
```

### Update application stage

**PATCH `/api/v1/applications/{application_id}/status`**

Purpose: Officer updates interested, shortlisted, interview, selected, rejected or withdrawn. Stage transitions are unrestricted; offer status remains on Placement.

Path parameters: application_id: integer.

Query parameters: None.

Authentication: **not required**.

Request body: ```json
{
  "status": "shortlisted"
}
```

Example successful response (200):

```json
{
  "student_id": 7,
  "job_id": 7,
  "id": 1,
  "status": "shortlisted",
  "created_at": "2026-09-30T11:29:06.646210Z",
  "updated_at": "2026-09-30T11:29:06.658229Z",
  "student_name": "Riya Behera",
  "job_title": "Example imported role",
  "company_name": "Odisha Techworks",
  "placement_id": null,
  "placement_status": null
}
```

Important errors: 404 missing application; 422 unsupported status or fields.

JavaScript fetch example:

```javascript
const result = await readJSON(await fetch(API + "/applications/1/status", {method: "PATCH", headers: {"Content-Type":"application/json"}, body: JSON.stringify({"status": "shortlisted"})}));
```

### Dashboard additions

The existing dashboard response additionally contains:

- available_opportunities: open Job count.
- eligible_matches: number of eligible student/open-opportunity pairs, not distinct students.
- known_vacancies: sum of non-null vacancy_count on open jobs; zero means no known openings counted, not proof that none exist.
- opportunities_without_vacancy_count: open records with unknown count.
- opportunity_sources: open records grouped by source.
- application_statistics: application counts by current stage.
- latest_opportunities: up to five open records, descending creation ID.

Existing skill demand/gap and eligible_students_per_job fields include all jobs, including closed records. Placed students remain distinct accepted/joined students. No fabricated average fit or market trends are returned.

## Adzuna external search and selected import

### Search Adzuna (does not store jobs)

**GET `/api/v1/opportunities/external/adzuna`**

Purpose: fetch a bounded India search page through the backend. No path parameters or request body. Authentication: none. Provider credentials are server environment configuration, never frontend parameters.

Query also accepts sort_by=date|relevance (default date) and focus=all|fresher|internship|junior (default all). Focus maps to supported Adzuna what_or keyword hints, not verified experience. There is no native experience-range filter.

Query: query string (default software engineer, length 1-150), location string (default India, max 150), page integer 1-100 (default 1), limit integer 1-20 (default 10). India means country-wide; other locations are forwarded as Adzuna's geographic search. Remote is a location search, not a guaranteed remote-work filter.

200 response example (illustrative test fixture, not a claimed live vacancy):

```json
{
  "source": "adzuna",
  "country": "in",
  "query": "python",
  "location": "Bengaluru",
  "page": 1,
  "limit": 5,
  "total_available": 1,
  "results": [
    {
      "source": "adzuna",
      "source_reference": "in:provider-123",
      "source_url": "https://www.adzuna.in/land/ad/provider-123",
      "title": "Python Developer",
      "company_name": "Research Systems",
      "description": "Python SQL FastAPI Docker",
      "location": "Bengaluru",
      "job_type": "full-time",
      "vacancy_count": null,
      "salary_stipend": "",
      "minimum_cgpa": 0,
      "graduation_year": null,
      "required_skills": [],
      "preferred_skills": [
        "Docker",
        "FastAPI",
        "Python",
        "SQL"
      ],
      "external_metadata": {
        "external_id": "provider-123",
        "country": "in",
        "posted_at": "2026-09-20T10:30:00+00:00",
        "category": "IT Jobs",
        "contract_type": "permanent",
        "contract_time": "full_time",
        "detected_skills": [
          "Docker",
          "FastAPI",
          "Python",
          "SQL"
        ],
        "skill_method": "Explicit mandatory clauses; other keyword mentions are preferred signals",
        "credential_tracking_removed": false,
        "requirements_verified": false,
        "description_is_snippet": true,
        "notice": "Extracted requirements are automated interpretations of a provider snippet. Please review the original listing before making an application decision.",
        "original_description": "Python SQL FastAPI Docker",
        "requirement_analysis": {
          "version": 3,
          "status": "INSUFFICIENT_DATA",
          "technical_skills": [
            "Docker",
            "FastAPI",
            "Python",
            "SQL"
          ],
          "required_skills": null,
          "preferred_skills": [
            "Docker",
            "FastAPI",
            "Python",
            "SQL"
          ],
          "minimum_experience": null,
          "maximum_experience": null,
          "experience_detected": false,
          "education_requirements": null,
          "branch_restrictions": null,
          "graduation_years": null,
          "job_category": "Full-time",
          "category_method": "keyword/source",
          "warnings": [
            "No required skills extracted; mandatory skill coverage is unavailable.",
            "Experience requirement: Not verified",
            "Education requirement: Not verified",
            "The provider supplies a description snippet; omitted requirements cannot be verified."
          ],
          "field_evidence": {
            "experience": [],
            "education": [],
            "branch": [],
            "graduation_years": []
          },
          "evidence": [
            {
              "text": "Python SQL FastAPI Docker",
              "skills": [
                "Docker",
                "FastAPI",
                "Python",
                "SQL"
              ],
              "method": "keyword",
              "mandatory": false
            }
          ],
          "ambiguous": false,
          "description_is_snippet": true
        }
      }
    }
  ],
  "skipped": 0,
  "cached": false,
  "searched_at": "2026-09-30T12:00:00+00:00",
  "expires_in_seconds": 300,
  "search_token": "opaque-token-returned-by-search-use-actual-value",
  "stored": false,
  "sort_by": "date",
  "focus": "all"
}
```

Token validity is five minutes from the original fetch, not renewed on cache hits. At most 32 cached searches are retained per backend process. Search skips malformed/duplicate records. Search results require an actual company name, stable ID and safe provider URL; unknown companies are not invented. total_available is the provider count, not the number imported or a vacancy count.

Errors: 503 configuration absent or provider credentials/access rejected; 429 local cooldown/provider rate limit (Retry-After header); 504 timeout/connection failure; 502 invalid/unreadable upstream response or other provider failure; 422 invalid local parameters. Raw provider bodies, credential URLs and exception messages are not returned.

```javascript
const result = await readJSON(await fetch(API + '/opportunities/external/adzuna?' + new URLSearchParams({query:'python developer',location:'Bengaluru',page:1,limit:5})));
```

### Import or refresh selected Adzuna results

**POST `/api/v1/opportunities/import/adzuna`**

Purpose: store explicit selections from a recent backend search; return existing JobRead records for normal CAMPUSLINK matching. No path/query parameters. Authentication: none. JSON body contains search_token (20-100 characters) and references (1-20 source references). Client-supplied listing contents are not accepted.

```json
{
  "search_token": "opaque-token-returned-by-search-use-actual-value",
  "references": [
    "in:provider-123"
  ]
}
```

200 response has exactly these envelope fields: created (integer), updated (integer), stored (true), opportunities (array of full JobRead objects, including nested company). Each returned JobRead has a stable id, source adzuna, source_reference, safe source_url, and external_metadata. Use the returned IDs immediately with the existing matching, application and placement routes. The detailed JobRead shape is unchanged except the additive optional external_metadata object; other sources return null.

Example successful 200 response (captured using a mocked provider in an isolated database):

```json
{
  "created": 1,
  "updated": 0,
  "stored": true,
  "opportunities": [
    {
      "company_id": 5,
      "title": "Python Developer",
      "description": "Python SQL FastAPI Docker",
      "required_skills": [],
      "preferred_skills": [
        "Docker",
        "FastAPI",
        "Python",
        "SQL"
      ],
      "minimum_cgpa": 0.0,
      "graduation_year": null,
      "location": "Bengaluru",
      "salary_stipend": "",
      "job_type": "full-time",
      "vacancy_count": null,
      "source_reference": "in:provider-123",
      "source_url": "https://www.adzuna.in/land/ad/provider-123",
      "status": "open",
      "external_metadata": {
        "external_id": "provider-123",
        "country": "in",
        "posted_at": "2026-09-20T10:30:00+00:00",
        "category": "IT Jobs",
        "contract_type": "permanent",
        "contract_time": "full_time",
        "detected_skills": [
          "Docker",
          "FastAPI",
          "Python",
          "SQL"
        ],
        "skill_method": "Explicit mandatory clauses; other keyword mentions are preferred signals",
        "credential_tracking_removed": false,
        "requirements_verified": false,
        "description_is_snippet": true,
        "notice": "Extracted requirements are automated interpretations of a provider snippet. Please review the original listing before making an application decision.",
        "fetched_at": "2026-09-30T12:42:47.413385+00:00",
        "source_company_name": "Research Systems",
        "original_description": "Python SQL FastAPI Docker",
        "requirement_analysis": {
          "version": 3,
          "status": "INSUFFICIENT_DATA",
          "technical_skills": [
            "Docker",
            "FastAPI",
            "Python",
            "SQL"
          ],
          "required_skills": null,
          "preferred_skills": [
            "Docker",
            "FastAPI",
            "Python",
            "SQL"
          ],
          "minimum_experience": null,
          "maximum_experience": null,
          "experience_detected": false,
          "education_requirements": null,
          "branch_restrictions": null,
          "graduation_years": null,
          "job_category": "Full-time",
          "category_method": "keyword/source",
          "warnings": [
            "No required skills extracted; mandatory skill coverage is unavailable.",
            "Experience requirement: Not verified",
            "Education requirement: Not verified",
            "The provider supplies a description snippet; omitted requirements cannot be verified."
          ],
          "field_evidence": {
            "experience": [],
            "education": [],
            "branch": [],
            "graduation_years": []
          },
          "evidence": [
            {
              "text": "Python SQL FastAPI Docker",
              "skills": [
                "Docker",
                "FastAPI",
                "Python",
                "SQL"
              ],
              "method": "keyword",
              "mandatory": false
            }
          ],
          "ambiguous": false,
          "description_is_snippet": true
        }
      },
      "source": "adzuna",
      "created_at": "2026-09-30T12:42:47.424240Z",
      "id": 7,
      "company": {
        "name": "Research Systems",
        "industry": "",
        "location": "",
        "website": "",
        "description": "",
        "id": 5
      }
    }
  ]
}
```

external_metadata adds fetched_at and source_company_name on import. posted_at is the source timestamp or null; Job.created_at is the local import timestamp. Refresh preserves company association, officer-edited requirements, status, original import date and lifecycle records. Preferred keyword signals refresh only when they still match the previous detected set. Deduplication uses country-prefixed source_reference, backed by a unique Adzuna reference index.

Errors: 409 expired/evicted token or backend restart (search again); 422 reference not from this search or invalid body; 503 missing credentials. A refresh does not reopen a manually closed opportunity.

```javascript
const stored = await readJSON(await fetch(API + '/opportunities/import/adzuna', {
  method:'POST', headers:{'Content-Type':'application/json'},
  body:JSON.stringify({search_token:result.search_token,references:[result.results[0].source_reference]})
}));
```

Important: mandatory clauses yield required skills; other dictionary mentions are preferred signals. Empty external required skills return null coverage, never 100%. Eligibility is UNVERIFIED unless a known failure makes it NOT_ELIGIBLE. Adzuna description snippets cannot establish complete requirements. Fit is provisional when eligibility is unverified or skill coverage unavailable. Display the returned notice and original listing prominently. No invented vacancy count, salary, year or CGPA restriction is supplied. source_url preserves the provider redirect destination but removes credential-bearing tracking parameters (Adzuna may embed the app ID in utm_source). Original listing clicks leave CAMPUSLINK; local interest does not submit an employer application.

## Requirement intelligence and tri-state eligibility

All matching endpoints share the same backend decision. `status` is `ELIGIBLE`,
`NOT_ELIGIBLE`, or `UNVERIFIED`; compatibility `eligible` is true only for ELIGIBLE.
Known failures take precedence over unknowns. `checks` explains each evaluated
requirement; `missing_requirements` lists failures; `unknown_requirements` lists
unresolved checks. `requirement_analysis` is null for configured manual/demo jobs.
External analysis also lives in `external_metadata.requirement_analysis`, alongside
`original_description`, source URL, source reference and existing provider metadata.

Extraction fields: version, status (COMPLETE/PARTIAL/INSUFFICIENT_DATA), technical_skills,
nullable required_skills, preferred_skills, nullable minimum_experience/maximum_experience,
experience_detected, nullable education_requirements/branch_restrictions/graduation_years,
job_category, category_method, warnings, evidence, field_evidence, ambiguous,
and description_is_snippet. Null restrictions mean not extracted, not confirmed absence.
Explicit evidence and keyword interpretations are distinguished. Adzuna snippets remain
PARTIAL or INSUFFICIENT_DATA even when some mandatory requirements are extracted.

Skill-gap adds eligibility, eligibility_status, coverage_available and coverage_note.
Null skill_match_percentage must display "Skill coverage unavailable". Fit adds provisional;
the unavailable skills component has score=null, available=false and contribution=0.
The six existing weights remain unchanged. No weight redistribution occurs. Other component
scores remain visible; a provisional score does not authorize interest or an application.

Dashboard eligible_matches counts verified student/open-opportunity pairs only.
unverified_matches and not_eligible_matches partition the remaining evaluated open pairs.
Per-job eligibility analytics adds unverified_students and not_eligible_students;
those per-job results include closed jobs. POST applications returns 409 for unverified
eligibility as well as unmet requirements. Existing applications and placements remain.

Only ELIGIBLE belongs in Eligible Matches or Suitable Candidates rankings. Display
UNVERIFIED in amber with warnings and a provisional score when returned. Keep original
Adzuna attribution/link visible and review the original before an application decision.
Search controls use the [official Adzuna search parameters](https://developer.adzuna.com/swagger/spec/test2.json).

## RECOMMENDED FRONTEND FLOW

1. **Load dashboard:** GET `/api/v1/analytics/dashboard`; bind cards and charts to returned fields.
2. **Load students:** GET `/api/v1/students`; retain IDs and display names/department/CGPA. Paginate if needed.
3. **Load companies:** GET `/api/v1/companies`; build an ID-to-name map.
4. **Discover opportunities:** GET `/api/v1/opportunities`; filter availability, title/company, location, type and source. Display provenance and requirements. Save the shared job ID.
5. **Select student:** use the list entry or GET `/api/v1/students/{student_id}`.
6. **Check eligibility:** GET `/api/v1/matching/eligibility` with student_id and job_id query parameters. Display reasons even for eligible: false.
7. **Generate candidate-job fit score:** GET `/api/v1/matching/fit` with the same IDs; show score, strengths, suggestions and explanation.
8. **Show matched/missing skills:** the fit response includes these. GET `/api/v1/matching/skill-gap` with the same IDs for a standalone skill-gap view.
9. **Upload resume:** POST `/api/v1/students/{student_id}/resume` with FormData. Show warnings, then reload student, eligibility, fit, skill gaps and dashboard.
10. **Express interest:** POST `/api/v1/applications` using student_id/job_id. Officer updates its stage through PATCH `/api/v1/applications/{application_id}/status`. Interest does not contact an employer.
11. **Show placement/offer information:** GET `/api/v1/placements` with optional student_id filter. Join names from loaded lists. POST `/api/v1/placements` records an offer; PATCH `/api/v1/placements/{placement_id}/status` changes status. Refresh offers and dashboard afterward.

Use loading/error states. Render user-entered/uploaded text using textContent. Placement deletion and general editing are not available.

## Endpoint verification

All method/path pairs were checked against generated OpenAPI and actual registered routes. Every operation example was executed successfully against the actual app in an isolated temporary database, including upload/download and 204 deletes. Every JSON block was parsed. The guide includes profile, opportunity and application additions. Run tests/verify_frontend_contract.py to check every documented method/path pair against current OpenAPI and parse every JSON block.

## Feature summary

Paths are exact server paths. Query parameters are detailed above. Full request examples and field constraints appear in the operation sections.

| Feature | Method | Endpoint | Request Body | Response Purpose |
|---|---|---|---|---|
| List students | GET | `/api/v1/students` | None | Populate the students list. |
| Create student | POST | `/api/v1/students` | student JSON | Create a student record. |
| Get student | GET | `/api/v1/students/{student_id}` | None | Load one student record. |
| Update student | PATCH | `/api/v1/students/{student_id}` | Partial resource JSON | Update supplied student fields. |
| Delete student | DELETE | `/api/v1/students/{student_id}` | None | Delete a student record. |
| List companies | GET | `/api/v1/companies` | None | Populate the companies list. |
| Create company | POST | `/api/v1/companies` | company JSON | Create a company record. |
| Get company | GET | `/api/v1/companies/{company_id}` | None | Load one company record. |
| Update company | PATCH | `/api/v1/companies/{company_id}` | Partial resource JSON | Update supplied company fields. |
| Delete company | DELETE | `/api/v1/companies/{company_id}` | None | Delete a company record. |
| List jobs | GET | `/api/v1/jobs` | None | Populate the jobs list. |
| Create job | POST | `/api/v1/jobs` | job JSON | Create a job record. |
| Get job | GET | `/api/v1/jobs/{job_id}` | None | Load one job record. |
| Update job | PATCH | `/api/v1/jobs/{job_id}` | Partial resource JSON | Update supplied job fields. |
| Delete job | DELETE | `/api/v1/jobs/{job_id}` | None | Delete a job record. |
| Student-job eligibility | GET | `/api/v1/matching/eligibility` | None | Check CGPA, graduation year and all required skills. |
| Candidate-job fit score | GET | `/api/v1/matching/fit` | None | Show 0-100 explainable fit and independent eligibility. |
| Skill-gap analysis | GET | `/api/v1/matching/skill-gap` | None | Show matched/missing skills and learning priorities. |
| Upload resume | POST | `/api/v1/students/{student_id}/resume` | Multipart file | Store/replace resume and extracted skills. |
| Read resume information | GET | `/api/v1/students/{student_id}/resume` | None | Read filename, extracted text and skills. |
| Download resume | GET | `/api/v1/students/{student_id}/resume/download` | None | Download original uploaded file. |
| List placements | GET | `/api/v1/placements` | None | Show placement/offer information. |
| Create placement | POST | `/api/v1/placements` | placement JSON | Record an offer. |
| Update placement status | PATCH | `/api/v1/placements/{placement_id}/status` | {"status":"accepted"} | Change offer status. |
| Dashboard analytics | GET | `/api/v1/analytics/dashboard` | None | Populate dashboard counts, charts, recent activity and placement statistics. |
| Skill analytics | GET | `/api/v1/analytics/skills` | None | Populate skill supply, demand and gap charts. |
| Eligibility analytics | GET | `/api/v1/analytics/eligibility` | None | Show eligible student counts per job. |
| Project information | GET | `/` | None | Show backend project/version/status. |
| Health check | GET | `/health` | None | Check backend and database connectivity. |
| Discover available opportunities | GET | `/api/v1/opportunities` | None | Populate the primary opportunity screen. Open jobs only by default. |
| Read opportunity details | GET | `/api/v1/opportunities/{job_id}` | None | Show company, requirements, source, availability and known openings. |
| Add manual opportunity | POST | `/api/v1/opportunities` | JSON (exact example above) | Placement officer fallback; source is assigned manual. |
| Import opportunities | POST | `/api/v1/opportunities/import` | JSON (exact example above) | Atomic ingestion of 1-100 JobCreate records; source is assigned json_import. |
| List applications | GET | `/api/v1/applications` | None | List interest/stages and linked offer status. Names are joined from current records. |
| Express interest | POST | `/api/v1/applications` | JSON (exact example above) | Record an eligible student's interest in an open opportunity; no external submission. |
| Update application stage | PATCH | `/api/v1/applications/{application_id}/status` | JSON (exact example above) | Officer updates interested, shortlisted, interview, selected, rejected or withdrawn. Stage transitions are unrestricted; offer status remains on Placement. |
| Search external listings | GET | `/api/v1/opportunities/external/adzuna` | None | Bounded read-only Adzuna results and import token. |
| Import selected external listings | POST | `/api/v1/opportunities/import/adzuna` | search_token, references | Created/refreshed stored JobRead records. |
