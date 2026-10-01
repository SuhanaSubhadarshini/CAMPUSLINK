"""Bounded, server-only Adzuna search and explicit import into the existing Job table."""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
import os
import re
import secrets
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, unquote_plus
from urllib.request import Request, build_opener, HTTPRedirectHandler
from fastapi import HTTPException
from sqlalchemy import select
from ..models import Company, Job
from ..schemas import JobRead
from .skill_extractor import extract_skills
from .requirement_extractor import extract_requirements, EXTERNAL_NOTICE

TTL = 300
MAX_CACHE = 32
_cache = OrderedDict()
_lock = threading.Lock()
_next_request = 0.0
SKILL_NOTE = EXTERNAL_NOTICE


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward credentials to another destination.


def _fetch(params):
    """No HTTP client URL logging, raw exceptions, redirects, or unbounded response reads."""
    url = "https://api.adzuna.com/v1/api/jobs/in/search/" + str(params.pop("page"))
    request = Request(url + "?" + urlencode(params), headers={"Accept": "application/json"})
    with build_opener(NoRedirect).open(request, timeout=12) as response:
        content = response.read(2 * 1024 * 1024 + 1)
        if len(content) > 2 * 1024 * 1024:
            raise ValueError("Response too large")
        return json.loads(content)


def _credentials():
    values = tuple(os.getenv(k, "").strip() for k in ("ADZUNA_APP_ID", "ADZUNA_APP_KEY"))
    if not all(values):
        raise HTTPException(503, "Adzuna is not configured. Set backend environment credentials and restart the server.")
    return values


def _text(value, maximum=20000):
    if not isinstance(value, str):
        return ""
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", value)).split())[:maximum]


def _company_key(name):
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


def _normalize(raw, credentials):
    if not isinstance(raw, dict):
        return None
    # Treat accidental upstream credential echoes as invalid records, not display data.
    serialized = json.dumps({k:v for k,v in raw.items() if k != "redirect_url"})
    if any(secret in serialized for secret in credentials):
        return None
    identity = raw.get("id")
    if not isinstance(identity, (str, int)) or isinstance(identity, bool):
        return None
    identity = str(identity)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", identity):
        return None
    title = _text(raw.get("title"), 150)
    company = raw.get("company")
    company = _text(company.get("display_name"), 150) if isinstance(company, dict) else ""
    if not title or not company:
        return None  # Existing Company model requires a name; never invent an employer.
    url = raw.get("redirect_url")
    if not isinstance(url, str) or len(url) > 2000:
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        # Adzuna embeds the app ID in utm_source. Remove only credential-bearing
        # tracking/auth parameters, preserving the provider redirect path and other tokens.
        safe_parts = []
        for part in parsed.query.split("&"):
            key, _, value = part.partition("=")
            if unquote_plus(key).lower() in {"app_id", "app_key", "api_key", "authorization"} or any(secret in unquote_plus(value) for secret in credentials):
                continue
            if part:
                safe_parts.append(part)
        url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "&".join(safe_parts), parsed.fragment))
        if any(secret in unquote_plus(url) for secret in credentials):
            return None
    except ValueError:
        return None
    # Preserve provider redirect destination, with credential-bearing tracking removed.
    original_description = raw.get("description") if isinstance(raw.get("description"), str) else ""
    description = _text(original_description, len(original_description) + 1)
    location = raw.get("location")
    location = _text(location.get("display_name"), 500) if isinstance(location, dict) else ""
    category = raw.get("category")
    category = _text(category.get("label"), 200) if isinstance(category, dict) else ""
    posted = None
    if isinstance(raw.get("created"), str):
        try:
            value = datetime.fromisoformat(raw["created"].replace("Z", "+00:00"))
            if value.tzinfo is not None:
                posted = value.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    contract = _text(raw.get("contract_type"), 100) or None
    contract_time = _text(raw.get("contract_time"), 100) or None
    kind = {"full_time": "full-time", "part_time": "part-time"}.get(contract_time, "unknown")
    if kind == "unknown" and contract == "contract":
        kind = "contract"
    # Reuse the project's deterministic vocabulary, plus explicit technical names absent from it.
    skills = set(extract_skills(description))
    for skill in ("Deep Learning", "TensorFlow", "PyTorch"):
        if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", description, re.I):
            skills.add(skill)
    skills = sorted(skills, key=str.casefold)
    analysis = extract_requirements(original_description, title, kind, snippet=True)
    return {"source": "adzuna", "source_reference": "in:" + identity, "source_url": url,
            "title": title, "company_name": company, "description": description, "location": location,
            "job_type": kind, "vacancy_count": None, "salary_stipend": "", "minimum_cgpa": 0,
            "graduation_year": None, "required_skills": analysis["required_skills"] or [], "preferred_skills": analysis["preferred_skills"],
            "external_metadata": {"original_description": original_description, "requirement_analysis": analysis, "external_id": identity, "country": "in", "posted_at": posted,
                "category": category or None, "contract_type": contract, "contract_time": contract_time,
                "detected_skills": skills, "skill_method": "Explicit mandatory clauses; other keyword mentions are preferred signals",
                "credential_tracking_removed": url != raw["redirect_url"],
                "requirements_verified": False, "description_is_snippet": True, "notice": SKILL_NOTE}}


