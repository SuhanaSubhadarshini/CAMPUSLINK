from .skill_extractor import normalize_skills
from .requirement_extractor import external_analysis, required_skills, degrees, branches


def student_skills(student):
    return set(normalize_skills(student.skills + student.extracted_skills))


def _skill_gap(student, job):
    available = student_skills(student)
    required = set(required_skills(job))
    preferred = set(normalize_skills(job.preferred_skills)) - required
    matched = sorted(available & required)
    missing = sorted(required - available)
    optional = sorted(preferred - available)
    return {
        "student_id": student.id, "job_id": job.id,
        "matched_skills": matched, "missing_skills": missing,
        "skill_match_percentage": round(100 * len(matched) / len(required), 2) if required else (None if external_analysis(job) else 100.0),
        "matched_preferred_skills": sorted(available & preferred),
        "missing_preferred_skills": optional,
        "recommended_skills_to_learn": missing + optional,
        "priorities": [{"skill": s, "priority": "high", "reason": "Required by job"} for s in missing]
        + [{"skill": s, "priority": "medium", "reason": "Preferred by job"} for s in optional],
    }


def eligibility(student, job):
    missing, unknown, checks = [], [], []
    def check(name, expected, actual, passed):
        status = "UNVERIFIED" if passed is None else "ELIGIBLE" if passed else "NOT_ELIGIBLE"
        item = {"requirement": name, "expected": expected, "actual": actual, "status": status}
        checks.append(item)
        if passed is None:
            unknown.append(item)
        elif not passed:
            missing.append(item)
    if job.source != "adzuna" or job.minimum_cgpa > 0:
        check("cgpa", job.minimum_cgpa, student.cgpa, student.cgpa >= job.minimum_cgpa)
    if job.graduation_year is not None:
        check("graduation_year", job.graduation_year, student.graduation_year, student.graduation_year == job.graduation_year)
    gap = _skill_gap(student, job)
    if gap["missing_skills"]:
        missing.append({"requirement": "required_skills", "missing": gap["missing_skills"]})
    if required_skills(job):
        checks.append({"requirement": "required_skills", "expected": required_skills(job), "actual": sorted(student_skills(student)), "status": "NOT_ELIGIBLE" if gap["missing_skills"] else "ELIGIBLE"})
    analysis = external_analysis(job)
    if analysis:
        if not required_skills(job):
            check("required_skills", "No required skills extracted", None, None)
        experience = getattr(student, 'professional_experience_years', None)
        low, high = analysis['minimum_experience'], analysis['maximum_experience']
        check("professional_experience_years", {"minimum": low, "maximum": high}, experience,
              None if not analysis['experience_detected'] or experience is None else (low is None or experience >= low) and (high is None or experience <= high))
        expected = analysis['education_requirements']
        actual = degrees(student.degree)
        compatible = set(actual)
        if 'B.Tech/B.E.' in compatible:
            compatible.add('Bachelor')
        if compatible & {'M.Tech/M.E.', 'MCA'}:
            compatible.add('Master')
        check("degree", expected, student.degree or None, bool(compatible & set(expected)) if expected and actual else None)
        if analysis['branch_restrictions']:
            actual_branch = branches(student.department)
            check("branch", analysis['branch_restrictions'], student.department, bool(set(actual_branch) & set(analysis['branch_restrictions'])) if actual_branch else None)
        if analysis['graduation_years']:
            check("graduation_year", analysis['graduation_years'], student.graduation_year, student.graduation_year in analysis['graduation_years'])
        if analysis['status'] != 'COMPLETE':
            check("extraction", analysis['status'], analysis['warnings'], None)
    status = "NOT_ELIGIBLE" if missing else "UNVERIFIED" if unknown else "ELIGIBLE"
    reasons = ["Missing required skills: " + ", ".join(x['missing']) if 'missing' in x else f"{x['requirement']}: expected {x['expected']}; actual {x['actual']}." for x in missing]
    reasons += [f"{x['requirement']}: not verified." for x in unknown]
    return {"student_id": student.id, "job_id": job.id, "eligible": status == "ELIGIBLE", "status": status,
            "reasons": reasons or ["All basic eligibility requirements are satisfied."], "missing_requirements": missing,
            "unknown_requirements": unknown, "checks": checks, "requirement_analysis": analysis}


def skill_gap(student, job):
    gap = _skill_gap(student, job)
    result = eligibility(student, job)
    return {**gap, "eligibility_status": result['status'], "eligibility": result,
            "coverage_available": gap['skill_match_percentage'] is not None,
            "coverage_note": "No required skills extracted" if gap['skill_match_percentage'] is None else None}


def match(student, job):
    gap = skill_gap(student, job)
    required_pct = gap["skill_match_percentage"]
    coverage_available = required_pct is not None
    required_pct = required_pct if coverage_available else 0
    preferred_count = len(gap["matched_preferred_skills"]) + len(gap["missing_preferred_skills"])
    preferred_pct = 100 * len(gap["matched_preferred_skills"]) / preferred_count if preferred_count else required_pct
    skill_score = (0.8 * required_pct + 0.2 * preferred_pct) if coverage_available else 0
    components = {
        "skills": (skill_score, 45), "cgpa": (student.cgpa * 10, 15),
        "coding": (student.coding_score, 15), "aptitude": (student.aptitude_score, 10),
        "communication": (student.communication_score, 10),
        "portfolio": (min(len(student.projects) * 30 + len(student.certifications) * 20, 100), 5),
    }
    contributions = {k: {"score": round(s, 2), "weight_percent": w, "contribution": round(s * w / 100, 2)} for k, (s, w) in components.items()}
    contributions["skills"]["available"] = coverage_available
    if not coverage_available:
        contributions["skills"]["score"] = None
    strengths = []
    if gap["matched_skills"]:
        strengths.append("Required skills present: " + ", ".join(gap["matched_skills"]))
    for label, value in [("coding", student.coding_score), ("aptitude", student.aptitude_score), ("communication", student.communication_score)]:
        if value >= 75:
            strengths.append(f"Strong self-reported {label} score ({value}/100).")
    suggestions = ["Learn " + s for s in gap["recommended_skills_to_learn"]]
    for label, value in [("coding", student.coding_score), ("aptitude", student.aptitude_score), ("communication", student.communication_score)]:
        if value < 60:
            suggestions.append(f"Practice {label}; current score is {value}/100.")
    if not student.projects:
        suggestions.append("Add a relevant project to demonstrate practical skills.")
    result = eligibility(student, job)
    return {**gap, "overall_fit_score": round(sum(s * w / 100 for s, w in components.values()), 2),
            "eligibility": result, "provisional": result["status"] == "UNVERIFIED" or not coverage_available, "strengths": strengths, "improvement_suggestions": suggestions,
            "explanation": {"components": contributions,
                "formula": "Sum of component score * weight / 100. Skills = 80% required + 20% preferred coverage; with no preferred skills, use required coverage. Configured manual jobs with no required skills retain 100% coverage. External jobs with no required skills have unavailable coverage and zero skill contribution; weights are not redistributed. CGPA = CGPA * 10. Portfolio = min(30 * projects + 20 * certifications, 100).",
                "limitations": "Hackathon heuristic, not a validated hiring model. Scores and portfolio entries are self-reported; portfolio counts do not assess quality or relevance. Eligibility is independent of fit score. No trained ML model is used."}}
