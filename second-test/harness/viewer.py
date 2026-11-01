"""Trial viewer: one self-contained HTML page per trial record, plus an index page for the run.

Usage (from second-test/):
    python3 harness/viewer.py runs/<run>                 # writes runs/<run>/view/index.html and one page per trial
    python3 harness/viewer.py runs/<run>/Empty-001.json  # a single trial

Each page shows the network, every agent's murderer answer per 30-second turn (click a cell for what the agent
saw, its reasoning summary, its private notes, and what it did), the switches to and from the correct answer
with the answers the agent could see at that moment, and the message log.
"""

import html
import json
import sys
from pathlib import Path

import networks

PRICE_PER_M = {"input": 0.10, "cached": 0.01, "output": 0.50}  # gpt-6-luna list prices, USD (as first-test)
TICK = 30


def cost(usage):
    return (PRICE_PER_M["input"] * (usage["input_tokens"] - usage["cached_tokens"])
            + PRICE_PER_M["cached"] * usage["cached_tokens"] + PRICE_PER_M["output"] * usage["output_tokens"]) / 1e6


def category(rec, answer):
    if not answer:
        return "none"
    name = answer[0] if isinstance(answer, list) else answer
    m = rec["mystery"]
    return "correct" if name == m["culprit"] else "RH" if name == m["red_herring"] else "OA"


def agent_turns(a):
    """Split an agent's conversation into practice and main turns: [{prompt, reply, reasoning}]."""
    turns, practice, prompt, k, main = [], [], None, 0, False
    for msg in a["messages"]:
        if msg["role"] == "user":
            if "**The main HIT.**" in msg["content"]:
                main = True
            prompt = msg["content"] if prompt is None else prompt + "\n\n" + msg["content"]
        elif msg["role"] == "assistant":
            reasoning = (a.get("reasoning") or [None] * (k + 1))[k]
            try:
                reply = json.loads(msg["content"])
            except json.JSONDecodeError:
                reply = {"raw": msg["content"]}
            (turns if main else practice).append({"prompt": prompt, "reply": reply, "reasoning": reasoning})
            prompt, k = None, k + 1
    return practice, turns


def layout(network, nodes=tuple(networks.NODES)):
    """Node coordinates in a 300 x 300 box."""
    import math

    def ring(nodes, r, phase=-90):
        return {n: (150 + r * math.cos(math.radians(phase + 360 * i / len(nodes))),
                    150 + r * math.sin(math.radians(phase + 360 * i / len(nodes)))) for i, n in enumerate(nodes)}

    if network == "HubAndSpoke":
        return {1: (150, 150), **ring(range(2, 10), 115)}
    if network in ("CorePeriphery", "OutCorePeriphery", "InCorePeriphery"):
        return {**ring((1, 2, 3), 45), **ring(range(4, 10), 125, -60)}
    if network == "LocallyClustered":
        pos = {}
        for centre, group in zip(ring((0, 1, 2), 85).values(), ((1, 2, 3), (4, 5, 6), (7, 8, 9))):
            for i, n in enumerate(group):
                pos[n] = (centre[0] + 35 * math.cos(math.radians(90 + 120 * i)), centre[1] + 35 * math.sin(math.radians(90 + 120 * i)))
        return pos
    core = networks.core(network)
    if core and network in networks.COUNTERFACTUALS:
        return {**ring(core, 45), **ring([n for n in nodes if n not in core], 125, -60)}
    return ring(list(nodes), 115)


