"""Persona cards: a short profile per agent, drawn independently from a configurable population distribution.

Kit file of the synthetic-organisations plugin (challenge module C1: within-condition homogeneity). Draw personas from
their own stream (group.stream("personas")) so that switching them on leaves every other random draw unchanged.
Replace DEMOGRAPHICS with the target population of the study when demographic grounding matters; personality uses the
five BFI-2 domains (Soto & John 2017) at low, average or high levels.
"""

DEMOGRAPHICS = {
    "female_share": 0.50,
    "age_mean": 35.0,
    "age_sd": 10.0,
    "age_range": (18, 70),
    "roles_or_backgrounds": [
        ("have a background in operations and practical execution", 0.34),
        ("have a background in quantitative analysis and finance", 0.33),
        ("have a background in strategy and general management", 0.33),
    ],
}
TRAITS = {  # domain -> (low, high) description; average levels are omitted from the text
    "extraversion": ("quiet and reserved, and you prefer to keep to yourself",
                     "outgoing and talkative, and you like to get involved"),
    "agreeableness": ("sceptical of other people, blunt, and you do not easily go along with others",
                      "trusting and considerate, and you like to cooperate"),
    "conscientiousness": ("easily distracted and not very careful or organised",
                          "organised, thorough and careful"),
    "negative_emotionality": ("calm, emotionally stable and sure of yourself",
                              "easily worried or stressed, and often unsure of yourself"),
    "open_mindedness": ("practical, and you prefer familiar approaches over abstract ideas",
                        "curious, and you enjoy exploring unfamiliar ideas"),
}
LEVELS = ("low", "average", "high")


def draw(rng, demographics=DEMOGRAPHICS, extra_traits=None):
    """Draw one persona dict from rng using the given demographics and optional extra_traits dict."""
    lo, hi = demographics["age_range"]
    age = lo - 1
    while not lo <= age <= hi:
        age = round(rng.gauss(demographics["age_mean"], demographics["age_sd"]))
    bgs = demographics["roles_or_backgrounds"]
    bg = rng.choices([b for b, _ in bgs], weights=[w for _, w in bgs])[0]
    traits = {**TRAITS, **(extra_traits or {})}
    return {
        "age": age,
        "gender": "woman" if rng.random() < demographics["female_share"] else "man",
        "background": bg,
        **{t: rng.choice(LEVELS) for t in traits},
    }


def describe(p, extra_traits=None):
    """Render the persona in plain second-person text for the agent's system or opening instructions."""
    parts = [f"You are a {p['age']}-year-old {p['gender']}. You {p['background']}."]
    for t, (low, high) in {**TRAITS, **(extra_traits or {})}.items():
        if p.get(t, "average") != "average":
            parts.append(f"You are {low if p[t] == 'low' else high}.")
    return " ".join(parts)