def search(query, location, page, limit, sort_by="date", focus="all"):
    global _next_request
    credentials = _credentials()
    fingerprint = sha256("\0".join(credentials).encode()).hexdigest()
    key = (fingerprint, query.strip(), location.strip(), page, limit, sort_by, focus)
    with _lock:
        now = time.monotonic()
        for old_key in list(_cache):
            if _cache[old_key]["expires"] <= now:
                del _cache[old_key]
        if key in _cache:
            result = deepcopy(_cache[key]["response"])
            result["cached"] = True
            return result
        if now < _next_request:
            raise HTTPException(429, "Please wait before another Adzuna search.", headers={"Retry-After": str(max(1, int(_next_request-now)+1))})
        _next_request = now + 5
        params = {"page": page, "app_id": credentials[0], "app_key": credentials[1],
                  "what": query.strip(), "results_per_page": limit, "sort_by": sort_by, "content-type": "application/json"}
        hints = {"fresher": "fresher graduate entry-level", "internship": "intern internship", "junior": "junior"}
        if focus in hints:
            params["what_or"] = hints[focus]
        if location.strip() and location.strip().casefold() != "india":
            params["where"] = location.strip()
        try:
            data = _fetch(params)
        except HTTPError as error:
            if error.code in (401, 403):
                raise HTTPException(503, "Adzuna rejected the server credentials or account access. Check backend configuration.") from None
            if error.code == 429:
                _next_request = time.monotonic() + 60
                raise HTTPException(429, "Adzuna rate limit reached. Wait before trying again.", headers={"Retry-After": "60"}) from None
            if error.code == 400:
                raise HTTPException(502, "Adzuna could not process this search. Try a different keyword or location.") from None
            raise HTTPException(502, "Adzuna is temporarily unavailable. Please try again later.") from None
        except (TimeoutError, URLError, OSError):
            raise HTTPException(504, "Adzuna could not be reached in time. Please try again later.") from None
        except (ValueError, TypeError):
            raise HTTPException(502, "Adzuna returned an unreadable response. Please try again later.") from None
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise HTTPException(502, "Adzuna returned an invalid result format.")
        rows, seen, skipped = [], set(), 0
        for raw in data["results"][:limit]:
            row = _normalize(raw, credentials)
            if row is None or row["source_reference"] in seen:
                skipped += 1
                continue
            seen.add(row["source_reference"])
            rows.append(row)
        count = data.get("count")
        response = {"source": "adzuna", "country": "in", "query": query, "location": location,
                    "page": page, "limit": limit, "sort_by": sort_by, "focus": focus, "total_available": count if type(count) is int and count >= 0 else None,
                    "results": rows, "skipped": skipped, "cached": False,
                    "searched_at": datetime.now(timezone.utc).isoformat(), "expires_in_seconds": TTL,
                    "search_token": secrets.token_urlsafe(32), "stored": False}
        _cache[key] = {"expires": time.monotonic()+TTL, "response": deepcopy(response)}
        while len(_cache) > MAX_CACHE:
            _cache.popitem(last=False)
        return response


def import_selected(db, token, references):
    _credentials()
    with _lock:
        entry = next((x for x in _cache.values() if x["response"]["search_token"] == token and x["expires"] > time.monotonic()), None)
        if entry is None:
            raise HTTPException(409, "Search results expired or server restarted. Search again before importing.")
        rows = {x["source_reference"]: deepcopy(x) for x in entry["response"]["results"]}
        if any(ref not in rows for ref in references):
            raise HTTPException(422, "Select only listings from this search result.")
    # Serialize SQLite upserts across processes; preserve Job IDs and all lifecycle links.
    db.connection().exec_driver_sql("BEGIN IMMEDIATE")
    companies = {_company_key(c.name): c for c in db.scalars(select(Company)).all()}
    created, updated, items = 0, 0, []
    for ref in dict.fromkeys(references):
        row = rows[ref]
        company_name = row.pop("company_name")
        item = db.scalar(select(Job).where(Job.source == "adzuna", Job.source_reference == ref))
        row["external_metadata"]["fetched_at"] = entry["response"]["searched_at"]
        row["external_metadata"]["source_company_name"] = company_name
        if item is None:
            company = companies.get(_company_key(company_name))
            if company is None:
                company = Company(name=company_name)
                db.add(company)
                db.flush()
                companies[_company_key(company_name)] = company
            item = Job(**row, company_id=company.id, status="open")
            db.add(item)
            created += 1
        else:
            # Refresh source facts, preserving officer-edited eligibility/skills, company and status.
            old_analysis = (item.external_metadata or {}).get("requirement_analysis") or {}
            if item.required_skills == (old_analysis.get("required_skills") or []):
                item.required_skills = row["required_skills"]
            if item.preferred_skills == old_analysis.get("preferred_skills", (item.external_metadata or {}).get("detected_skills", [])):
                item.preferred_skills = row["preferred_skills"]
            for field in ("title", "description", "location", "job_type", "source_url", "external_metadata"):
                setattr(item, field, row[field])
            updated += 1
        db.flush()
        items.append(item)
    db.commit()
    return {"created": created, "updated": updated, "stored": True,
            "opportunities": [JobRead.model_validate(x).model_dump(mode="json") for x in items]}
