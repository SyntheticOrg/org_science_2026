"""The murder mysteries of Bernstein, Shore & Jang (2023), Appendix B, with randomised surface names.

Clue texts follow Appendix B.3 verbatim except for names, which the authors also randomised across
versions ("names and genders of suspects, murder weapons, city names, location names, event names").
Times of day are kept fixed. Placeholders: {P:role} person with title, {T:role} surname only,
{his:victim}/{him:victim} pronouns, {C:x} city, {E:x} event, {H:x} hotel, {G:x} company, {W:x} weapon.
"""

import random
import re
from dataclasses import dataclass, field

# --- pools for randomisation -----------------------------------------------------

SURNAMES = [
    "Hall", "Brown", "Lewis", "Moore", "Jones", "Davis", "Taylor", "Miller", "Clark", "Walker", "Young", "King",
    "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Hill", "Campbell", "Mitchell", "Roberts", "Carter",
    "Phillips", "Evans", "Turner", "Parker", "Collins", "Edwards", "Stewart", "Morris", "Murphy", "Cook", "Rogers",
    "Morgan", "Cooper", "Peterson", "Reed", "Bailey", "Bell", "Howard", "Ward", "Cox", "Richardson", "Wood",
    "Watson", "Brooks", "Bennett", "Gray", "Hughes", "Price", "Sanders", "Myers", "Long", "Ross", "Foster",
]
CITIES = ["Chicago", "Honolulu", "London", "Boston", "Denver", "Seattle", "Toronto", "Dublin", "Sydney", "Madrid",
          "Atlanta", "Phoenix", "Miami", "Vienna", "Lisbon", "Oslo", "Austin", "Portland", "Geneva", "Prague"]
HOTELS = ["Harbor", "Grand", "Garden", "Plaza", "Regent", "Lakeside", "Crown", "Meridian", "Beacon"]
COMPANIES = ["Panoid", "Supil", "Corvex", "Talmor", "Quenta", "Dravik", "Lumora", "Brexton", "Velcor", "Ostrin"]
EVENTS = {  # (name, search keywords)
    "fund": [("political fundraiser", ["political", "fundraiser"]), ("charity gala", ["charity", "gala"]),
             ("awards dinner", ["awards", "dinner"])],
    "launch": [("major project launch", ["major", "project", "launch"]), ("product unveiling", ["product", "unveiling"]),
               ("trade show", ["trade", "show"])],
    "conf": [("conference", ["conference"]), ("sales summit", ["sales", "summit"]),
             ("shareholder meeting", ["shareholder", "shareholders"])],
}
WEAPONS = {
    "gun": [("9-mm handgun", ["handgun", "gun", "9mm"]), (".38 revolver", ["revolver", "38"]),
            ("hunting rifle", ["hunting", "rifle"])],
    "blade": [("bolo knife", ["bolo", "knife"]), ("machete", ["machete"]), ("hatchet", ["hatchet"])],
    "rare": [("switchblade", ["switchblade"]), ("dagger", ["dagger"]), ("crowbar", ["crowbar"])],
    "poison": [("cyanide", ["cyanide"]), ("arsenic", ["arsenic"]), ("strychnine", ["strychnine"])],
}
PLAYER_NAMES = ["Avery", "Blake", "Casey", "Drew", "Emery", "Finley", "Harper", "Jamie", "Kendall", "Logan", "Micah",
                "Noel", "Peyton", "Quinn", "Reese", "Rowan", "Sage", "Skyler", "Toby", "Wren"]


# --- templates -------------------------------------------------------------------

