"""The manager-agent game: payoffs, the nine fixed game sequences, payoff tables as text, and outcome measures."""

ROUNDS, BLOCK = 18, 9
GAMES = ACTIONS = range(1, 6)

# Games in rounds 1 to 18 by group position, as written in the z-Tree programs and played in all 40 sessions.
SEQUENCES = {pos: [int(x) for x in s.split()] for pos, s in {
    1: "4 2 5 3 5 1 5 2 2 4 2 3 1 5 3 1 1 2",
    2: "3 1 5 3 4 3 1 5 5 5 3 3 3 2 1 1 1 4",
    3: "3 4 1 4 4 5 1 4 3 3 4 4 2 2 4 4 3 3",
    4: "2 2 4 4 1 5 4 2 5 4 3 1 1 2 1 4 2 2",
    5: "3 5 1 2 2 3 5 4 3 2 3 1 2 3 5 2 5 5",
    6: "2 2 3 5 1 3 4 4 5 1 2 3 4 5 2 4 1 3",
    7: "4 5 2 3 2 3 1 4 5 1 5 5 3 5 1 4 2 2",
    8: "3 3 5 2 4 1 2 3 1 5 4 3 2 3 1 5 3 3",
    9: "1 4 4 5 1 2 3 3 4 5 2 3 1 5 4 2 2 3",
}.items()}


def position(group):
    """Groups 1, 10, 19 play sequence 1; groups 2, 11, 20 play sequence 2; and so on."""
    return (group - 1) % 9 + 1


def payoffs(game, row, col):
    """(F, C, A) in ECU for row f`row` and column c`col` of game `game`."""
    f = 54 - 14 * abs(row - col) - 7 * abs(row - 5) - 4 * abs(row - game)
    c = 54 - 14 * abs(row - col) - 7 * abs(col - 1) - 4 * abs(col - game)
    return f, c, f + c


def safe_surplus(game):
    return 80 - 8 * abs(game - 3)


def outcome(game, row, col):
    """'efficient', 'safe', 'other' (coordinated elsewhere) or 'failure'. In game 3 safe and efficient coincide;
    this returns 'efficient' there, and Table 3 leaves game 3 out."""
    if row != col:
        return "failure"
    return "efficient" if row == game else "safe" if row == 3 else "other"


def efficiency_gain(rounds):
    """One group's efficiency gain over (game, total surplus) pairs: 0 is the safe outcome, 1 efficient play."""
    safe = sum(safe_surplus(g) for g, _ in rounds)
    return (sum(s for _, s in rounds) - safe) / (80 * len(rounds) - safe)


def tables_text():
    """The five payoff tables as monospace text; each cell 'F, C, A'."""
    out = []
    for g in GAMES:
        lines = [f"Game {g}", "      " + "".join(f"c{c:<14}" for c in ACTIONS).rstrip()]
        for r in ACTIONS:
            lines.append(f"f{r}    " + "".join(f"{'%d, %d, %d' % payoffs(g, r, c):<15}" for c in ACTIONS).rstrip())
        out.append("\n".join(lines))
    return "```\n" + "\n\n".join(out) + "\n```"
