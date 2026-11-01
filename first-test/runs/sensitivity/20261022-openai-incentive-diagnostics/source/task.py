"""Hidden-profile task from Maciejovsky & Budescu (2020), Study 1, Table 2."""

APPLICANTS = ("A", "B", "C")
ATTRIBUTES = ("interpersonal skills", "personal skills", "experience", "intelligence", "motivation")

# CUES[role][applicant] = {attribute: +1 positive / -1 negative}; absent = not shown to that role.
CUES = {
    1: {
        "A": {"interpersonal skills": 1, "experience": 1, "motivation": -1},
        "B": {"interpersonal skills": 1, "intelligence": 1, "motivation": -1},
        "C": {"personal skills": -1, "experience": -1, "intelligence": 1},
    },
    2: {
        "A": {"interpersonal skills": 1, "personal skills": -1, "experience": 1},
        "B": {"personal skills": -1, "experience": 1, "intelligence": 1},
        "C": {"interpersonal skills": 1, "personal skills": -1, "motivation": -1},
    },
    3: {
        "A": {"experience": 1, "intelligence": -1, "motivation": -1},
        "B": {"interpersonal skills": 1, "personal skills": -1, "experience": 1},
        "C": {"interpersonal skills": 1, "intelligence": 1, "motivation": -1},
    },
}
ROLES = tuple(CUES)


def strength(cues):
    """2 x positives - 1 x negatives."""
    return sum(2 if v > 0 else -1 for v in cues.values())


def _pool():
    full = {a: {} for a in APPLICANTS}
    for role in ROLES:
        for a in APPLICANTS:
            for attr, v in CUES[role][a].items():
                assert full[a].setdefault(attr, v) == v, f"roles disagree on {a} {attr}"
    return full


FULL_PROFILE = _pool()
SCORES = {a: strength(FULL_PROFILE[a]) for a in APPLICANTS}
BEST = max(SCORES, key=SCORES.get)


def information(role):
    """Text for the {information} placeholder: only this role's cues."""
    lines = []
    for a in APPLICANTS:
        cues = CUES[role][a]
        parts = [f"{attr}: {'positive' if cues[attr] > 0 else 'negative'}" for attr in ATTRIBUTES if attr in cues]
        lines.append(f"Applicant {a}: " + "; ".join(parts))
    return "\n".join(lines)


def is_ranking(ranking):
    return sorted(ranking) == sorted(APPLICANTS)


def correct(ranking):
    """Primary outcome per agent: best applicant ranked first."""
    assert is_ranking(ranking), ranking
    return ranking[0] == BEST
