import json
import re
from pathlib import Path

SKILL_DICTIONARY = json.loads(Path(__file__).with_name("skill_dictionary.json").read_text(encoding="utf-8"))
ALIASES = {alias.casefold(): name for name, aliases in SKILL_DICTIONARY.items() for alias in [name, *aliases]}


def clean_skill_names(skills):
    """Canonicalize known aliases; preserve arbitrary custom skills and their casing."""
    result, seen = [], set()
    for value in skills:
        value = " ".join(value.split())
        canonical = ALIASES.get(value.casefold(), value)
        if canonical and canonical.casefold() not in seen:
            seen.add(canonical.casefold())
            result.append(canonical)
    return result


def normalize_skills(skills):
    """Normalize known aliases and compare unknown skills case-insensitively."""
    return sorted({ALIASES.get(s.casefold(), s.casefold()) for s in clean_skill_names(skills)}, key=str.casefold)


def extract_skills(text):
    found = []
    for name, aliases in SKILL_DICTIONARY.items():
        if any(re.search(r"(?<![\w+#])" + re.escape(alias) + r"(?![\w+#])", text, re.I) for alias in aliases):
            found.append(name)
    return sorted(found, key=str.casefold)
