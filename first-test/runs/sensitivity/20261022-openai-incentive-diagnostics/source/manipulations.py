"""Conflict-of-interest manipulations of Study 1 (experiment 2 in APPROACH.md): who is paid, for what, how much."""

MANIPULATIONS = ("control", "weak-buy", "weak-sell", "strong-buy", "strong-sell")
DISCUSSION_SIDE_GBP = 5  # the paper's amount; runner.py --side-gbp overrides it for experiment 3
MARKET_SIDE_GBP_PER_SHARE = 2.5

# Paid role -> target applicant.
TARGETS = {
    "control": {},
    "weak-buy": {1: "A"},
    "weak-sell": {1: "A"},
    "strong-buy": {1: "A", 2: "A", 3: "C"},
    "strong-sell": {1: "A", 2: "A", 3: "C"},
}


def target(manipulation, role):
    return TARGETS[manipulation].get(role)


def key(institution, manipulation, role):
    """Suffix of this role's `payment_*`, `rule_*`, and `quiz_pay_*` sections in instructions.md, or None if unpaid."""
    t = target(manipulation, role)
    if t is None:
        return None
    strength, direction = manipulation.split("-")
    if institution == "market":
        return f"market_{direction}_{t}"
    group = "role1" if strength == "weak" else ("role12" if role in (1, 2) else "role3")
    return f"discussion_{strength}_{direction}_{group}"


def pay_values():
    """Placeholder values for the discussion `rule_*` and `quiz_pay_*` sections; the £4 group bonus is fixed."""
    return {"side": DISCUSSION_SIDE_GBP, "total": DISCUSSION_SIDE_GBP + 4}


def discussion_side_payment(manipulation, role, firsts):
    """£ side payment from the three final first choices (paper, Study 1 method section)."""
    t = target(manipulation, role)
    if t is None:
        return 0
    n = firsts.count(t)
    strength, direction = manipulation.split("-")
    unanimous_rule = strength == "strong" and t == "A"  # roles 1 and 2 in the strong conditions need all three
    if direction == "buy":
        ok = n == 3 if unanimous_rule else n >= 2
    else:
        ok = n == 0 if unanimous_rule else (3 - n) >= 2
    return DISCUSSION_SIDE_GBP if ok else 0


def market_side_payment(manipulation, role, paid_period_trades):
    """£2.50 per share of the target bought (buy) or sold (sell) in the paid period. Trades are (applicant, price, buyer, seller)."""
    t = target(manipulation, role)
    if t is None:
        return 0
    side = 2 if manipulation.endswith("buy") else 3
    return MARKET_SIDE_GBP_PER_SHARE * sum(1 for tr in paid_period_trades if tr[0] == t and tr[side] == role)
