"""Findings PDF (portrait A4: charts, tables, little text), built from results/trials_summary.csv and the authors'
data in source/dataverse (fetch with harness/fetch_data.py). Needs matplotlib, unlike the rest of the harness.

Usage (from second-test/):
    python3 harness/summary.py && python3 harness/report.py      # writes results/second-test-findings.pdf
"""
import csv
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "second-test-findings.pdf"
ORDER = ["HubAndSpoke", "CorePeriphery", "InCorePeriphery", "CompleteClique", "LocallyClustered", "OutCorePeriphery"]
FINAL, FINAL_ISOLATES = "20261021-final-net10", "20261021-final-empty10"
SETTINGS = [  # (network run, isolate run, label) for Figure 3 and Table 3
    ("20261021-persona-net10", "20261021-persona-empty10", "Personas, full memory"),
    ("20261021-var-memory4", "20261021-var-memory4-empty10", "Memory 4, notes unlimited"),
    ("20261021-var-mem4pad8", "20261021-var-mem4pad8-empty10", "Memory 4, notepad 8"),
    ("20261021-var-mem3pad8", "20261021-var-mem3pad8-empty10", "Memory 3, notepad 8"),
    ("20261021-var-mem3pad15", "20261021-var-mem3pad15-empty10", "Memory 3, notepad 15"),
    (FINAL, FINAL_ISOLATES, "Final: + susceptibility, plain pay"),
]


def build():
    rows = list(csv.DictReader((ROOT / "results" / "trials_summary.csv").open()))
    done = [r for r in rows if r["status"] == "complete"]
    num = lambda r, k: int(r[k]) if r[k] not in ("", None) else 0
    by_run = defaultdict(lambda: defaultdict(list))
    for r in done:
        by_run[r["run"]][r["network"]].append(r)
    hum = defaultdict(list)
    for r in csv.DictReader((ROOT / "source" / "dataverse" / "trialData.csv").open()):
        hum[r["network"]].append(int(r["numCorrectAtFinish"]))
    hc = [0, 0]
    for r in csv.DictReader((ROOT / "source" / "dataverse" / "solutions1.csv").open()):
        try:
            aw, ma = int(r["altersWAnswer"]), int(r["matchingAlters"])
        except ValueError:
            continue
        if r["network"] in ORDER and aw > 0:
            hc[0] += ma > 0
            hc[1] += 1

    def follow(run):
        hub = by_run[run]["HubAndSpoke"]
        return [sum(num(r, "hub_followers") for r in hub), sum(num(r, "hub_follow_eligible") for r in hub)]

    final = by_run[FINAL]
    settings = []
    for run, iso, label in SETTINGS:
        nets = by_run[run]
        allv = [num(r, "num_correct") for n in ORDER for r in nets[n]]
        cen = [num(r, "num_correct") for n in ("HubAndSpoke", "CorePeriphery") for r in nets[n]]
        ctl = [num(r, "num_correct") for n in ("LocallyClustered", "CompleteClique") for r in nets[n]]
        fol = follow(run)
        settings.append(dict(label=label, k=len(nets["HubAndSpoke"]), iso=st.mean(num(r, "num_correct") for r in by_run[iso]["Empty"]),
                             mean=st.mean(allv), le1=sum(v <= 1 for v in allv) / len(allv), gt6=sum(v > 6 for v in allv) / len(allv),
                             contrast=st.mean(cen) - st.mean(ctl), follow=fol[0] / fol[1]))
    out_cp = final["OutCorePeriphery"]
    return {
        "order": ORDER, "humans": {n: hum[n] for n in ORDER}, "humans_isolates": hum["SyntheticIsolates"],
        "agents": {n: [num(r, "num_correct") for r in final[n]] for n in ORDER},
        "agents_isolates": [num(r, "num_correct") for r in by_run[FINAL_ISOLATES]["Empty"]],
        "agents_follow": follow(FINAL),
        "agents_copy": sum(num(r, "copy_matches") for n in ORDER for r in final[n]) / sum(num(r, "copy_changes") for n in ORDER for r in final[n]),
        "agents_outcp_core": [sum(num(r, "core_correct") for r in out_cp), 3 * len(out_cp)],
        "humans_copy": hc[0] / hc[1], "settings": settings,
        "total_cost": sum(float(r["cost_usd"]) for r in rows), "n_trials": len(rows),
    }