MAIN = {
    "roles": {  # role -> fixed part in the logic
        "victim": "male",
        "brown": None,  # main red herring
        "lewis": None,  # true culprit
        "moore": None, "jones": None, "davis": None, "taylor": None, "miller": None,
    },
    "suspects": ["brown", "lewis", "moore", "jones", "davis", "taylor", "miller"],
    "culprit": "lewis",
    "red_herring": "brown",
    "cities": ["fund", "launch", "conf"],
    "hotels": ["death", "meeting", "cocktail"],
    "companies": ["meeting", "cocktail"],
    "broadcasts": {  # seconds -> messages from headquarters
        0: ["{P:victim} is missing and presumed dead. Your task is to identify the murderer. {P:victim} was scheduled "
            "to be at a {E:fund}, a {E:launch}, and a {E:conf} in the days around {his:victim} disappearance."],
        300: ["{P:victim}'s body was discovered at the {H:death} Hotel in {C:launch}, after the {E:launch}.",
              "Security camera footage shows that {P:victim} went directly to the {H:death} Hotel after the {E:launch} "
              "and never left.",
              "Initial examination indicates that the time of death was 8 pm."],
        600: ["Autopsy results show that the murder weapon was a {W:gun}."],
    },
    "clues": {  # wave -> searchable clues
        1: [
            "The {E:fund} was scheduled in {C:fund}.",
            "The {E:launch} was scheduled in {C:launch}.",
            "The {E:conf} was scheduled in {C:conf}.",
            "The {E:conf} apparently went well.",
            "Two witnesses reported that {P:victim} extorted large sums of money from {P:moore}, {P:jones}, and {P:brown}.",
            "{P:taylor} told investigators that {P:victim} cut {P:brown}, {P:davis}, and {P:taylor} out of a lucrative "
            "business deal.",
            "{P:miller} reports that {P:miller} and {P:brown} were involved in business with The {G:meeting} Group.",
            "{P:miller} reports that The {G:meeting} Group was involved in secret negotiations with {P:victim}.",
            "{P:davis} and {P:taylor} were confirmed to be in {C:conf} since before the victim went missing.",
            "{P:davis} and {P:taylor} were traveling together.",
            "{P:brown}, {P:davis}, and {P:taylor} have been having frequent private meetings recently.",
            "Anonymous sources say {P:taylor} was interested in undermining the {E:conf}.",
            "{P:miller} claims to have been in {C:fund} since before {P:victim} went missing.",
            "{P:moore} and {P:jones} were confirmed to be in {C:launch} around the time of {P:victim}'s disappearance.",
            "{P:brown} and {P:lewis} were confirmed to be in {C:launch} around the time of {P:victim}'s disappearance.",
            "{P:miller} and {P:brown} were friends.",
            "Search of {P:miller}'s home revealed that {P:miller} owned {W:poison} and a {W:blade}.",
            "Search of {P:moore}'s home revealed that {P:moore} owned a {W:rare}.",
            "Search of {P:jones}'s home revealed that {P:jones} owned a {W:blade}.",
            "Search of {P:brown}'s home revealed that {P:brown} owned a {W:blade}.",
            "Search of {P:davis}'s home revealed that {P:davis} owned a {W:blade}.",
            "Search of {P:davis}'s home revealed that {P:davis} owned a {W:gun}.",
            "Search of {P:lewis}'s home revealed that {P:lewis} owned a {W:gun}.",
            "Search of {P:brown}'s home revealed that {P:brown} owned a {W:gun}.",
            "There is no evidence that {P:taylor} owned any potential murder weapons.",
            "The victim, {P:victim}, had many enemies.",
        ],
        2: [
            "{P:jones}, {P:brown}, and {P:lewis} were present at the {E:launch}, according to a witness.",
            "{P:miller} was present at the {E:fund}.",
            "{P:taylor} did not attend the {E:conf}, according to an alibi witness.",
            "{P:davis} attended the {E:conf}.",
            "{P:moore} did not attend the {E:launch}, according to an alibi witness.",
            "The {G:meeting} Group's business meeting occurred at the {H:meeting} Hotel, which is a 35-minute drive "
            "from the {H:death} Hotel.",
            "The {G:meeting} Group's business meeting began at 6 and ended around 9 pm.",
            "{P:moore}, {P:jones}, and {P:brown} attended The {G:meeting} Group's business meeting after the {E:launch}.",
            "{P:brown} and {P:lewis} attended The {G:cocktail} Company's cocktail hour after the {E:launch}.",
            "The {G:cocktail} Company's cocktail hour began at 10 and ended around 12 pm.",
            "The {G:cocktail} Company's cocktail hour occurred at the {H:cocktail} Hotel, which is a 45-minute drive "
            "from the {H:death} Hotel.",
            "{P:brown} traveled directly between The {G:meeting} Group's business meeting and The {G:cocktail} "
            "Company's cocktail hour.",
            "{P:brown} was seen speaking to a friend at 7:50 pm at The {G:meeting} Group's business meeting.",
            "The {G:meeting} Group often hosted VIP parties.",
            "{P:lewis} was hoping to land a big contract with The {G:cocktail} Company.",
        ],
    },
}

PRACTICE = {  # stage 1 (Appendix B.1), single player, fixed names as in the paper
    "intro": "The murderer is either Mr. Smith, Mr. Lee, or Ms. White. The murder weapon was poison.",
    "suspects": ["Mr. Smith", "Mr. Lee", "Ms. White"],
    "culprit": "Mr. Lee",
    "clues": [
        ("Mr. Smith was out of town at the time of the murder.", ["smith"]),
        ("Mr. Smith was very sad to learn about the murder.", ["smith"]),
        ("Ms. White was with Mr. Smith at the time of the murder.", ["white", "smith"]),
        ("Ms. White grew up in California.", ["white", "california"]),
        ("Mr. Lee's fingerprints were found at the scene of the crime.", ["lee"]),
        ("Mr. Lee had poison at his house that matched the poison used in the murder.", ["lee", "poison"]),
    ],
}


# --- instantiation ---------------------------------------------------------------

@dataclass
class Clue:
    id: str
    text: str
    wave: int  # searchable from the start of this phase
    keywords: frozenset


