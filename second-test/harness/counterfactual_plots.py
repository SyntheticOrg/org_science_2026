"""Counterfactual figures: (1) humans vs agents in the paper's out and in core-periphery, (2) the agents' paper networks
against every counterfactual. Share of players correct at the end and share of core nodes correct, per trial, with
bootstrap 95% intervals. Built from results/trials_summary.csv and source/dataverse.

Usage (from second-test/):
    python3 harness/summary.py && python3 harness/counterfactual_plots.py   # writes results/counterfactuals-*.png
"""
import csv
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import networks

ROOT = Path(__file__).resolve().parent.parent
RUNS = {"20261021-final-net10", "20261026-final-cp11to20", "20261026-counterfactuals-10", "20261026-counterfactuals-11to20"}
SURFACE, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
HUM, AGT = "#2a78d6", "#eb6834"  # as report.py (validated pair)
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"], "font.size": 9,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": BASE, "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "legend.frameon": False,
})


def ci(xs, n=5000, rng=random.Random(1)):
    means = sorted(st.mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return st.mean(xs), means[int(0.025 * n)], means[int(0.975 * n)]


def perm_p(a, b, n=20000, rng=random.Random(2)):
    obs, pool, hits = abs(st.mean(a) - st.mean(b)), a + b, 0
    for _ in range(n):
        rng.shuffle(pool)
        hits += abs(st.mean(pool[:len(a)]) - st.mean(pool[len(a):])) >= obs - 1e-12
    return hits / n


def agents():
    """network -> (per-trial share correct, per-trial share of core correct)"""
    out = defaultdict(lambda: ([], []))
    for r in csv.DictReader((ROOT / "results" / "trials_summary.csv").open()):
        if r["run"] not in RUNS or r["status"] != "complete" or r["network"] not in networks.COUNTERFACTUALS \
                and r["network"] not in ("OutCorePeriphery", "InCorePeriphery"):
            continue
        out[r["network"]][0].append(int(r["num_correct"]) / int(r["players"]))
        out[r["network"]][1].append(int(r["core_correct"]) / len(networks.core(r["network"])))
    return out


def humans():
    share = defaultdict(list)
    for r in csv.DictReader((ROOT / "source" / "dataverse" / "trialData.csv").open()):
        share[r["network"]].append(int(r["numCorrectAtFinish"]) / 9)
    core = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader((ROOT / "source" / "dataverse" / "individualData.tab").open()):
        if int(r["node"]) in networks.CORE and r["correctAtEnd"] not in ("", "NA"):
            core[r["network"]][r["trial_id"]].append(int(r["correctAtEnd"]))
    return {n: (share[n], [st.mean(v) for v in core[n].values()]) for n in ("OutCorePeriphery", "InCorePeriphery")}


A, H = agents(), humans()
pct = lambda v: f"{v:.0%}"


def figure_paper_vs_agents(path):
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.8), sharey=True)
    w = 0.36
    for ax, net, title in zip(axes, ("OutCorePeriphery", "InCorePeriphery"), ("Out core-periphery", "In core-periphery")):
        for g, (label, k) in enumerate((("All players", 0), ("Core (nodes 1–3)", 1))):
            for dx, data, col, who in ((-w / 2 - 0.01, H, HUM, "Humans"), (w / 2 + 0.01, A, AGT, "Agents")):
                m, lo, hi = ci(data[net][k])
                ax.bar(g + dx, m, w, color=col, zorder=2, label=f"{who} ({len(data[net][k])} trials)" if g == 0 else None)
                ax.errorbar(g + dx, m, yerr=[[m - lo], [hi - m]], color=INK2, lw=1, capsize=3, zorder=3)
                ax.text(g + dx, hi + 0.02, pct(m), ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks([0, 1], ["All players", "Core (nodes 1–3)"], color=INK2)
        ax.grid(axis="x", visible=False)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.legend(loc="upper right", fontsize=8)
    axes[0].set_ylim(0, 1)
    axes[0].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    axes[0].set_ylabel("Correct at the end (share)")
    fig.suptitle("Paper (humans) vs replication (agents): share correct at the end, 95% bootstrap intervals",
                 x=0.07, ha="left", fontsize=10, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(path, dpi=200)


SERIES = {  # direction -> [(series, [(network, label)])]; None marks the paper's network
    "Out": [("Paper network", [("OutCorePeriphery", "core 3, periphery 6, 3 ties up")]),
            ("Ties back up", [("OutCP_up0", "0 ties up"), ("OutCP_up6", "6 ties up")]),
            ("Core size", [("OutCP_core1", "core 1"), ("OutCP_core2", "core 2"), ("OutCP_core4", "core 4")]),
            ("Periphery size", [("OutCP_per3", "periphery 3"), ("OutCP_per9", "periphery 9")]),
            ("Star", [("OutStar", "star")])],
    "In": [("Paper network", [("InCorePeriphery", "core 3, periphery 6, 3 ties down")]),
           ("Ties down", [("InCP_down0", "0 ties down"), ("InCP_down6", "6 ties down")]),
           ("Core size", [("InCP_core1", "core 1"), ("InCP_core2", "core 2"), ("InCP_core4", "core 4")]),
           ("Periphery size", [("InCP_per3", "periphery 3"), ("InCP_per9", "periphery 9")]),
           ("Star", [("InStar", "star")])],
}


def figure_agents_vs_counterfactuals(path):
    fig, axes = plt.subplots(2, 2, figsize=(8.5, 9), sharex=True)
    for row, (d, series) in enumerate(SERIES.items()):
        base = series[0][1][0][0]
        rows, y = [], 0
        for s, items in series:
            for net, label in items:
                rows.append((y, net, label, s))
                y -= 1
            y -= 0.6
        for col, (k, metric) in enumerate(((0, "All players correct"), (1, "Core correct"))):
            ax = axes[row][col]
            bm, blo, bhi = ci(A[base][k])
            ax.axvspan(blo, bhi, color=AGT, alpha=0.12, lw=0, zorder=0)
            ax.axvline(bm, color=AGT, lw=1.2, ls=(0, (4, 3)), zorder=1)
            for yy, net, label, s in rows:
                m, lo, hi = ci(A[net][k])
                is_base = net == base
                p = None if is_base else perm_p(A[net][k], A[base][k])
                col_ = AGT if is_base else INK2
                ax.plot([lo, hi], [yy, yy], color=col_, lw=1.5, zorder=2, solid_capstyle="round")
                ax.plot(m, yy, "o", ms=7, color=col_, mec=SURFACE, mew=1.5, zorder=3)
                note = pct(m) + ("" if is_base else (f"  p={p:.3f}" if p >= 0.001 else "  p<0.001") if p < 0.05 else "")
                ax.text(hi + 0.02, yy, note, va="center", fontsize=7.5, color=INK if p is not None and p < 0.05 else INK2,
                        fontweight="bold" if p is not None and p < 0.05 else "normal")
            ax.set_yticks([r[0] for r in rows], [r[2] for r in rows] if col == 0 else [], fontsize=8, color=INK2)
            if col == 0:
                for yy, net, label, s in rows:
                    if net == base or rows[[r[1] for r in rows].index(net) - 1][3] != s:
                        ax.text(-0.02, yy + 0.55, s.upper(), transform=ax.get_yaxis_transform(), ha="right", fontsize=6.5,
                                color=MUTED, fontweight="bold")
            ax.grid(axis="y", visible=False)
            ax.set_xlim(0, 1.08)
            ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
            ax.set_title(f"{d} core-periphery: {metric.lower()}", loc="left", fontsize=9.5, color=INK)
    for ax in axes[1]:
        ax.set_xlabel("Share correct at the end (mean, 95% bootstrap interval)")
    fig.suptitle("Agents: paper network (orange, band = its 95% interval) vs counterfactuals, 20 trials each\n"
                 "bold: differs from the paper network, permutation test p < 0.05",
                 x=0.03, y=0.995, ha="left", fontsize=10, color=INK2)
    fig.tight_layout(rect=(0, 0, 1, 0.965))
    fig.savefig(path, dpi=200)


if __name__ == "__main__":
    figure_paper_vs_agents(ROOT / "results" / "counterfactuals-1-paper-vs-agents.png")
    figure_agents_vs_counterfactuals(ROOT / "results" / "counterfactuals-2-agents-vs-deviations.png")
    print("wrote results/counterfactuals-1-paper-vs-agents.png, results/counterfactuals-2-agents-vs-deviations.png")
