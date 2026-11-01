"""Persona cards: a short profile per agent, drawn independently from the population the human sample came from.

Demographics follow the MTurk sample of Levay, Freese & Druckman (2016, SAGE Open, Table 1 and appendix Table 1),
which Bernstein, Shore & Jang cite for their participants: mean age 31.6 (the paper gives no spread; we assume a
standard deviation of 10, truncated to 18-70), 53.9% male, 22.3% students, and the education distribution below.
Personality uses the Big Five domains as in the BFI-2 (Soto & John 2017): each domain is low, average or high
relative to the population, one third each, drawn independently (real traits correlate somewhat; ignored here).
Politics and income are left out because they have no bearing on the task.

Optional sixth trait, susceptibility to interpersonal influence (Bearden, Netemeyer & Teel 1989): how easily the
person is swayed by what others think, low, average or high with one third each. It is drawn from its own random
stream, so switching it on leaves every other attribute of every persona unchanged.
"""

import random

MALE = 0.539
STUDENT = 0.223
AGE_MEAN, AGE_SD, AGE_RANGE = 31.6, 10, (18, 70)
EDUCATION = [  # (description, share)
    ("did not finish high school", 0.013),
    ("finished high school", 0.100),
    ("have some college or vocational training but no degree", 0.438),
    ("have a bachelor's degree", 0.358),
    ("have a graduate degree", 0.091),
]
TRAITS = {  # domain -> (low, high) description; average levels are not described
    "extraversion": ("quiet and reserved, and you prefer to keep to yourself",
                     "outgoing and talkative, and you like to get involved"),
    "agreeableness": ("sceptical of other people, blunt, and you do not easily go along with others",
                      "trusting and considerate, and you like to cooperate"),
    "conscientiousness": ("easily distracted and not very careful or organised",
                          "organised, thorough and careful"),
    "negative_emotionality": ("calm, emotionally stable and sure of yourself",
                              "easily worried or stressed, and often unsure of yourself"),
    "open_mindedness": ("practical, and you are not much interested in puzzles or abstract ideas",
                        "curious, and you enjoy puzzles and thinking about ideas"),
}
SUSCEPTIBILITY = ("confident in your own judgment, and you rarely change your mind because of what other people think",
                  "easily swayed by what other people think, and you often go along with them")
LEVELS = ("low", "average", "high")


def draw(rng, susceptibility_rng=None):
    """One persona as a dict of attributes; susceptibility_rng, if given, adds the susceptibility trait."""
    age = AGE_RANGE[0] - 1
    while not AGE_RANGE[0] <= age <= AGE_RANGE[1]:
        age = round(rng.gauss(AGE_MEAN, AGE_SD))
    edu = rng.choices([e for e, _ in EDUCATION], weights=[w for _, w in EDUCATION])[0]
    p = {
        "age": age,
        "gender": "man" if rng.random() < MALE else "woman",
        "education": edu,
        "student": rng.random() < STUDENT,
        **{t: rng.choice(LEVELS) for t in TRAITS},
    }
    if susceptibility_rng:
        p["susceptibility"] = susceptibility_rng.choice(LEVELS)
    return p


def describe(p):
    """The persona in plain second-person text, for the agent's instructions."""
    parts = [f"You are a {p['age']}-year-old {p['gender']}. You {p['education']}"
             + (", and you are currently a student." if p["student"] else ".")]
    for t, (low, high) in {**TRAITS, "susceptibility": SUSCEPTIBILITY}.items():
        if p.get(t, "average") != "average":
            parts.append(f"You are {low if p[t] == 'low' else high}.")
    return " ".join(parts)