data = build()

SURFACE, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
HUM, AGT = "#2a78d6", "#eb6834"  # categorical slots 1 and 2 (validated: CVD dE 24.7, normal 33.6)
GOOD, BAD = "#006300", "#d03b3b"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": BASE, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "legend.frameon": False,
})
A4 = (8.27, 11.69)
NAMES = {"HubAndSpoke": "Hub-and-spoke", "CorePeriphery": "Core-periphery", "InCorePeriphery": "In core-periphery",
         "CompleteClique": "Complete clique", "LocallyClustered": "Locally clustered", "OutCorePeriphery": "Out core-periphery"}
order = data["order"]
H, A = data["humans"], data["agents"]
mean = st.mean
pct = lambda xs, f: sum(f(v) for v in xs) / len(xs)


def header(fig, title, sub=None):
    fig.text(0.07, 0.955, title, fontsize=15, fontweight="bold", va="top")
    if sub:
        fig.text(0.07, 0.928, sub, fontsize=9.5, color=INK2, va="top")


def footer(fig, page):
    fig.text(0.07, 0.03, "Synthetic replication of Bernstein, Shore & Jang (2023), Organization Science 34(6). gpt-6-luna agents.",
             fontsize=7, color=MUTED)
    fig.text(0.93, 0.03, str(page), fontsize=7, color=MUTED, ha="right")


def table(fig, rect, rows, header_row, col_widths, aligns=None, mark=None):
    """A clean table: hairline rules, header in secondary ink. mark(r, c) -> colour for a cell's text."""
    ax = fig.add_axes(rect)
    ax.axis("off")
    n = len(rows) + 1
    h = 1 / n
    x = 0
    xs = []
    for w in col_widths:
        xs.append(x)
        x += w
    aligns = aligns or ["left"] + ["right"] * (len(header_row) - 1)
    for c, (label, x0, w) in enumerate(zip(header_row, xs, col_widths)):
        ha = aligns[c]
        ax.text(x0 + (w - 0.01 if ha == "right" else 0.005), 1 - h / 2, label, ha=ha, va="center", fontsize=7.8,
                color=INK2, fontweight="bold", transform=ax.transAxes)
    ax.plot([0, 1], [1 - h, 1 - h], color=BASE, lw=0.8, transform=ax.transAxes, clip_on=False)
    for r, row in enumerate(rows):
        y = 1 - h * (r + 1.5)
        for c, (val, x0, w) in enumerate(zip(row, xs, col_widths)):
            ha = aligns[c]
            color = mark(r, c) if mark else None
            ax.text(x0 + (w - 0.01 if ha == "right" else 0.005), y, val, ha=ha, va="center", fontsize=8.2,
                    color=color or INK, transform=ax.transAxes)
        ax.plot([0, 1], [1 - h * (r + 2)] * 2, color=GRID, lw=0.5, transform=ax.transAxes, clip_on=False)
    return ax


def stat_tile(fig, x, y, w, label, agents, humans, note, ok):
    ax = fig.add_axes([x, y, w, 0.105])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="#f3f2ee", edgecolor="none"))
    ax.text(0.07, 0.83, label, fontsize=7.8, color=INK2, transform=ax.transAxes, va="center")
    ax.text(0.07, 0.48, agents, fontsize=19, fontweight="bold", transform=ax.transAxes, va="center")
    ax.text(0.07, 0.17, f"humans {humans}", fontsize=7.8, color=INK2, transform=ax.transAxes, va="center")
    ax.text(0.93, 0.48, note, fontsize=8, ha="right", va="center",
            color=GOOD if ok else BAD, transform=ax.transAxes)