def build(rec):
    nodes = [int(n) for n in rec["players"]]
    snaps = rec.get("snapshots", [])
    view = {
        "title": f"{rec['network']} trial {rec['trial']}", "network": rec["network"], "status": rec["status"],
        "model": rec["model"], "effort": rec.get("reasoning_effort"), "summary": rec.get("reasoning_summary"),
        "mystery": rec["mystery"], "outcome": rec.get("outcome"), "earnings": rec.get("earnings"),
        "edges": rec["edges"], "pos": {str(k): v for k, v in layout(rec["network"], [int(n) for n in rec["players"]]).items()},
        "players": rec["players"], "positions": {str(k): v for k, v in rec["positions"].items()},
        "messages": rec.get("messages", []), "events": rec.get("events", []), "agents": {}, "switches": [],
        "error": rec.get("error"), "mixed": bool(rec.get("effort_mix")),
    }
    usage_total = {"input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0, "calls": 0}
    for n in nodes:
        a = rec["agents"][str(n)]
        practice, turns = agent_turns(a)
        cells = []
        for t, s in enumerate(snaps):
            ans = s["murderer"].get(str(n))
            cells.append({"cat": category(rec, ans), "answer": ans})
        view["agents"][str(n)] = {"player": a["player"], "effort": (rec.get("efforts") or {}).get(str(n)),
                                  "persona": (rec.get("personas") or {}).get(str(n)), "practice": practice, "turns": turns, "cells": cells,
                                  "usage": a["usage"], "failures": a["failures"],
                                  "practice_passed": (rec.get("practice") or {}).get(str(n), {}).get("passed")}
        for k in usage_total:
            usage_total[k] += a["usage"].get(k, 0)
    view["usage"], view["cost"] = usage_total, cost(usage_total)
    # Switches into or out of the correct answer, with what the agent could see at the start of that turn.
    for row in rec.get("answers", []):
        if row["question"] != "murderer":
            continue
        n, t = row["node"], row["seconds"] // TICK - 1
        before = snaps[t - 1]["murderer"].get(str(n)) if t > 0 else None
        if (category(rec, before) == "correct") == (row["category"] == "correct"):
            continue
        visible = []
        for s in networks.sources(rec["network"], n):
            seen = snaps[t - 1]["murderer"].get(str(s)) if t > 0 else None
            visible.append({"player": rec["players"][str(s)], "cat": category(rec, seen), "answer": seen})
        view["switches"].append({"node": n, "tick": t, "seconds": row["seconds"], "to": row["answer"],
                                 "cat": row["category"], "visible": visible})
    return view


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fbfaf8;--panel:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--correct:#2f8f5b;--rh:#c8553d;--oa:#7d8bb0;--none:#ecebe7;--accent:#3c6fd1;--code:#f3f2ee}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--panel:#1d1d20;--ink:#ecebe7;--muted:#9a9aa0;--line:#2e2e33;--correct:#4cb37a;--rh:#e07a5f;--oa:#8e9bc4;--none:#2a2a2e;--accent:#7aa2f7;--code:#26262a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,system-ui,Segoe UI,sans-serif}
main{max-width:1200px;margin:0 auto;padding:20px 16px 60px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}
a{color:var(--accent)}.muted{color:var(--muted)}.row{display:flex;gap:20px;flex-wrap:wrap}.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}
.facts{flex:1;min-width:280px}.facts td{padding:2px 10px 2px 0;vertical-align:top}
svg text{fill:var(--ink);font-size:10px}.grid{overflow-x:auto}
table.g{border-collapse:separate;border-spacing:2px}table.g td{width:22px;height:22px;border-radius:4px;cursor:pointer;padding:0}
table.g td.lab{width:auto;cursor:default;padding-right:8px;white-space:nowrap;font-size:13px}table.g th{font-weight:400;font-size:10px;color:var(--muted)}
td.correct{background:var(--correct)}td.RH{background:var(--rh)}td.OA{background:var(--oa)}td.none{background:var(--none)}
td.sel{outline:2px solid var(--accent);outline-offset:1px}td.phase{border-left:3px solid var(--muted)}
.legend span{display:inline-block;width:12px;height:12px;border-radius:3px;margin:0 4px 0 12px;vertical-align:-1px}
.detail{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media (max-width:800px){.detail{grid-template-columns:1fr}}
pre{white-space:pre-wrap;word-wrap:break-word;background:var(--code);padding:10px;border-radius:8px;margin:6px 0;font:12px/1.45 ui-monospace,Menlo,monospace;max-height:520px;overflow:auto}
.lbl{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-top:10px}
table.list{border-collapse:collapse;width:100%}table.list td,table.list th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}
.pill{display:inline-block;padding:0 7px;border-radius:9px;font-size:12px;color:#fff}.pill.correct{background:var(--correct)}.pill.RH{background:var(--rh)}.pill.OA{background:var(--oa)}.pill.none{background:var(--muted)}
button{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:3px 10px;cursor:pointer}
</style></head><body><main>
<h1 id="title"></h1><div class="muted" id="sub"></div>
<div class="row" style="margin-top:14px"><div class="card"><svg id="net" width="300" height="300" viewBox="0 0 300 300"></svg></div>
<div class="card facts"><table id="facts"></table></div></div>
<h2>Murderer answer per turn</h2>
<div class="muted legend">Click a cell to see that turn. Thick lines mark minute 5 and minute 10.<span style="background:var(--correct)"></span>correct<span style="background:var(--rh)"></span>red herring<span style="background:var(--oa)"></span>other<span style="background:var(--none)"></span>none</div>
<div class="card grid" style="margin-top:8px"><table class="g" id="grid"></table></div>
<div class="card" style="margin-top:14px" id="detail"><span class="muted">Select a cell above.</span></div>
<h2>Switches to and from the correct answer</h2><div class="card"><table class="list" id="switches"></table></div>
<h2>Messages</h2><div class="card"><table class="list" id="messages"></table></div>
</main>
<script>
const V = __DATA__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const md = s => esc(s).replace(/\\*\\*(.+?)\\*\\*/g, "<b>$1</b>");
const clock = s => Math.floor(s/60) + ":" + String(s%60).padStart(2, "0");
const name = n => V.players[n];
const ans = a => a ? `${esc(a[0])} (${a[1]}%)` : "none";
const pill = (cat, text) => `<span class="pill ${cat}">${esc(text)}</span>`;
const short = cat => ({correct:"correct", RH:"red herring", OA:"other", none:"none"})[cat];

$("title").textContent = V.title;
$("sub").textContent = `${V.model}, effort ${V.mixed ? "mixed" : V.effort ?? "n/a"}, reasoning summaries ${V.summary ?? "off"} · status ${V.status}` + (V.error ? ` · ${V.error}` : "");
const o = V.outcome || {};
const facts = [
  ["Correct at the end", o.num_correct != null ? `${o.num_correct} of ${Object.keys(V.players).length}` : "n/a"],
  ["Culprit / red herring", `${esc(V.mystery.culprit)} / ${esc(V.mystery.red_herring)}`],
  ["Victim", esc(V.mystery.victim)],
  ["Murder weapon", esc(V.mystery.names.weapon_gun)],
  ["Messages", o.messages != null ? `${o.messages} (${o.text_messages} with text, ${o.shares} shares, ${o.replies} replies, ${o.forwards} forwards)` : "n/a"],
  ["Searches", o.searches ?? "n/a"],
  ["Calls / tokens", `${V.usage.calls} calls, ${V.usage.input_tokens.toLocaleString()} input (${V.usage.cached_tokens.toLocaleString()} cached), ${V.usage.output_tokens.toLocaleString()} output (${V.usage.reasoning_tokens.toLocaleString()} reasoning)`],
  ["Cost", "$" + V.cost.toFixed(3)],
];
$("facts").innerHTML = facts.map(([k, v]) => `<tr><td class="muted">${k}</td><td>${v}</td></tr>`).join("");

// network
const nodes = Object.keys(V.players).map(Number);
const final = n => { const c = V.agents[n].cells; return c.length ? c[c.length - 1].cat : "none"; };
const has = new Set(V.edges.map(([i, j]) => i + "-" + j));
let svg = `<defs><marker id="arr" viewBox="0 0 10 10" refX="19" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0L10,5L0,10z" fill="var(--muted)"/></marker></defs>`;
for (const [i, j] of V.edges) {
  const two = has.has(j + "-" + i);
  if (two && i > j) continue;
  const [x1, y1] = V.pos[i], [x2, y2] = V.pos[j];
  svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="var(--muted)" stroke-opacity=".55" ${two ? "" : 'marker-end="url(#arr)"'}/>`;
}
for (const n of nodes) {
  const [x, y] = V.pos[n];
  svg += `<g style="cursor:pointer" onclick="pick(${n}, null)"><circle cx="${x}" cy="${y}" r="12" fill="var(--${final(n) === "none" ? "none" : final(n).toLowerCase()})" stroke="var(--panel)" stroke-width="2"/><text x="${x}" y="${y + 3.5}" text-anchor="middle" style="fill:#fff;font-weight:600">${n}</text><text x="${x}" y="${y + 25}" text-anchor="middle">${esc(name(n))}</text></g>`;
}
$("net").innerHTML = svg;

// grid
const ticks = Math.max(...nodes.map(n => V.agents[n].cells.length), 0);
let g = "<tr><th></th>" + Array.from({length: ticks}, (_, t) => `<th>${t % 2 ? "" : clock((t + 1) * 30)}</th>`).join("") + "</tr>";
for (const n of nodes) {
  const A = V.agents[n];
  const prac = A.practice_passed == null ? "" : A.practice_passed ? " ✓" : " ✗";
  g += `<tr><td class="lab">${n} ${esc(A.player)} <span class="muted">${esc(V.positions[n])}${A.effort && V.mixed ? " · " + esc(A.effort) : ""}${prac}</span></td>` +
    A.cells.map((c, t) => `<td id="c${n}-${t}" class="${c.cat}${t === 10 || t === 20 ? " phase" : ""}" title="${esc(A.player)} at ${clock((t + 1) * 30)}: ${c.answer ? esc(c.answer[0]) + " " + c.answer[1] + "%" : "none"}" onclick="pick(${n}, ${t})"></td>`).join("") + "</tr>";
}
$("grid").innerHTML = g;

function actions(r) {
  if (r.raw) return `<pre>${esc(r.raw)}</pre>`;
  const out = [];
  if (r.open_messages) out.push("Opened unread messages");
  if (r.scribble) out.push("Scribbled: " + esc(r.scribble));
  if (r.searches && r.searches.length) out.push("Searched: " + r.searches.map(esc).join(", "));
  for (const m of r.messages || []) out.push(`Message to ${m.to.map(esc).join(", ") || "nobody"}: "${esc(m.text)}"` +
    (m.share_clues.length ? ` sharing ${m.share_clues.map(esc).join(", ")}` : "") + (m.reply_to ? ` (reply to ${esc(m.reply_to)})` : "") + (m.forward ? ` (forward ${esc(m.forward)})` : ""));
  if (r.victim) out.push("Victim answer: " + esc(r.victim));
  if (r.murderer) out.push(`Murderer answer: ${esc(r.murderer.name)} (${r.murderer.confidence}%)`);
  return out.length ? "<ul>" + out.map(x => `<li>${x}</li>`).join("") + "</ul>" : '<p class="muted">Did nothing.</p>';
}

function turnView(title, turn) {
  return `<h3 style="margin:0 0 6px">${title}</h3><div class="detail"><div><div class="lbl">What the agent saw</div><pre>${md(turn.prompt)}</pre></div><div>` +
    `<div class="lbl">Reasoning summary</div>${turn.reasoning ? `<pre>${md(turn.reasoning)}</pre>` : '<p class="muted">Not recorded (run with --reasoning-summary).</p>'}` +
    `<div class="lbl">Private notes</div><pre>${esc(turn.reply.notes ?? "")}</pre><div class="lbl">Actions</div>${actions(turn.reply)}</div></div>`;
}

let cur = null;
function pick(n, t) {
  const A = V.agents[n];
  if (t === null) t = 0;
  document.querySelectorAll("td.sel").forEach(e => e.classList.remove("sel"));
  const cell = $(`c${n}-${t}`); if (cell) cell.classList.add("sel");
  cur = [n, t];
  const turn = A.turns[t];
  const nav = `<div style="margin-bottom:10px"><button onclick="step(-1)">← previous turn</button> <button onclick="step(1)">next turn →</button> <span class="muted">${A.practice.length} practice turns: <a href="#" onclick="showPractice(${n});return false">show</a></span></div>`;
  const P = A.persona;
  const card = P ? `<div class="muted" style="margin-bottom:8px">Persona: ${P.age}, ${P.gender}, ${esc(P.education)}${P.student ? ", student" : ""}` +
    Object.entries(P).filter(([k, v]) => ["low", "high"].includes(v)).map(([k, v]) => ` · ${k.replace("_", " ")} ${v}`).join("") + "</div>" : "";
  $("detail").innerHTML = nav + card + (turn ? turnView(`${esc(A.player)} (node ${n}), turn ${t + 1}, ${clock(t * 30)} to ${clock((t + 1) * 30)}`, turn) : '<p class="muted">No turn recorded.</p>');
}
function step(d) { if (!cur) return; const [n, t] = cur; const T = V.agents[n].turns.length; pick(n, Math.max(0, Math.min(T - 1, t + d))); }
function showPractice(n) {
  const A = V.agents[n];
  $("detail").innerHTML = `<button onclick="pick(${n}, 0)">back to the main game</button>` + A.practice.map((p, i) => turnView(`${esc(A.player)}, practice turn ${i + 1}`, p)).join("<hr>");
}
document.addEventListener("keydown", e => { if (e.key === "ArrowRight") step(1); if (e.key === "ArrowLeft") step(-1); });

$("switches").innerHTML = V.switches.length ? "<tr><th>Time</th><th>Player</th><th>Switched to</th><th>Answers visible at the start of that turn</th></tr>" + V.switches.map(s =>
  `<tr><td>${clock(s.seconds)}</td><td><a href="#detail" onclick="pick(${s.node}, ${s.tick})">${esc(name(s.node))}</a></td><td>${pill(s.cat, s.to)}</td><td>${s.visible.length ? s.visible.map(v => `${esc(v.player)}: ${pill(v.cat, v.answer ? v.answer[0] : "none")}`).join(" ") : '<span class="muted">nobody</span>'}</td></tr>`).join("")
  : '<tr><td class="muted">No switches to or from the correct answer.</td></tr>';

$("messages").innerHTML = V.messages.length ? "<tr><th>Time</th><th>Id</th><th>From</th><th>To</th><th>Kind</th><th>Content</th></tr>" + V.messages.map(m =>
  `<tr><td>${clock(m.seconds)}</td><td>${m.id}</td><td>${esc(name(m.sender))}</td><td>${m.to.map(name).map(esc).join(", ")}</td><td>${m.kind}</td><td>${esc(m.text)}${m.clues.length ? ` <span class="muted">[${m.clues.join(", ")}]</span>` : ""}${m.reply_to ? ` <span class="muted">re ${m.reply_to}</span>` : ""}${m.forward ? ` <span class="muted">fwd ${m.forward}</span>` : ""}</td></tr>`).join("")
  : '<tr><td class="muted">No messages.</td></tr>';
</script></body></html>
"""

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>__TITLE__</title>
<style>:root{--bg:#fbfaf8;--panel:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#e3e1dc;--accent:#3c6fd1}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--panel:#1d1d20;--ink:#ecebe7;--muted:#9a9aa0;--line:#2e2e33;--accent:#7aa2f7}}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 -apple-system,system-ui,sans-serif}main{max-width:1000px;margin:0 auto;padding:20px 16px}
a{color:var(--accent)}table{border-collapse:collapse;width:100%;background:var(--panel)}td,th{border-bottom:1px solid var(--line);padding:6px 10px;text-align:left}
.muted{color:var(--muted)}.wrap{overflow-x:auto}</style></head><body><main><h1 style="font-size:22px">__TITLE__</h1><p class="muted">__SUB__</p>
<div class="wrap"><table><tr><th>Trial</th><th>Status</th><th>Correct</th><th>Messages</th><th>Searches</th><th>Practice passed</th><th>Cost</th></tr>__ROWS__</table></div></main></body></html>
"""


def write_trial(path, out_dir):
    rec = json.loads(Path(path).read_text())
    view = build(rec)
    data = json.dumps(view, ensure_ascii=False).replace("</", "<\\/")
    page = out_dir / (Path(path).stem + ".html")
    page.write_text(PAGE.replace("__TITLE__", html.escape(view["title"])).replace("__DATA__", data))
    o = view["outcome"] or {}
    passed = [a["practice_passed"] for a in view["agents"].values() if a["practice_passed"] is not None]
    return page, (f'<tr><td><a href="{page.name}">{html.escape(view["title"])}</a></td><td>{view["status"]}</td>'
                  f'<td>{o.get("num_correct", "")}</td><td>{o.get("messages", "")}</td><td>{o.get("searches", "")}</td>'
                  f'<td>{f"{sum(passed)} of {len(passed)}" if passed else ""}</td><td>${view["cost"]:.3f}</td></tr>'), view["cost"]


def main():
    target = Path(sys.argv[1])
    files = [target] if target.is_file() else sorted(p for p in target.glob("*.json") if p.name != "config.json")
    out_dir = (target.parent if target.is_file() else target) / "view"
    out_dir.mkdir(exist_ok=True)
    rows, total = [], 0
    for f in files:
        page, row, c = write_trial(f, out_dir)
        rows.append(row)
        total += c
        print(page)
    if target.is_dir():
        title = f"Run {target.name}"
        (out_dir / "index.html").write_text(INDEX.replace("__TITLE__", html.escape(title))
                                            .replace("__SUB__", f"{len(files)} trials, total cost ${total:.2f}").replace("__ROWS__", "\n".join(rows)))
        print(out_dir / "index.html")


if __name__ == "__main__":
    main()
