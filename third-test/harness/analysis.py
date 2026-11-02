"""Analysis: Tables 2, 3, 5, 6 (message counts), 7 and 9 and the replication tests, agents beside humans.

Usage (from third-test/; every run with chat must be coded first with code_chat.py):
    uv run --no-project --with pandas --with scipy python harness/analysis.py runs/<exp1> [runs/<exp2>] > results/<name>.md

Human values are recomputed from the replication package with the authors' rules (APPROACH.md, Outcomes and
analysis) and shown next to the printed ones. The unit is the group; the main window is rounds 10 to 18.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

import game
from runner import TREATMENTS
from test_core import PKG, TABLE2

MAIN = TREATMENTS[:7]
REPORTERS = ("SC-MC", "CH-MC", "EC-MC")
SEED, DRAWS = 20261026, 10_000

# Printed values (APPROACH.md, Human benchmarks).
PRINTED = {
    "table2": {t: TABLE2[i] for i, t in enumerate(MAIN, 1)} | {"EC-MC": (96.7, 55.7, 71.3, -4.9)},
    "table3": dict(zip(MAIN, [(48.1, 12.6, 4.9), (36.1, 30.6, 8.2), (32.8, 30.1, 4.4), (31.1, 36.1, 32.2),
                              (41.0, 36.1, 20.8), (29.5, 44.8, 15.8), (34.4, 50.8, 14.8)])),
    "table7": {"SC-MC": [(24.9, 75.1), (36.4, 63.6), (68.0, 32.0), (73.3, 26.7), (87.6, 12.4)],
               "CH-MC": [(46.6, 2.5), (42.8, 3.1), (43.0, 2.2), (50.1, 1.9), (47.1, 0.3)]},
    "table9": {"SC-MC": (30.9, 41.6), "EC-MC": (49.8, 28.6), "CH-MC": (77.4, 1.0)},
    "messages": {"CH/S-D": (None, 4.45), "CH/A-D": (3.33, 3.72), "CH-MC": (4.56, 5.30), "EC-MC": (3.1, 7.4)},
    "safe": {"SC-MC": .444, "CH/S-D": .111, "CH/A-D": .105, "CH-MC": "<.001", "EC-MC": .356},
    "ranksum": {("CH-MC", "SC-MC"): .003, ("CH-MC", "CH/S-D"): .014, ("CH-MC", "CH/A-D"): .162},
}


# --- data ------------------------------------------------------------------------

def agent_data(dirs):
    """Group-rounds, agent-rounds (F and C, reporting treatments) and chat counts from complete groups."""
    rounds, reports, chats, info = [], [], [], Counter()
    for d in dirs:
        coding = json.loads((d / "coding.json").read_text())["rounds"] if (d / "coding.json").exists() else {}
        for p in sorted(d.glob("*-[0-9][0-9].json")):
            rec = json.loads(p.read_text())
            t = rec["treatment"]
            info[(t, rec["status"])] += 1
            info[(t, "invalid replies")] += sum(len(a["failures"]) for a in rec["agents"].values())
            if rec["status"] != "complete":
                continue
            gid = f"{d.name}/{rec['group']}"
            for x in rec["rounds"]:
                g = x["game"]
                r = dict(source="agents", treatment=t, group=gid, round=x["round"], game=g, row=x["row"], col=x["column"],
                         surplus=x["payoffs"]["A"])
                if "chat" in x:
                    c = coding[f"{t}|{rec['group']}|{x['round']}"]  # KeyError: run code_chat.py first
                    said = [m for m in x["chat"] if m["message"]]
                    chats.append(dict(treatment=t, group=gid, round=x["round"], ended=x["chat_ended"],
                                      A=sum(m["speaker"] == "A" for m in said), agents=sum(m["speaker"] != "A" for m in said),
                                      agents_distinct=len({(m["speaker"], m["message"]) for m in said if m["speaker"] != "A"})))
                    claims = {s: [cl["game"] for cl in sorted(c["claims"], key=lambda cl: cl["index"]) if cl["speaker"] == s] for s in "FC"}
                    if t == "EC-MC":  # the last game report counts
                        truth = {s: float(bool(v) and v[-1] == g) for s, v in claims.items()}
                        lie = {s: float(bool(v) and v[-1] != g) for s, v in claims.items()}
                    else:  # ever told the truth, ever lied
                        truth = {s: float(g in v) for s, v in claims.items()}
                        lie = {s: float(any(c != g for c in v)) for s, v in claims.items()}
                elif t == "SC-MC":
                    r.update(rep_F=x["reports"]["F"], rep_C=x["reports"]["C"])
                    truth = {s: float(x["reports"][s] == g) for s in "FC"}
                    lie = {s: 1 - truth[s] for s in "FC"}
                else:
                    truth = lie = None
                if truth is not None:
                    r["revealed"] = revealed(t, truth, lie)
                    reports += [dict(source="agents", treatment=t, group=gid, round=x["round"], game=g, agent=s,
                                     truth=truth[s], lie=lie[s]) for s in "FC"]
                rounds.append(r)
    return pd.DataFrame(rounds), pd.DataFrame(reports), pd.DataFrame(chats), info


def revealed(t, truth, lie):
    """SC-MC: both reports true. EC-MC: a true last report and no false one. Chat: someone truthful, no contradiction."""
    if t == "SC-MC":
        return float(truth["F"] and truth["C"])
    if t == "EC-MC":
        return float((truth["F"] or truth["C"]) and not (lie["F"] or lie["C"]))
    contradict = (truth["F"] and lie["C"]) or (truth["C"] and lie["F"])
    return float((truth["F"] or truth["C"]) and not contradict)


def human_data():
    read = lambda f: pd.read_stata(PKG / f, convert_categoricals=False)
    m, follow, coding = read("BC Master Data, Main Experiment.dta"), read("BC Master Data, Follow Up Experiment.dta"), read("BC Coding Data, Main Experiment.dta")
    m = m[(m.type == 0) & (m.true_treatment_ordered <= 7)].copy()
    m["treatment"] = [MAIN[int(t) - 1] for t in m.true_treatment_ordered]
    m["group"] = [f"{s}/{g}" for s, g in zip(m.session, m.group)]
    rounds = m.rename(columns={"period": "round", "strategy1": "row", "strategy2": "col", "payoff_manager": "surplus"})
    rounds = rounds[["treatment", "group", "round", "game", "row", "col", "surplus", "message1", "message2"]].copy()
    sc = rounds.treatment == "SC-MC"
    rounds.loc[sc, "rep_F"], rounds.loc[sc, "rep_C"] = rounds.loc[sc, "message1"], rounds.loc[sc, "message2"]
    rounds.loc[sc, "revealed"] = ((rounds.message1 == rounds.game) & (rounds.message2 == rounds.game))[sc].astype(float)
    reports = [rounds[sc].assign(agent=s, truth=(rounds[sc][f"message{i}"] == rounds[sc].game).astype(float))
               for i, s in ((1, "F"), (2, "C"))]
    for r in reports:
        r["lie"] = 1 - r.truth

    # CH-MC chat codes: fractional coder means; the coding file mislabels its treatment dummies, so use the number.
    c = coding[coding.true_treatment_ordered == 7].copy()
    c["group"] = [f"{int(s)}/{int(g)}" for s, g in zip(c.session, c.group)]
    c["round"] = c.period.astype(int)
    c["revealed"] = ((c.truthful > 0) & (c.contradict == 0)).astype(float)
    ch = rounds.treatment == "CH-MC"
    rounds.loc[ch, "revealed"] = rounds[ch].drop(columns="revealed").merge(c[["group", "round", "revealed"]], on=["group", "round"], how="left")["revealed"].values
    base = c[["group", "round", "game"]].assign(treatment="CH-MC")
    reports += [base.assign(agent=s, truth=c[f"truth_a{i}"].values, lie=c[f"false_a{i}"].values) for i, s in ((1, "F"), (2, "C"))]

    # EC-MC: message-level data; the last game report of each agent-round counts.
    follow["group"] = [f"EC{s}/{g}" for s, g in zip(follow.session, follow.group)]
    e = follow.drop_duplicates(["group", "period"]).rename(columns={"period": "round", "strategy1": "row", "strategy2": "col", "payoff_manager": "surplus"})
    e = e[["group", "round", "game", "row", "col", "surplus"]].assign(treatment="EC-MC")
    msg = follow[(follow.messagecode >= 11) & (follow.messagecode <= 15) & (follow.type > 0)].sort_values("obn")
    last = msg.groupby(["group", "period", "type"]).messagecode.last() - 10
    ec = []
    for (grp, rnd, g) in zip(e.group, e["round"], e.game):
        rep = {s: last.get((grp, rnd, i)) for i, s in ((1, "F"), (2, "C"))}
        truth = {s: float(v == g) for s, v in rep.items()}
        lie = {s: float(v is not None and v != g) for s, v in rep.items()}
        ec.append(revealed("EC-MC", truth, lie))
        reports.append(pd.DataFrame([dict(treatment="EC-MC", group=grp, round=rnd, game=g, agent=s, truth=truth[s], lie=lie[s]) for s in "FC"]))
    e["revealed"] = ec
    rounds = pd.concat([rounds.drop(columns=["message1", "message2"]), e], ignore_index=True).assign(source="humans")
    reports = pd.concat(reports, ignore_index=True)[["treatment", "group", "round", "game", "agent", "truth", "lie"]].assign(source="humans")

    counts = coding.assign(treatment=[MAIN[int(t) - 1] for t in coding.true_treatment_ordered],
                           group=[f"{int(s)}/{int(g)}" for s, g in zip(coding.session, coding.group)], round=coding.period.astype(int))
    chats = counts.rename(columns={"nummess_man": "A", "nummess_agent": "agents"})[["treatment", "group", "round", "A", "agents"]]
    sent = follow[follow.messagecode != -999].groupby(["group", "period", "type"]).size().unstack(fill_value=0)
    sent = sent.reindex(pd.MultiIndex.from_frame(e[["group", "round"]]), fill_value=0)
    chats = pd.concat([chats, pd.DataFrame(dict(treatment="EC-MC", group=e.group.values, round=e["round"].values,
                                                A=sent.get(0, 0).values, agents=(sent.get(1, 0) + sent.get(2, 0)).values))], ignore_index=True)
    return rounds, reports, chats


# --- measures --------------------------------------------------------------------

def window(df, w):
    return df[df["round"] >= 10] if w == "10-18" else df[df["round"] <= 9] if w == "1-9" else df


def gains(df):
    """Efficiency gain per group: 0 is the safe outcome, 1 efficient play."""
    return df.groupby("group").apply(lambda x: game.efficiency_gain(list(zip(x.game, x.surplus))), include_groups=False)


def safe_diff(df):
    """Per group: mean surplus minus mean safe surplus for the same draws."""
    return df.assign(d=df.surplus - (80 - 8 * (df.game - 3).abs())).groupby("group").d.mean()


def table2_row(df):
    coord = df.row == df.col
    eff = coord & (df.row == df.game)
    return (100 * coord.mean(), 100 * eff.sum() / coord.sum() if coord.any() else np.nan, df.surplus.mean(), 100 * gains(df).mean())


def table3_row(df):
    d = df[df.game != 3]
    coord = d.row == d.col
    safe, eff = coord & (d.row == 3), coord & (d.row == d.game)
    return tuple(100 * v.mean() for v in (safe, eff, coord & ~safe & ~eff))


def manager_mistake(df):
    """p. 1973: no coordination, or coordination outside the interval between 3 and the true game."""
    coord = df.row == df.col
    lo, hi = np.minimum(df.game, 3), np.maximum(df.game, 3)
    return (~coord | (df.row > hi) | (df.row < lo)).mean()


def table7(rep, t):
    """By remapped game (C's games mirrored, 6 - game): SC-MC pooled; otherwise the mean of the two role means."""
    d = rep[rep.treatment == t].assign(mapgame=lambda x: np.where(x.agent == "F", x.game, 6 - x.game))
    if t == "SC-MC":
        by = d.groupby("mapgame")[["truth", "lie"]].mean()
    else:
        by = d.groupby(["agent", "mapgame"])[["truth", "lie"]].mean().groupby("mapgame").mean()
    return 100 * by


# --- tests -----------------------------------------------------------------------

def signrank_p(d):
    """Exact two-sided signed-rank p; zeros are ranked and carry no sign (Pratt), as in the authors' Stata output."""
    d = np.round(np.asarray(d, float), 9)
    r = (2 * rankdata(np.abs(d))).astype(int)
    nz = r[d != 0]
    obs, mean = r[d > 0].sum(), nz.sum() / 2
    dist = np.zeros(nz.sum() + 1)
    dist[0] = 1
    for ri in nz:
        dist[ri:] = dist[ri:] + dist[:-ri].copy()
    s = np.arange(len(dist))
    return min(1.0, dist[np.abs(s - mean) >= abs(obs - mean) - 1e-9].sum() / dist.sum())


def ranksum_p(x, y):
    """Exact two-sided rank-sum p over all splits of the pooled ranks (ties take mid-ranks)."""
    x, y = np.round(np.asarray(x, float), 9), np.round(np.asarray(y, float), 9)
    r = (2 * rankdata(np.concatenate([x, y]))).astype(int)
    n1 = len(x)
    dist = np.zeros((n1 + 1, r.sum() + 1))
    dist[0, 0] = 1
    for ri in r:
        dist[1:, ri:] = dist[1:, ri:] + dist[:-1, :-ri].copy()
    dist = dist[n1]
    obs, mean = r[:n1].sum(), n1 * r.sum() / (len(r))
    s = np.arange(len(dist))
    return min(1.0, dist[np.abs(s - mean) >= abs(obs - mean) - 1e-9].sum() / dist.sum())


def perm_boot_one(d, rng):
    """Mean of d: sign-flip permutation p (two-sided) and bootstrap 95% CI over groups."""
    d = np.asarray(d, float)
    flips = rng.choice([-1, 1], size=(DRAWS, len(d))) @ d / len(d)
    boot = rng.choice(d, size=(DRAWS, len(d))).mean(axis=1)
    return d.mean(), (np.abs(flips) >= abs(d.mean()) - 1e-12).mean(), np.percentile(boot, [2.5, 97.5])


def perm_boot_two(x, y, rng):
    """Difference in means x - y: label permutation p (two-sided) and bootstrap 95% CI resampling groups within arms."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    pooled, obs = np.concatenate([x, y]), x.mean() - y.mean()
    perm = np.array([(lambda p: p[:len(x)].mean() - p[len(x):].mean())(rng.permutation(pooled)) for _ in range(DRAWS)])
    boot = rng.choice(x, size=(DRAWS, len(x))).mean(axis=1) - rng.choice(y, size=(DRAWS, len(y))).mean(axis=1)
    return obs, (np.abs(perm) >= abs(obs) - 1e-12).mean(), np.percentile(boot, [2.5, 97.5])


def slope(d):
    """Least-squares slope of lie (percentage points) on remapped game."""
    return 100 * np.polyfit(d.mapgame, d.lie, 1)[0] if d.mapgame.nunique() > 1 else np.nan


def r4(rep, rng):
    """Gradient of lying in the remapped game, SC-MC minus CH-MC, all 18 rounds; groups are resampled and permuted."""
    d = rep[rep.treatment.isin(["SC-MC", "CH-MC"])].assign(mapgame=lambda x: np.where(x.agent == "F", x.game, 6 - x.game))
    by = {t: [g for _, g in d[d.treatment == t].groupby("group")] for t in ("SC-MC", "CH-MC")}
    stat = lambda a, b: slope(pd.concat(a)) - slope(pd.concat(b))
    obs = stat(by["SC-MC"], by["CH-MC"])
    pick = lambda gs: [gs[i] for i in rng.integers(len(gs), size=len(gs))]
    boot = [stat(pick(by["SC-MC"]), pick(by["CH-MC"])) for _ in range(DRAWS // 10)]
    pooled, n = by["SC-MC"] + by["CH-MC"], len(by["SC-MC"])
    perm = []
    for _ in range(DRAWS // 10):
        idx = rng.permutation(len(pooled))
        perm.append(stat([pooled[i] for i in idx[:n]], [pooled[i] for i in idx[n:]]))
    return slope(pd.concat(by["SC-MC"])), slope(pd.concat(by["CH-MC"])), obs, (np.abs(perm) >= abs(obs) - 1e-12).mean(), np.nanpercentile(boot, [2.5, 97.5])


# --- report ----------------------------------------------------------------------

def fmt(v, digits=1):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    return v if isinstance(v, str) else f"{v:.{digits}f}"


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return "\n".join(out + ["| " + " | ".join(fmt(c) if not isinstance(c, str) else c for c in r) + " |" for r in rows])


def report(dirs):
    a_rounds, a_rep, a_chat, info = agent_data(dirs)
    h_rounds, h_rep, h_chat = human_data()
    treatments = [t for t in TREATMENTS if t in set(a_rounds.treatment)]
    out = [f"# Results: {', '.join(str(d) for d in dirs)}", ""]
    configs = [json.loads((d / "config.json").read_text()) for d in dirs]
    out.append("Settings: " + "; ".join(f"{d.name}: {c['model']}, effort {c['reasoning_effort']}, {c['turns']} turns, notes {c['notes']}"
                                        for d, c in zip(dirs, configs)))
    out.append("")
    out.append(table(["Treatment", "complete groups", "incomplete", "invalid replies (re-asked)"],
                     [(t, str(info[(t, 'complete')]), str(info[(t, 'incomplete')]), str(info[(t, 'invalid replies')])) for t in treatments]))

    for w in ("10-18", "1-9", "all"):
        out += ["", f"## Table 2, rounds {w}: agents / humans recomputed (printed)", ""]
        rows = []
        for t in treatments:
            a = table2_row(window(a_rounds[a_rounds.treatment == t], w))
            h = table2_row(window(h_rounds[h_rounds.treatment == t], w))
            p = PRINTED["table2"].get(t) if w == "10-18" else None
            rows.append([t] + [f"{fmt(x)} / {fmt(y)}" + (f" ({fmt(z)})" if p else "") for x, y, z in zip(a, h, p or (None,) * 4)])
        out.append(table(["Treatment", "coordinated %", "efficient if coordinated %", "surplus", "efficiency gain %"], rows))

    out += ["", "## Table 3, rounds 10-18, games other than 3: agents / humans recomputed (printed)", ""]
    rows = []
    for t in [t for t in treatments if t in PRINTED["table3"]]:
        a, h = table3_row(window(a_rounds[a_rounds.treatment == t], "10-18")), table3_row(window(h_rounds[h_rounds.treatment == t], "10-18"))
        rows.append([t] + [f"{fmt(x)} / {fmt(y)} ({fmt(z)})" for x, y, z in zip(a, h, PRINTED["table3"][t])])
    out.append(table(["Treatment", "safe %", "efficient %", "other coordinated %"], rows))

    if "SC-MC" in treatments:
        out += ["", "## Table 5, SC-MC, all rounds: A's row when A coordinated, by F's report (rows) and C's report (columns); cells with 5 or fewer blank", ""]
        for name, df in (("agents", a_rounds), ("humans", h_rounds)):
            d = df[(df.treatment == "SC-MC") & (df.row == df.col)]
            piv = d.pivot_table(index="rep_F", columns="rep_C", values="row", aggfunc=["mean", "count"])
            rows = [[f"F says {i}"] + [fmt(piv["mean"].get(j, {}).get(i)) if piv["count"].get(j, {}).get(i, 0) > 5 else "" for j in range(1, 6)]
                    for i in range(1, 6)]
            out += [f"{name}:", "", table(["", *[f"C says {j}" for j in range(1, 6)]], rows), ""]
        rows = []
        for name, df in (("agents", a_rounds), ("humans", h_rounds)):
            d = df[df.treatment == "SC-MC"]
            agree = d[d.rep_F == d.rep_C]
            split = d[(d.rep_F == 5) & (d.rep_C == 1)]
            rows.append([name, f"{100 * ((agree.row != agree.rep_F) | (agree.col != agree.rep_C)).mean():.1f} ({len(agree)})",
                         f"{100 * (1 - ((split.row == 3) & (split.col == 3)).mean()):.1f} ({len(split)})" if len(split) else "– (0)"])
        out.append(table(["SC-MC, all rounds", "matching reports not followed % (n)", "no safe choice after reports 5 and 1 % (n)"], rows))
    rows = []
    for t in [t for t in treatments if t in REPORTERS]:
        rows.append([t] + [f"{100 * manager_mistake(window(a[a.treatment == t], w)):.1f} / {100 * manager_mistake(window(h[h.treatment == t], w)):.1f}"
                           for w in ("10-18", "all") for a, h in [(a_rounds, h_rounds)]])
    out += ["", "Manager mistakes (p. 1973), agents / humans recomputed:", "", table(["Treatment", "rounds 10-18 %", "all rounds %"], rows)]

    chat_t = [t for t in treatments if t in PRINTED["messages"]]
    if chat_t:
        out += ["", "## Table 6, messages per round, A and per agent: agents / humans recomputed (printed). CH treatments all rounds; EC-MC rounds 10-18", ""]
        rows = []
        for t in chat_t:
            w = "10-18" if t == "EC-MC" else "all"
            a, h = window(a_chat[a_chat.treatment == t], w), window(h_chat[h_chat.treatment == t], w)
            pa, pg = PRINTED["messages"][t]
            ends = Counter(a.ended)
            rows.append([t, f"{fmt(a.A.mean())} / {fmt(h.A.mean())} ({fmt(pa)})" if t != "CH/S-D" else "–",
                         f"{fmt(a.agents.mean() / 2)} / {fmt(h.agents.mean() / 2)} ({fmt(pg)})",
                         fmt(a.agents_distinct.mean() / 2), f"{ends['budget']} of {len(a)}"])
        out.append(table(["Treatment", "A", "per agent", "per agent, distinct messages", "chats ending at the turn limit"], rows))
        out += ["", "Content categories beyond game claims wait for Appendix E (APPROACH.md)."]

    rep_t = [t for t in treatments if t in REPORTERS]
    for t in [t for t in rep_t if t in ("SC-MC", "CH-MC", "EC-MC")]:
        a, h = table7(a_rep, t), table7(h_rep, t)
        p = PRINTED["table7"].get(t)
        out += ["", f"## Table 7, {t}, all rounds, by remapped game: agents / humans recomputed" + (" (printed)" if p else ""), ""]
        rows = [[str(k)] + [f"{fmt(a.loc[k, c])} / {fmt(h.loc[k, c])}" + (f" ({fmt(p[k - 1][j])})" if p else "") for j, c in enumerate(("truth", "lie"))]
                for k in range(1, 6)]
        out.append(table(["Remapped game", "truth %", "lie %"], rows))

    out += ["", "## Table 9, rounds 10-18: agents / humans recomputed (printed)", ""]
    rows = []
    for t in rep_t:
        ar, hr = window(a_rounds[a_rounds.treatment == t], "10-18"), window(h_rounds[h_rounds.treatment == t], "10-18")
        al, hl = window(a_rep[a_rep.treatment == t], "10-18"), window(h_rep[h_rep.treatment == t], "10-18")
        p = PRINTED["table9"][t]
        rows.append([t, f"{fmt(100 * ar.revealed.mean())} / {fmt(100 * hr.revealed.mean())} ({fmt(p[0])})",
                     f"{fmt(100 * al.lie.mean())} / {fmt(100 * hl.lie.mean())} ({fmt(p[1])})", fmt(100 * al.truth.mean()),
                     f"{al[al.lie > 0].group.nunique()} of {al.group.nunique()}"])
    out.append(table(["Treatment", "game revealed %", "agent-rounds with a lie %", "agent-rounds with the truth %", "agent groups with any lie"], rows))

    # Tests
    rng = np.random.default_rng(SEED)
    out += ["", "## Tests, rounds 10-18 (exact two-sided Wilcoxon tests on group means)", "",
            "Signed-rank against the safe outcome (zeros ranked, unsigned):", ""]
    rows = []
    for t in treatments:
        a, h = safe_diff(window(a_rounds[a_rounds.treatment == t], "10-18")), safe_diff(window(h_rounds[h_rounds.treatment == t], "10-18"))
        rows.append([t, fmt(a.mean(), 2), f"{(a == 0).sum()} of {len(a)}", fmt(signrank_p(a), 3), fmt(h.mean(), 2), fmt(signrank_p(h), 3),
                     fmt(PRINTED["safe"].get(t), 3)])
    out.append(table(["Treatment", "agents: surplus − safe", "groups at 0", "agents p", "humans: surplus − safe", "humans p", "printed p"], rows))
    out += ["", "Rank-sum on group surplus:", ""]
    rows = []
    for (x, y), pp in PRINTED["ranksum"].items():
        if {x, y} <= set(treatments):
            sa = {t: window(a_rounds[a_rounds.treatment == t], "10-18").groupby("group").surplus.mean() for t in (x, y)}
            sh = {t: window(h_rounds[h_rounds.treatment == t], "10-18").groupby("group").surplus.mean() for t in (x, y)}
            rows.append([f"{x} vs {y}", fmt(sa[x].mean() - sa[y].mean(), 2), fmt(ranksum_p(sa[x], sa[y]), 3),
                         fmt(sh[x].mean() - sh[y].mean(), 2), fmt(ranksum_p(sh[x], sh[y]), 3), fmt(pp, 3)])
    out.append(table(["Contrast", "agents: difference", "agents p", "humans: difference", "humans p", "printed p"], rows))

    if {"SC-MC", "CH-MC"} <= set(treatments):
        out += ["", "## Primary hypotheses (agents; humans recomputed for reference). Permutation p from 10,000 draws; bootstrap 95% CI over groups", ""]
        rows = []
        for name, rd, rp in (("agents", a_rounds, a_rep), ("humans", h_rounds, h_rep)):
            ch, sc = (window(rd[rd.treatment == t], "10-18") for t in ("CH-MC", "SC-MC"))
            d = safe_diff(ch)
            m, p, ci = perm_boot_one(d, rng)
            rows.append(["R1: CH-MC surplus − safe", name, fmt(m, 2), fmt(signrank_p(d), 3), fmt(p, 3), f"[{ci[0]:.2f}, {ci[1]:.2f}]"])
            x, y = ch.groupby("group").surplus.mean(), sc.groupby("group").surplus.mean()
            m, p, ci = perm_boot_two(x, y, rng)
            rows.append(["R2: CH-MC − SC-MC surplus", name, fmt(m, 2), fmt(ranksum_p(x, y), 3), fmt(p, 3), f"[{ci[0]:.2f}, {ci[1]:.2f}]"])
            lie = {t: 100 * window(rp[rp.treatment == t], "10-18").groupby("group").lie.mean() for t in ("SC-MC", "CH-MC")}
            m, p, ci = perm_boot_two(lie["SC-MC"], lie["CH-MC"], rng)
            rows.append(["R3: SC-MC − CH-MC lie rate (pp)", name, fmt(m, 1), fmt(ranksum_p(lie["SC-MC"], lie["CH-MC"]), 3), fmt(p, 3), f"[{ci[0]:.1f}, {ci[1]:.1f}]"])
            s_sc, s_ch, diff, p, ci = r4(rp, rng)
            rows.append([f"R4: lie slope per remapped game, SC-MC {fmt(s_sc)} vs CH-MC {fmt(s_ch)} (pp)", name, fmt(diff, 1), "–", fmt(p, 3),
                         f"[{ci[0]:.1f}, {ci[1]:.1f}]"])
        out.append(table(["Hypothesis", "data", "estimate", "Wilcoxon p", "permutation p", "bootstrap 95% CI"], rows))
        out += ["", "R4 uses all 18 rounds, as Table 7; the bootstrap and permutation use 1,000 draws of whole groups."]

    main = [t for t in MAIN if t in treatments]
    if len(main) == 7:
        sa = {t: window(a_rounds[a_rounds.treatment == t], "10-18").surplus.mean() for t in main}
        sh = {t: window(h_rounds[h_rounds.treatment == t], "10-18").surplus.mean() for t in main}
        ca = {t: (lambda d: (d.row == d.col).mean())(window(a_rounds[a_rounds.treatment == t], "10-18")) for t in main}
        rho = spearmanr([sa[t] for t in main], [sh[t] for t in main]).statistic
        out += ["", "## Secondary", "",
                f"- NC-D surplus rank among the seven treatments (1 = lowest): {sorted(main, key=sa.get).index('NC-D') + 1}; "
                f"coordination rank: {sorted(main, key=ca.get).index('NC-D') + 1}.",
                f"- Rank correlation of treatment surplus, agents against humans recomputed: {rho:.2f}.",
                "- Agents' order by surplus: " + ", ".join(f"{t} {sa[t]:.1f}" for t in sorted(main, key=sa.get, reverse=True)) + ".",
                "- Humans' order: " + ", ".join(f"{t} {sh[t]:.1f}" for t in sorted(main, key=sh.get, reverse=True)) + "."]
    if set(REPORTERS) <= set(treatments):
        lie = {t: 100 * window(a_rep[a_rep.treatment == t], "10-18").lie.mean() for t in REPORTERS}
        out.append(f"- EC-MC lying between SC-MC and CH-MC: SC-MC {lie['SC-MC']:.1f}%, EC-MC {lie['EC-MC']:.1f}%, CH-MC {lie['CH-MC']:.1f}%.")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(report([Path(d) for d in sys.argv[1:]]))