with PdfPages(OUT) as pdf:
    # --- page 1: overview -------------------------------------------------------------------------
    fig = plt.figure(figsize=A4)
    header(fig, "Network centralization with LLM agents",
           "Replication of Bernstein, Shore & Jang (2023) with synthetic participants: final setting, 10 trials per network")
    contrast_a = mean(A["HubAndSpoke"] + A["CorePeriphery"]) - mean(A["LocallyClustered"] + A["CompleteClique"])
    contrast_h = mean(H["HubAndSpoke"] + H["CorePeriphery"]) - mean(H["LocallyClustered"] + H["CompleteClique"])
    alla = [v for n in order for v in A[n]]
    allh = [v for n in order for v in H[n]]
    tiles = [
        ("Correct at the end (of 9)", f"{mean(alla):.1f}", f"{mean(allh):.1f}", "matches", True),
        ("Centralised minus controls", f"{contrast_a:+.2f}", f"{contrast_h:+.2f}", "too weak", False),
        ("Out core-periphery", f"{mean(A['OutCorePeriphery']):.1f}", f"{mean(H['OutCorePeriphery']):.2f}", "worst, matches", True),
        ("Spokes adopting correct hub", f"{data['agents_follow'][0] / data['agents_follow'][1]:.0%}", "64%", "too low", False),
    ]
    for i, t in enumerate(tiles):
        stat_tile(fig, 0.07 + i * 0.218, 0.79, 0.205, *t)

    ax = fig.add_axes([0.1, 0.47, 0.84, 0.27])
    x = range(len(order))
    w = 0.36
    ax.bar([i - w / 2 - 0.01 for i in x], [mean(H[n]) for n in order], w, color=HUM, label="Humans (30 trials each)", zorder=2)
    ax.bar([i + w / 2 + 0.01 for i in x], [mean(A[n]) for n in order], w, color=AGT, label="Agents (10 trials each)", zorder=2)
    ax.axhline(mean(data["humans_isolates"]), color=HUM, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.axhline(mean(data["agents_isolates"]), color=AGT, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(5.6, mean(data["humans_isolates"]) + 0.08, "isolates", fontsize=7, color=MUTED, ha="right", va="bottom")
    labels = {"HubAndSpoke": "Hub-and-\nspoke", "CorePeriphery": "Core-\nperiphery", "InCorePeriphery": "In core-\nperiphery",
              "CompleteClique": "Complete\nclique", "LocallyClustered": "Locally\nclustered", "OutCorePeriphery": "Out core-\nperiphery"}
    ax.set_xticks(list(x), [labels[n] for n in order], color=INK2, fontsize=8)
    ax.set_ylabel("Mean number correct at the end (of 9)")
    ax.set_ylim(0, 6)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper right", fontsize=8, ncols=2)
    ax.set_title("Figure 1. Mean correct per network (dashed: isolates, humans 3.19, agents 2.6)", loc="left", fontsize=9, color=INK2)

    rows = [[NAMES[n], f"{mean(H[n]):.2f}", f"{mean(A[n]):.1f}", f"{pct(H[n], lambda v: v <= 1):.0%}", f"{pct(A[n], lambda v: v <= 1):.0%}",
             f"{pct(H[n], lambda v: v > 6):.0%}", f"{pct(A[n], lambda v: v > 6):.0%}"] for n in order]
    rows.append(["All networks", f"{mean(allh):.2f}", f"{mean(alla):.1f}", f"{pct(allh, lambda v: v <= 1):.0%}", f"{pct(alla, lambda v: v <= 1):.0%}",
                 f"{pct(allh, lambda v: v > 6):.0%}", f"{pct(alla, lambda v: v > 6):.0%}"])
    table(fig, [0.07, 0.2, 0.86, 0.2], rows, ["Network", "Mean, humans", "Mean, agents", "0–1 correct, h.", "0–1 correct, a.",
                                              "> 6 correct, h.", "> 6 correct, a."], [0.25, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125])
    fig.text(0.07, 0.15, "Overall level, the complete clique, core-periphery and the weak out core-periphery match the human data. The main\n"
                         "centralisation advantage is small and not significant (one-sided permutation p = 0.43), because hub-and-spoke is too low.",
             fontsize=8.5, color=INK2, va="top", linespacing=1.5)
    footer(fig, 1)
    pdf.savefig(fig)
    plt.close(fig)

    # --- page 2: distributions and hypotheses ------------------------------------------------------
    fig = plt.figure(figsize=A4)
    header(fig, "Distributions and hypotheses", "Share of trials with at most k of 9 correct, as in the paper's Figure 6")
    for i, n in enumerate(order):
        ax = fig.add_axes([0.08 + (i % 3) * 0.3, 0.665 - (i // 3) * 0.2, 0.25, 0.15])
        for vals, col in ((H[n], HUM), (A[n], AGT)):
            ks = list(range(10))
            ax.step(ks, [pct(vals, lambda v, k=k: v <= k) for k in ks], where="post", color=col, lw=2)
        ax.set_xlim(0, 9)
        ax.set_ylim(0, 1.02)
        ax.set_xticks([0, 3, 6, 9])
        ax.set_yticks([0, 0.5, 1], ["0", ".5", "1"])
        ax.set_title(NAMES[n], loc="left", fontsize=8.5, color=INK)
        if i % 3 == 0:
            ax.set_ylabel("share of trials", fontsize=7.5)
        if i // 3 == 1:
            ax.set_xlabel("number correct", fontsize=7.5)
    fig.text(0.08, 0.875, "— Humans", color=HUM, fontsize=8.5, fontweight="bold")
    fig.text(0.2, 0.875, "— Agents", color=AGT, fontsize=8.5, fontweight="bold")
    fig.text(0.08, 0.408, "Figure 2. A curve further right means more participants correct. A steep jump at 0 or 9 means trials end all wrong or all right.",
             fontsize=7.5, color=INK2)

    fol = data["agents_follow"]
    core = data["agents_outcp_core"]
    hyp = [
        ["H1  Fewer stuck trials (0–1 correct)", "hub 10%, CP 27%, isolates 10%", "hub 30%, CP 40%, isolates 30%", "Partly"],
        ["H2  Answer spreads (> 6 correct)", "hub 27%, CP 33%, clique 33%", "hub 20%, CP 50%, clique 40%", "Partly"],
        ["H3  Better on average (centralised minus controls)", f"{contrast_h:+.2f}", f"{contrast_a:+.2f} (p = 0.43)", "No"],
        ["H4  One-way centralisation brings no benefit", "out core-periphery 3.13 (worst)", f"{mean(A['OutCorePeriphery']):.1f} (worst)", "Yes"],
        ["Mechanism: spokes adopt a correct hub", "64%", f"{fol[0] / fol[1]:.0%} ({fol[0]} of {fol[1]})", "No"],
        ["Mechanism: out core-periphery core correct", "32%", f"{core[0] / core[1]:.0%} ({core[0]} of {core[1]})", "Yes"],
        ["Answer changes matching a neighbour", f"{data['humans_copy']:.0%}", f"{data['agents_copy']:.0%}", "No"],
    ]
    colour = {"Yes": GOOD, "No": BAD, "Partly": INK2}
    table(fig, [0.07, 0.11, 0.86, 0.24], hyp, ["Hypothesis or mechanism", "Humans", "Agents", "Replicates"],
          [0.41, 0.24, 0.25, 0.10], ["left", "left", "left", "right"], mark=lambda r, c: colour[hyp[r][3]] if c == 3 else None)
    fig.text(0.07, 0.37, "Table 2. The paper's hypotheses and mechanism checks, humans against the final agent setting (CP: core-periphery)",
             fontsize=9, color=INK2)
    footer(fig, 2)
    pdf.savefig(fig)
    plt.close(fig)

    # --- page 3: what the settings did -------------------------------------------------------------
    fig = plt.figure(figsize=A4)
    header(fig, "How the settings moved the result", "The main design variants tested; isolates were checked before every network run")
    rows_s = data["settings"]
    ax = fig.add_axes([0.36, 0.6, 0.57, 0.27])
    ys = list(range(len(rows_s)))[::-1]
    ax.barh(ys, [r["contrast"] for r in rows_s], 0.55, color=AGT, zorder=2)
    ax.axvline(contrast_h, color=HUM, lw=1.5, ls=(0, (4, 3)))
    ax.axvline(0, color=BASE, lw=0.8)
    ax.text(contrast_h + 0.05, len(rows_s) - 0.45, f"humans {contrast_h:+.2f}", color=HUM, fontsize=7.5, va="bottom")
    ax.set_yticks(ys, [r["label"] for r in rows_s], fontsize=8, color=INK2)
    ax.set_xlabel("Centralised minus decentralised controls (mean correct)")
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-2, 4)
    ax.set_title("Figure 3. The main contrast across settings", loc="left", fontsize=9, color=INK2, x=-0.45)
    tab = [[r["label"], str(r["k"]), f"{r['iso']:.1f}", f"{r['mean']:.1f}", f"{r['le1']:.0%}", f"{r['gt6']:.0%}", f"{r['contrast']:+.2f}", f"{r['follow']:.0%}"]
           for r in rows_s]
    tab.insert(0, ["Humans", "30", "3.2", f"{mean(allh):.1f}", f"{pct(allh, lambda v: v <= 1):.0%}", f"{pct(allh, lambda v: v > 6):.0%}", f"{contrast_h:+.2f}", "64%"])
    table(fig, [0.07, 0.3, 0.86, 0.22], tab, ["Setting", "Trials/net.", "Isolates", "Networks", "0–1", "> 6", "Contrast", "Hub followed"],
          [0.31, 0.09, 0.09, 0.1, 0.08, 0.08, 0.12, 0.13], mark=lambda r, c: HUM if r == 0 else None)
    fig.text(0.07, 0.535, "Table 3. Isolates and networks: mean correct of 9; 0–1 and > 6: share of network trials", fontsize=9, color=INK2)
    fig.text(0.07, 0.25, "Full memory makes agents pool clues, so dense networks win. Limiting memory to the last few turns brings back\n"
                         "learning from others' answers, but a notepad of 8 words makes every network lock onto the red herring.\n"
                         "Memory 3 with a 15-word notepad sits closest; the susceptibility trait changed nothing measurable.",
             fontsize=8.5, color=INK2, va="top", linespacing=1.5)
    footer(fig, 3)
    pdf.savefig(fig)
    plt.close(fig)

    # --- page 4: setup ------------------------------------------------------------------------------
    fig = plt.figure(figsize=A4)
    header(fig, "Setup and departures from the original")
    setup = [
        ["Task", "The paper's murder mystery, 41 clues and three broadcasts (Appendix B.3); names redrawn per trial"],
        ["Networks", "Six treatments, 9 players; reconstructed from Appendix E and checked against the authors' data"],
        ["Isolates", "Nine unconnected agents (humans: resampled from in core-periphery nodes 5, 7, 9)"],
        ["Time", "15 minutes as 30 turns of 30 seconds; all agents act at once"],
        ["Search", "1 search per turn; a search can return a clue already found"],
        ["Messages", "Along network ties only; writing a message uses the turn's search"],
        ["Agents", "gpt-6-luna, reasoning effort drawn per agent (low, medium, high)"],
        ["Personas", "MTurk demographics (Levay et al. 2016), Big Five, susceptibility to influence"],
        ["Memory", "Last 3 turns plus a notepad of up to 15 words per turn, always visible"],
        ["Calibration", "Settings fixed on isolates only, before the network runs"],
    ]
    table(fig, [0.07, 0.56, 0.86, 0.33], setup, ["Element", "Final setting"], [0.18, 0.82], ["left", "left"])
    dep = [
        ["Keywords per clue", "Not published; rebuilt from the names in each clue"],
        ["Discrete turns", "Real time replaced by 30-second turns"],
        ["Memory and notepad", "Humans could scroll back through all messages; the limit models working memory"],
        ["No dropout", "16% of human trials had some dropout"],
        ["Practice", "Stage 1 only, no screening; stage 2 not run"],
        ["Same model", "All agents share one model; outcomes stay more bimodal than human ones"],
    ]
    table(fig, [0.07, 0.28, 0.86, 0.2], dep, ["Departure", "What it means"], [0.25, 0.75], ["left", "left"])
    fig.text(0.07, 0.5, "Departures to report", fontsize=10, fontweight="bold")
    fig.text(0.07, 0.22, f"Cost: ${data['total_cost']:.2f} for {data['n_trials']} trial records across calibration, pilots and the final run "
                         "(gpt-6-luna list prices).\nFor comparison, the human study paid about $3,800 to its main-trial participants.",
             fontsize=8.5, color=INK2, va="top", linespacing=1.5)
    footer(fig, 4)
    pdf.savefig(fig)
    plt.close(fig)
print("written", OUT)