@dataclass
class Mystery:
    victim: str
    suspects: list  # answer options, display names
    culprit: str
    red_herring: str | None
    clues: list
    broadcasts: dict  # seconds -> [text]
    wave_starts: dict = field(default_factory=lambda: {1: 0})
    names: dict = field(default_factory=dict)  # role -> display name, for the record

    def category(self, answer):
        """The authors' coding: correct, RH (main red herring), OA (other answer), none."""
        if answer is None:
            return "none"
        if answer == self.culprit:
            return "correct"
        return "RH" if answer == self.red_herring else "OA"

    def wave_at(self, seconds):
        return max(w for w, s in self.wave_starts.items() if s <= seconds)


def _words(text):
    return [w.lower() for w in re.findall(r"[A-Za-z0-9]+", text)]


def make_main(rng):
    """One randomised version of the main-trial mystery, with shuffled clue ids."""
    t = MAIN
    surnames = rng.sample(SURNAMES, len(t["roles"]))
    persons, pronoun, kw = {}, {}, {}
    for (role, fixed), name in zip(t["roles"].items(), surnames):
        sex = fixed or rng.choice(["male", "female"])
        persons[role] = ("Mr. " if sex == "male" else "Ms. ") + name
        pronoun[role] = ("his", "him") if sex == "male" else ("her", "her")
        kw[f"P:{role}"] = kw[f"T:{role}"] = [name.lower()]
    cities = dict(zip(t["cities"], rng.sample(CITIES, 3)))
    hotels = dict(zip(t["hotels"], rng.sample(HOTELS, 3)))
    companies = dict(zip(t["companies"], rng.sample(COMPANIES, 2)))
    events = {k: rng.choice(v) for k, v in EVENTS.items()}
    weapons = {k: rng.choice(v) for k, v in WEAPONS.items()}
    values = {}
    for role in persons:
        values[f"P:{role}"], values[f"T:{role}"] = persons[role], persons[role].split(" ", 1)[1]
        values[f"his:{role}"], values[f"him:{role}"] = pronoun[role]
    for k, v in cities.items():
        values[f"C:{k}"], kw[f"C:{k}"] = v, [v.lower()]
    for k, v in hotels.items():
        values[f"H:{k}"], kw[f"H:{k}"] = v, [v.lower()]
    for k, v in companies.items():
        values[f"G:{k}"], kw[f"G:{k}"] = v, [v.lower()]
    for k, (name, words) in events.items():
        values[f"E:{k}"], kw[f"E:{k}"] = name, words
    for k, (name, words) in weapons.items():
        values[f"W:{k}"], kw[f"W:{k}"] = name, words

    def render(template):
        return re.sub(r"\{([^}]+)\}", lambda m: values[m.group(1)], template)

    def keywords(template):
        return frozenset(w for key in re.findall(r"\{([^}]+)\}", template) for w in kw.get(key, []))

    raw = [(render(c), wave, keywords(c)) for wave, cs in t["clues"].items() for c in cs]
    ids = rng.sample(range(1, len(raw) + 1), len(raw))
    clues = sorted((Clue(f"C{i}", text, wave, k) for i, (text, wave, k) in zip(ids, raw)), key=lambda c: int(c.id[1:]))
    return Mystery(
        victim=persons["victim"],
        suspects=[persons[r] for r in t["suspects"]],
        culprit=persons[t["culprit"]],
        red_herring=persons[t["red_herring"]],
        clues=clues,
        broadcasts={s: [render(m) for m in ms] for s, ms in t["broadcasts"].items()},
        wave_starts={1: 0, 2: 300},
        names={**{r: p for r, p in persons.items()}, **{f"city_{k}": v for k, v in cities.items()},
               **{f"hotel_{k}": v for k, v in hotels.items()}, **{f"company_{k}": v for k, v in companies.items()},
               **{f"event_{k}": v[0] for k, v in events.items()}, **{f"weapon_{k}": v[0] for k, v in weapons.items()}},
    )


def make_practice(rng):
    p = PRACTICE
    ids = rng.sample(range(1, len(p["clues"]) + 1), len(p["clues"]))
    clues = sorted((Clue(f"C{i}", text, 1, frozenset(k)) for i, (text, k) in zip(ids, p["clues"])), key=lambda c: int(c.id[1:]))
    return Mystery(victim=None, suspects=list(p["suspects"]), culprit=p["culprit"], red_herring=None, clues=clues,
                   broadcasts={0: [p["intro"]]})


def search(mystery, query, seconds, already, rng):
    """The platform's search (oceler SearchController): try each word of the query in turn until one matches a
    keyword; return one random matching clue that is unlocked and not in `already`. With the platform's
    unique_factoids setting on, `already` holds the clues this player has found by search; with it off (repeat
    search), pass an empty set and a search can return a clue the player has seen before."""
    wave = mystery.wave_at(seconds)
    for word in _words(query):
        hits = [c for c in mystery.clues if word in c.keywords and c.wave <= wave and c.id not in already]
        if hits:
            return rng.choice(hits)
    return None
