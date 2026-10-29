/* Networks of Agents: prototype site. Plain JS + SVG, data from data/summary.js and data/trials.js. */
const S = window.SUMMARY, T = window.TRIALS;
const NS = "http://www.w3.org/2000/svg";
const COL = ["var(--c0)", "var(--c1)", "var(--c2)", "var(--c3)"];
const CAT = ["No answer", "Correct", "Red herring", "Other suspect"];
const mean = a => a.reduce((s, v) => s + v, 0) / a.length;
const pct = v => `${Math.round(v * 100)}%`;
const mmss = s => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const surname = n => n.split(" ").slice(-1)[0];

function svg(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function el(tag, attrs = {}, html = "") {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? (e.className = v) : e.setAttribute(k, v);
  if (html) e.innerHTML = html;
  return e;
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const tip = document.getElementById("tip");
function showTip(ev, html) { tip.innerHTML = html; tip.hidden = false; moveTip(ev); }
function moveTip(ev) { tip.style.left = Math.min(ev.clientX + 14, innerWidth - 290) + "px"; tip.style.top = ev.clientY + 14 + "px"; }
function hideTip() { tip.hidden = true; }
function hover(node, html) {
  node.addEventListener("mouseenter", e => showTip(e, typeof html === "function" ? html() : html));
  node.addEventListener("mousemove", moveTip);
  node.addEventListener("mouseleave", hideTip);
}

const NAMES = {
  HubAndSpoke: "Hub and spoke", CorePeriphery: "Core-periphery", OutCorePeriphery: "Out core-periphery",
  InCorePeriphery: "In core-periphery", LocallyClustered: "Locally clustered", CompleteClique: "Complete clique",
  OutCP_up0: "0 upward ties", OutCP_up6: "6 upward ties", OutCP_core1: "Core 1", OutCP_core2: "Core 2", OutCP_core4: "Core 4",
  OutCP_per3: "Periphery 3", OutCP_per9: "Periphery 9", OutStar: "Star",
  InCP_down0: "0 downward ties", InCP_down6: "6 downward ties", InCP_core1: "Core 1", InCP_core2: "Core 2", InCP_core4: "Core 4",
  InCP_per3: "Periphery 3", InCP_per9: "Periphery 9", InStar: "Star",
};
const fullName = n => n.startsWith("OutCP_") || n === "OutStar" ? `Out core-periphery, ${NAMES[n].toLowerCase()}`
  : n.startsWith("InCP_") || n === "InStar" ? `In core-periphery, ${NAMES[n].toLowerCase()}` : NAMES[n];
const ABOUT = {
  HubAndSpoke: "One hub is connected in both directions to eight spokes; spokes are not connected to each other.",
  CorePeriphery: "Three fully connected core nodes, each connected in both directions to all six peripheral nodes.",
  OutCorePeriphery: "Edges run from each core node to all peripheral nodes; three peripheral nodes have an edge to one core node each.",
  InCorePeriphery: "Edges run from all peripheral nodes to the core; each core node has an edge to one peripheral node.",
  LocallyClustered: "Three fully connected clusters of three nodes, linked by bridging edges.",
  CompleteClique: "All nodes are connected in both directions.",
};
const describeCF = n => {
  const s = S.structures[n], out = n.startsWith("Out");
  return `${s.core.length} core and ${s.nodes.length - s.core.length} peripheral nodes, ${s.edges.length} directed edges. ${out ? "Core nodes send to the periphery" : "Peripheral nodes send to the core"}.`;
};

// Core nodes sit on a small inner ring in the viewer layout; spread them out so labels and arrows stay readable.
const POS = {};
function posOf(net) {
  if (POS[net]) return POS[net];
  const st = S.structures[net], out = {};
  for (const [n, [x, y]] of Object.entries(st.pos)) {
    const f = st.core.includes(+n) ? 1.55 : 1;
    out[n] = [150 + (x - 150) * f, 150 + (y - 150) * f];
  }
  return (POS[net] = out);
}

/* ---------------- hero ---------------- */
const P = S.paper, PAPER = Object.keys(P);
const allH = PAPER.flatMap(n => P[n].humans), allA = PAPER.flatMap(n => P[n].agents);
const cfCore = S.counterfactuals;


/* ---------------- paper vs agents chart ---------------- */
(function paperChart() {
  const order = ["HubAndSpoke", "CorePeriphery", "InCorePeriphery", "CompleteClique", "LocallyClustered", "OutCorePeriphery"];
  const W = 1000, H = 330, L = 44, R = 12, B = 44, top = 16, ymax = 6;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}` }, document.getElementById("chart-paper"));
  const y = v => top + (H - top - B) * (1 - v / ymax), gw = (W - L - R) / order.length, bw = gw * 0.3;
  for (let v = 0; v <= ymax; v++) {
    svg("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: v ? "#ecebe5" : "#c3c2b7" }, s);
    svg("text", { x: L - 10, y: y(v) + 4, "text-anchor": "end", "font-size": 16, fill: "#898781" }, s).textContent = v;
  }
  const iso = [[mean(S.isolates.humans), "#bdbcb4"], [mean(S.isolates.agents), "#3f3e3a"]];
  for (const [v, c] of iso) svg("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: c, "stroke-dasharray": "5 4", "stroke-width": 1.5 }, s);
  order.forEach((n, i) => {
    const cx = L + gw * i + gw / 2;
    [["humans", "#bdbcb4", -1], ["agents", "#3f3e3a", 1]].forEach(([who, c, side]) => {
      const vals = P[n][who], m = mean(vals), x = cx + side * (bw / 2 + 2) - bw / 2;
      const r = svg("path", { d: barPath(x, y(m), bw, y(0) - y(m), 4), fill: c }, s);
      hover(r, `<b>${NAMES[n]}</b><br>${who === "humans" ? "Humans" : "Agents"}: mean ${m.toFixed(2)} of 9 correct<br>${vals.length} trials; 0 to 1 correct in ${pct(vals.filter(v => v <= 1).length / vals.length)} of trials`);
      svg("text", { x: x + bw / 2, y: y(m) - 6, "text-anchor": "middle", "font-size": 16, fill: "#0b0b0b", "font-weight": 500 }, s).textContent = m.toFixed(1);
    });
    svg("text", { x: cx, y: H - 16, "text-anchor": "middle", "font-size": 17, fill: "#52514e" }, s).textContent = NAMES[n];
  });
  document.getElementById("iso-key").textContent = `Isolates (dashed): humans ${iso[0][0].toFixed(1)}, agents ${iso[1][0].toFixed(1)}`;
})();
function barPath(x, y0, w, h, r) {
  r = Math.min(r, h, w / 2);
  return `M${x},${y0 + h}V${y0 + r}Q${x},${y0} ${x + r},${y0}H${x + w - r}Q${x + w},${y0} ${x + w},${y0 + r}V${y0 + h}Z`;
}

(function hypotheses() {
  const share = (a, f) => pct(a.filter(f).length / a.length);
  const lo = v => v <= 1, hi = v => v > 6;
  const fol = S.follow.agents, core = S.outcp_core.agents, cp = S.copy.agents;
  const rows = [
    ["Fewer trials with 0 to 1 correct", `hub ${share(P.HubAndSpoke.humans, lo)}, CP ${share(P.CorePeriphery.humans, lo)}`, `hub ${share(P.HubAndSpoke.agents, lo)}, CP ${share(P.CorePeriphery.agents, lo)}`, "partly", "H1"],
    ["More trials with more than 6 correct", `hub ${share(P.HubAndSpoke.humans, hi)}, CP ${share(P.CorePeriphery.humans, hi)}`, `hub ${share(P.HubAndSpoke.agents, hi)}, CP ${share(P.CorePeriphery.agents, hi)}`, "partly", "H2"],
    ["Centralized networks outperform decentralized ones", `+${S.contrast.humans.toFixed(2)}`, `+${S.contrast.agents.toFixed(2)} (p = 0.43)`, "no", "H3"],
    ["One-way centralization yields no advantage", `out CP ${mean(P.OutCorePeriphery.humans).toFixed(2)}, worst`, `out CP ${mean(P.OutCorePeriphery.agents).toFixed(1)}, worst`, "yes", "H4"],
    ["Spokes adopt the hub's correct answer", pct(S.follow.humans), `${pct(fol[0] / fol[1])} (${fol[0]} of ${fol[1]})`, "no", "Mechanism"],
  ];
  const box = document.getElementById("hyp"), label = { yes: "Replicated", no: "Not replicated", partly: "Partly replicated" };
  for (const [t, h, a, v, k] of rows)
    box.appendChild(el("div", { class: "h" }, `<div class="muted small">${k}</div><div class="t">${t}</div><div class="vals"><span>Humans</span><b>${h}</b><span>Agents</span><b>${a}</b></div>`));
  document.getElementById("calibration").innerHTML = `
    <table><tr><th>Setting</th><th>Implementation</th></tr>
    <tr><td>One search per 30-second turn, repeat searches allowed</td><td>One random matching clue per search, as on the original platform</td></tr>
    <tr><td>Mixed reasoning effort (low, medium, high)</td><td>Each agent gets one effort level at random</td></tr>
    <tr><td>Messages cost time</td><td>Writing takes 3 s plus 1.5 s per word out of the 30-second turn</td></tr>
    <tr><td>Persona cards</td><td>Age, gender, education, and Big Five traits drawn to match MTurk samples, plus susceptibility to influence</td></tr>
    <tr><td>Limited memory with a notepad</td><td>Agents see only their last 3 turns, plus a notepad of up to 15 words per turn</td></tr>
    <tr><td>Neutral payment wording</td><td>No instruction to enter an answer early</td></tr></table>
    <p>Isolates, mean correct of 9: agents ${mean(S.isolates.agents).toFixed(1)}, humans ${mean(S.isolates.humans).toFixed(2)}.</p>`;
})();

/* ---------------- game player ---------------- */
const byNet = {};
for (const t of T) if (!t.pilot) (byNet[t.network] ||= []).push(t);
for (const n in byNet) byNet[n].sort((a, b) => a.trial - b.trial);
const findTrial = id => T.find(t => t.id === id);
function representative(net) {
  const ts = byNet[net], f = ts.find(t => t.featured);
  if (f) return f;
  const med = [...ts].map(t => t.num_correct).sort((a, b) => a - b)[Math.floor(ts.length / 2)];
  return ts.find(t => t.num_correct === med);
}

const state = { trial: null, k: 29, sel: null, playing: false, timer: null, mode: null };
const gsvg = document.getElementById("graph"), scrub = document.getElementById("scrub");

const PICKS = {
  game: [["Original treatments", ["HubAndSpoke", "CorePeriphery", "LocallyClustered", "CompleteClique", "OutCorePeriphery", "InCorePeriphery"]]],
  "cf-game": [
    ["Out core-periphery", ["OutCorePeriphery", "OutCP_up0", "OutCP_up6", "OutCP_core1", "OutCP_core2", "OutCP_core4", "OutCP_per3", "OutCP_per9", "OutStar"]],
    ["In core-periphery", ["InCorePeriphery", "InCP_down0", "InCP_down6", "InCP_core1", "InCP_core2", "InCP_core4", "InCP_per3", "InCP_per9", "InStar"]],
  ],
};
const DEFAULT = { game: "OutCorePeriphery", "cf-game": "InCP_down0" };
const last = {};
function buildPicker(mode) {
  const box = document.getElementById("picker");
  box.innerHTML = "";
  for (const [g, nets] of PICKS[mode]) {
    const row = el("div", { class: "prow" });
    row.appendChild(el("span", { class: "grp" }, g));
    for (const n of nets) {
      const b = el("button", { class: "chip", "data-net": n }, mode === "cf-game" && PAPER.includes(n) ? "Original" : NAMES[n]);
      b.onclick = () => loadTrial(representative(n));
      row.appendChild(b);
    }
    box.appendChild(row);
  }
}
// One player, moved between the two replay tabs; each tab remembers its last trial.
function mountPlayer(mode) {
  const slot = document.querySelector(`#${mode} .slot`), block = document.getElementById("player-block");
  if (state.mode === mode && slot.contains(block)) return;
  if (state.mode && state.trial) last[state.mode] = state.trial;
  slot.appendChild(block);
  state.mode = mode;
  buildPicker(mode);
  loadTrial(last[mode] || representative(DEFAULT[mode]));
}

document.getElementById("trial-select").onchange = e => loadTrial(findTrial(e.target.value));
scrub.oninput = () => { stop(); setK(+scrub.value, false); };
document.getElementById("play").onclick = () => state.playing ? stop() : play();

function play() {
  if (state.k >= 29) setK(0, false);
  state.playing = true;
  document.getElementById("play").innerHTML = "&#10074;&#10074;";
  state.timer = setInterval(() => { if (state.k >= 29) return stop(); setK(state.k + 1, true); }, 900);
}
function stop() {
  state.playing = false;
  clearInterval(state.timer);
  document.getElementById("play").innerHTML = "&#9654;";
}

const DETAIL = {};
function detail(t) {
  if (!DETAIL[t.file]) DETAIL[t.file] = fetch("data/trials/" + t.file).then(r => r.json()).then(d => (DETAIL[t.file] = d));
  return DETAIL[t.file] instanceof Promise ? DETAIL[t.file] : Promise.resolve(DETAIL[t.file]);
}

function loadTrial(t, opts = {}) {
  stop();
  state.trial = t;
  state.sel = opts.node ?? null;
  document.querySelectorAll(".chip").forEach(c => c.classList.toggle("on", c.dataset.net === t.network && !t.pilot));
  const sel = document.getElementById("trial-select");
  sel.innerHTML = "";
  const list = t.pilot ? [t] : byNet[t.network];
  for (const x of list) sel.appendChild(el("option", { value: x.id }, `${x.pilot ? "Pilot" : x.trial}`));
  sel.value = t.id;
  document.getElementById("g-title").textContent = fullName(t.network);
  document.getElementById("g-sub").textContent = t.pilot ? "pilot without time costs for messages" : "";
  document.getElementById("g-note").textContent = (ABOUT[t.network] || describeCF(t.network)) +
    ` Murderer: ${t.culprit}. Red herring: ${t.red_herring}.` + (t.pilot ? " Pilot trial run before time costs for messages were introduced." : "");
  drawGraph(t);
  drawArea(t);
  setK(opts.k ?? 29, false);
  detail(t).then(() => { if (state.trial === t) render(); });
}

function drawGraph(t) {
  gsvg.innerHTML = "";
  const st = S.structures[t.network], pos = posOf(t.network), R = t.nodes.length > 10 ? 12 : 14;
  const defs = svg("defs", {}, gsvg);
  const mk = svg("marker", { id: "arr", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
  svg("path", { d: "M0,1L9,5L0,9z", fill: "#a9a89e" }, mk);
  const es = new Set(st.edges.map(e => e.join("-")));
  state.edgeEls = {};
  for (const [i, j] of st.edges) {
    const [x1, y1] = pos[i], [x2, y2] = pos[j], dx = x2 - x1, dy = y2 - y1, d = Math.hypot(dx, dy);
    const ux = dx / d, uy = dy / d, both = es.has(`${j}-${i}`);
    if (both && i > j) { state.edgeEls[`${i}-${j}`] = state.edgeEls[`${j}-${i}`]; continue; } // drawn once, as a two-headed line
    const s0 = both ? R + 3 : R;
    const p = svg("path", { class: "edge", d: `M${x1 + ux * s0},${y1 + uy * s0}L${x2 - ux * (R + 3)},${y2 - uy * (R + 3)}`, "marker-end": "url(#arr)", ...(both ? { "marker-start": "url(#arr)" } : {}) }, gsvg);
    state.edgeEls[`${i}-${j}`] = p;
  }
  state.pulseLayer = svg("g", {}, gsvg);
  state.nodeEls = {};
  t.nodes.forEach((n, idx) => {
    const [x, y] = pos[n], g = svg("g", { class: "node", transform: `translate(${x},${y})` }, gsvg);
    svg("circle", { class: "ring", r: R + 4 }, g);
    const c = svg("circle", { class: "body", r: R }, g);
    const conf = svg("text", { class: "conf", y: 3 }, g);
    const [lx, ly, anchor] = labelSpot(n, st.edges, pos, st.core.includes(n) ? R + 4 : R);
    svg("text", { x: lx, y: ly, class: "lab", "text-anchor": anchor }, g).textContent = t.names[idx];
    if (st.core.includes(n)) svg("circle", { class: "core-mark", r: R + 1.5 }, g);
    c.onclick = () => { state.sel = state.sel === n ? null : n; render(); };
    hover(c, () => {
      const a = t.turns[state.k][idx];
      return `<b>${t.names[idx]}</b>${st.core.includes(n) ? " (core)" : ""}<br>${a ? `${t.suspects[a[0]]}, ${a[1]}% sure<br>${CAT[a[2]]}` : "No answer yet"}`;
    });
    state.nodeEls[n] = { g, c, conf };
  });
}

// Put a node's name on the side with the most room between its own edges, so it does not sit on an arrow.
function labelSpot(n, edges, pos, R) {
  const [x0, y0] = pos[n], dirs = [];
  for (const [i, j] of edges) {
    const m = i === n ? j : j === n ? i : null;
    if (m != null) dirs.push(Math.atan2(pos[m][1] - y0, pos[m][0] - x0));
  }
  const gap = a => dirs.length ? Math.min(...dirs.map(d => { const v = Math.abs(a - d) % (2 * Math.PI); return Math.min(v, 2 * Math.PI - v); })) : Math.PI;
  let best = Math.PI / 2, score = -1;
  for (let k = 0; k < 16; k++) {
    const a = k * Math.PI / 8, sc = gap(a) + (Math.sin(a) > 0.9 ? 0.05 : 0); // slight preference for below
    if (sc > score + 1e-9) { score = sc; best = a; }
  }
  const c = Math.cos(best), s = Math.sin(best), anchor = c > 0.35 ? "start" : c < -0.35 ? "end" : "middle";
  // Text baseline sits at y; glyphs reach about 7 units above it.
  const x = anchor === "middle" ? 0 : c * (R + 7) + (c > 0 ? 2 : -2);
  const y = anchor === "middle" ? (s > 0 ? R + 12 : -R - 6) : s > 0.35 ? s * (R + 7) + 7 : s < -0.35 ? s * (R + 7) - 1 : 3;
  return [x, y, anchor];
}

function drawArea(t) {
  const box = document.getElementById("area");
  box.innerHTML = "";
  const W = 520, H = 66, n = t.nodes.length, s = svg("svg", { viewBox: `0 0 ${W} ${H}` }, box);
  const x = k => 4 + (W - 8) * k / 29, y = v => 6 + (H - 22) * (1 - v / n);
  const counts = t.turns.map(row => [1, 2, 3, 0].map(c => row.filter(a => (a ? a[2] : 0) === c).length));
  let base = counts.map(() => 0);
  [1, 2, 3, 0].forEach((c, ci) => {
    const top = base.map((b, k) => b + counts[k][ci]);
    const d = top.map((v, k) => `${k ? "L" : "M"}${x(k)},${y(v)}`).join("") + base.map((v, k) => `L${x(29 - k)},${y(base[29 - k])}`).join("") + "Z";
    svg("path", { d, fill: COL[c], opacity: c ? 0.9 : 0.6 }, s);
    base = top;
  });
  [0, 10, 20, 29].forEach(k => svg("text", { x: x(k), y: H - 1, "font-size": 12, fill: "#898781", "text-anchor": k ? (k === 29 ? "end" : "middle") : "start" }, s).textContent = mmss((k + 1) * 30 - (k === 29 ? 0 : 0)));
  state.cursor = svg("line", { y1: 2, y2: H - 14, stroke: "#0b0b0b", "stroke-width": 1.5 }, s);
  const hit = svg("rect", { x: 0, y: 0, width: W, height: H, fill: "transparent" }, s);
  const kAt = ev => { const r = s.getBoundingClientRect(); return Math.max(0, Math.min(29, Math.round((ev.clientX - r.left) / r.width * 29))); };
  hit.addEventListener("click", ev => { stop(); setK(kAt(ev), false); });
  hit.addEventListener("mousemove", ev => {
    const k = kAt(ev), c = counts[k];
    showTip(ev, `<b>${mmss((k + 1) * 30)}</b><br>Correct ${c[0]} · Red herring ${c[1]} · Other ${c[2]} · None ${c[3]}`);
  });
  hit.addEventListener("mouseleave", hideTip);
}

function setK(k, animate) {
  state.k = k;
  scrub.value = k;
  if (animate) pulses(k);
  render();
}

function pulses(k) {
  const t = state.trial, pos = posOf(t.network);
  for (const [sec, from, to] of t.messages) {
    if (sec !== (k + 1) * 30) continue;
    for (const r of to) {
      const [x1, y1] = pos[from], [x2, y2] = pos[r];
      const dot = svg("circle", { class: "pulse", r: 3.2, cx: x1, cy: y1 }, state.pulseLayer);
      const e = state.edgeEls[`${from}-${r}`];
      if (e) e.classList.add("hot");
      const t0 = performance.now();
      (function step(now) {
        const f = Math.min(1, (now - t0) / 700), q = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
        dot.setAttribute("cx", x1 + (x2 - x1) * q);
        dot.setAttribute("cy", y1 + (y2 - y1) * q);
        if (f < 1) requestAnimationFrame(step); else { dot.remove(); if (e) e.classList.remove("hot"); }
      })(t0);
    }
  }
}

function render() {
  const t = state.trial, k = state.k, st = S.structures[t.network];
  document.getElementById("clock").textContent = mmss((k + 1) * 30);
  t.nodes.forEach((n, idx) => {
    const a = t.turns[k][idx], e = state.nodeEls[n];
    e.c.setAttribute("fill", COL[a ? a[2] : 0]);
    e.conf.textContent = a ? a[1] : "";
    e.g.classList.toggle("sel", state.sel === n);
  });
  const W = 520;
  state.cursor.setAttribute("x1", 4 + (W - 8) * k / 29);
  state.cursor.setAttribute("x2", 4 + (W - 8) * k / 29);

  const side = document.getElementById("side");
  const fin = t.final, ok = fin.filter(f => f === "correct").length, rh = fin.filter(f => f === "RH").length;
  let h = `<div class="blk"><h4>Outcome of this trial</h4><div class="outcome"><div><b>${ok} of ${t.nodes.length}</b>correct</div><div><b>${rh}</b>on the red herring</div><div><b>${t.messages.length}</b>messages</div></div></div>`;
  h += `<div class="blk"><h4>Answers at ${mmss((k + 1) * 30)}</h4><table class="ptable">`;
  t.nodes.forEach((n, idx) => {
    const a = t.turns[k][idx];
    h += `<tr data-n="${n}" class="${state.sel === n ? "sel" : ""}"><td><i class="dot c${a ? a[2] : 0}"></i>${esc(t.names[idx])}${st.core.includes(n) ? ' <span class="muted">core</span>' : ""}</td><td>${a ? esc(surname(t.suspects[a[0]])) : '<span class="muted">none</span>'}</td><td class="num">${a ? a[1] + "%" : ""}</td></tr>`;
  });
  h += `</table></div>`;
  if (state.sel != null) {
    const idx = t.nodes.indexOf(state.sel);
    h += `<div class="blk"><h4>Answers of ${esc(t.names[idx])} by turn</h4><div class="strip">` +
      t.turns.map((row, j) => `<span data-k="${j}" class="${j === k ? "now" : ""}" style="background:${COL[row[idx] ? row[idx][2] : 0]}" title="${mmss((j + 1) * 30)}: ${row[idx] ? esc(t.suspects[row[idx][0]]) + ", " + row[idx][1] + "%" : "no answer"}"></span>`).join("") + `</div>`;
    const d = DETAIL[t.file], ag = d && !(d instanceof Promise) ? d.agents[state.sel] : null;
    if (ag) {
      const tu = ag.turns[k];
      h += `<div class="muted small">Persona: ${esc(ag.persona || "none")}. Reasoning effort: ${esc(ag.effort || "")}.</div>`;
      h += `<div class="note-box" style="margin-top:10px"><div class="who">Turn starting ${mmss(k * 30)}${tu.search ? ` · search "${esc(tu.search)}"${tu.clue ? " → " + tu.clue : ""}` : ""}</div>${esc(tu.notes) || "<span class='muted'>(no notes)</span>"}${tu.notepad ? `<div class="who" style="margin-top:6px">Notepad</div>${esc(tu.notepad)}` : ""}${tu.clue ? `<div class="who" style="margin-top:6px">${tu.clue}</div>${esc(d.clues[tu.clue])}` : ""}</div>`;
    } else h += `<div class="muted small" style="margin-top:8px">Loading notes…</div>`;
    h += `</div>`;
  }
  const msgs = t.messages.filter(m => m[0] === (k + 1) * 30 && (state.sel == null || m[1] === state.sel || m[2].includes(state.sel)));
  h += `<div class="blk"><h4>Messages this turn${state.sel != null ? " to or from " + esc(t.names[t.nodes.indexOf(state.sel)]) : ""}</h4><div class="msgs">`;
  h += msgs.length ? msgs.map(([, f, to, text, nc]) => `<div class="msg"><div class="m-h">${esc(t.names[t.nodes.indexOf(f)])} to ${to.length > 3 ? to.length + " players" : to.map(r => esc(t.names[t.nodes.indexOf(r)])).join(", ")}${nc ? ` · ${nc} clue${nc > 1 ? "s" : ""} shared` : ""}</div>${text ? esc(text) : '<span class="muted">(clues only)</span>'}</div>`).join("") : '<div class="muted small">None.</div>';
  h += `</div></div>`;
  side.innerHTML = h;
  side.querySelectorAll("tr[data-n]").forEach(r => r.onclick = () => { const n = +r.dataset.n; state.sel = state.sel === n ? null : n; render(); });
  side.querySelectorAll(".strip span").forEach(s => s.onclick = () => { stop(); setK(+s.dataset.k, false); });
}

function goTo(id, node, k, tab) {
  const t = findTrial(id), mode = tab || (PAPER.includes(t.network) || t.pilot ? "game" : "cf-game");
  history.pushState(null, "", "#" + mode);
  showTab(mode);
  loadTrial(t, { node, k });
}

/* ---------------- counterfactuals ---------------- */
function miniGraph(net, coreColor) {
  const st = S.structures[net], pos = posOf(net), s = svg("svg", { viewBox: "-20 -20 340 340" });
  const es = new Set(st.edges.map(e => e.join("-")));
  const defs = svg("defs", {}, s), id = "m" + net;
  const mk = svg("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse" }, defs);
  svg("path", { d: "M0,1L9,5L0,9z", fill: "#a9a89e" }, mk);
  for (const [i, j] of st.edges) {
    const [x1, y1] = pos[i], [x2, y2] = pos[j], d = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / d, uy = (y2 - y1) / d;
    const both = es.has(`${j}-${i}`);
    if (both && i > j) continue;
    svg("path", { d: `M${x1 + ux * (both ? 18 : 15)},${y1 + uy * (both ? 18 : 15)}L${x2 - ux * 18},${y2 - uy * 18}`, stroke: "#b9b8ae", "stroke-width": 1.4, "marker-end": `url(#${id})`, ...(both ? { "marker-start": `url(#${id})` } : {}) }, s);
  }
  for (const n of st.nodes) svg("circle", { cx: pos[n][0], cy: pos[n][1], r: 14, fill: st.core.includes(n) ? coreColor : "#d9d8d2", stroke: "#fff", "stroke-width": 2.5 }, s);
  return s;
}

(function spotlight() {
  const box = document.getElementById("spot"), base = cfCore.InCorePeriphery, d0 = cfCore.InCP_down0;
  for (const [net, cap, v, c] of [["InCorePeriphery", "Original structure (3 downward ties)", base.core[0], "#bdbcb4"], ["InCP_down0", "Variant without downward ties", d0.core[0], "#3f3e3a"]]) {
    const m = el("div", { class: "mini" });
    m.appendChild(miniGraph(net, c));
    m.appendChild(el("div", { class: "num" }, pct(v)));
    m.appendChild(el("div", { class: "cap" }, `${cap}<br><span class="muted">core agents correct at the end (20 trials)</span>`));
    box.appendChild(m);
  }
  const p = v => v < 0.001 ? "&lt; 0.001" : v.toFixed(3);
  box.appendChild(el("div", { class: "say" }, `
    <table class="spot-t"><tr><th></th><th>Original</th><th>Variant</th><th>p</th></tr>
    <tr><td>Core correct</td><td>${pct(base.core[0])}</td><td>${pct(d0.core[0])}</td><td>${p(d0.p_core)}</td></tr>
    <tr><td>All correct</td><td>${pct(base.share[0])}</td><td>${pct(d0.share[0])}</td><td>${p(d0.p_share)}</td></tr>
    </table>
    <p class="muted small">In core-periphery, 20 trials per structure. Permutation tests against the original structure.</p>
    <p><button class="linkbtn" id="spot-go">Open a trial with 0 downward ties</button></p>`));
  document.getElementById("spot-go").onclick = () => {
    const best = [...byNet.InCP_down0].sort((a, b) => b.num_correct - a.num_correct)[0];
    goTo(best.id, null, 29, "cf-game");
  };
})();

const SERIES = {
  Out: [["Original structure", ["OutCorePeriphery"]], ["Upward ties", ["OutCP_up0", "OutCP_up6"]], ["Core size", ["OutCP_core1", "OutCP_core2", "OutCP_core4"]], ["Periphery size", ["OutCP_per3", "OutCP_per9"]], ["Star", ["OutStar"]]],
  In: [["Original structure", ["InCorePeriphery"]], ["Downward ties", ["InCP_down0", "InCP_down6"]], ["Core size", ["InCP_core1", "InCP_core2", "InCP_core4"]], ["Periphery size", ["InCP_per3", "InCP_per9"]], ["Star", ["InStar"]]],
};
const rowLabel = n => ({ OutCorePeriphery: "Original", InCorePeriphery: "Original" }[n] || NAMES[n]);
let metric = "share";
function drawCF() {
  for (const d of ["Out", "In"]) {
    const box = document.getElementById("cf-" + d.toLowerCase());
    box.innerHTML = `<h3 style="margin:8px 0 4px">${d} core-periphery</h3>`;
    const rows = [];
    let y = 22;
    for (const [g, nets] of SERIES[d]) { rows.push({ g, y }); y += 20; for (const n of nets) { rows.push({ n, y }); y += 28; } y += 6; }
    const W = 520, L = 175, R = 80, H = y + 28, x = v => L + (W - L - R) * v;
    const s = svg("svg", { viewBox: `0 0 ${W} ${H}` }, box), base = cfCore[SERIES[d][0][1][0]][metric];
    for (const v of [0, 0.25, 0.5, 0.75, 1]) {
      svg("line", { x1: x(v), x2: x(v), y1: 10, y2: H - 20, stroke: "#ecebe5" }, s);
      svg("text", { x: x(v), y: H - 6, "text-anchor": "middle", "font-size": 14, fill: "#898781" }, s).textContent = pct(v);
    }
    svg("rect", { x: x(base[1]), width: x(base[2]) - x(base[1]), y: 10, height: H - 30, fill: "#3f3e3a", opacity: 0.07 }, s);
    svg("line", { x1: x(base[0]), x2: x(base[0]), y1: 10, y2: H - 20, stroke: "#3f3e3a", "stroke-dasharray": "4 3" }, s);
    for (const r of rows) {
      if (r.g) { svg("text", { x: 0, y: r.y + 4, "font-size": 13, "font-weight": 600, fill: "#898781", "letter-spacing": "0.06em" }, s).textContent = r.g.toUpperCase(); continue; }
      const c = cfCore[r.n], [m, lo, hi] = c[metric], p = c["p_" + metric], isBase = p == null, sig = p != null && p < 0.05;
      const g = svg("g", { class: "row" }, s);
      svg("rect", { class: "hit", x: 0, y: r.y - 12, width: W, height: 24, fill: "transparent", rx: 6 }, g);
      svg("text", { x: 8, y: r.y + 4, "font-size": 16, fill: "#52514e" }, g).textContent = rowLabel(r.n);
      const col = isBase ? "#3f3e3a" : sig ? "#0b0b0b" : "#a3a29a";
      svg("line", { x1: x(lo), x2: x(hi), y1: r.y, y2: r.y, stroke: col, "stroke-width": 2, "stroke-linecap": "round" }, g);
      svg("circle", { cx: x(m), cy: r.y, r: 5.5, fill: col, stroke: "#fff", "stroke-width": 2 }, g);
      const t = svg("text", { x: x(hi) + 8, y: r.y + 4, "font-size": 15, fill: sig ? "#0b0b0b" : "#52514e", "font-weight": sig ? 700 : 400 }, g);
      t.textContent = pct(m) + (sig ? (p < 0.001 ? "  p<0.001" : `  p=${p.toFixed(3)}`) : "");
      hover(g, `<b>${fullName(r.n)}</b><br>${metric === "share" ? "All agents" : "Core agents"} correct: ${pct(m)} (95% CI ${pct(lo)} to ${pct(hi)})<br>${c.n} trials${isBase ? "" : `; vs original structure p = ${p < 0.001 ? "< 0.001" : p.toFixed(3)}`}<br><span style="opacity:.7">Select to open a trial</span>`);
      g.addEventListener("click", () => { hideTip(); goTo(representative(r.n).id, null, 29, "cf-game"); });
    }
  }
}
document.querySelectorAll("#metric button").forEach(b => b.onclick = () => {
  metric = b.dataset.k;
  document.querySelectorAll("#metric button").forEach(x => x.classList.toggle("on", x === b));
  drawCF();
});
drawCF();

function byRound(n) {
  const ts = byNet[n], share = t => t.num_correct / t.nodes.length;
  return [mean(ts.filter(t => t.trial <= 10).map(share)), mean(ts.filter(t => t.trial > 10).map(share))];
}
(function cfMore() {
  const H = S.humans_cp, c = cfCore;
  document.getElementById("cf-more").innerHTML = `
    <p><b>Humans and agents, original one-way structures</b> (humans 30 trials, agents 20 trials)</p>
    <table><tr><th>Network</th><th>All correct, humans</th><th>All correct, agents</th><th>Core correct, humans</th><th>Core correct, agents</th></tr>
    ${["OutCorePeriphery", "InCorePeriphery"].map(n => `<tr><td>${NAMES[n]}</td><td>${pct(H[n].share[0])}</td><td>${pct(c[n].share[0])}</td><td>${pct(H[n].core[0])}</td><td>${pct(c[n].core[0])}</td></tr>`).join("")}</table>
    <p><b>All correct by round</b> (trials 1 to 10, trials 11 to 20)</p>
    <table><tr><th>Structure</th><th>Trials 1 to 10</th><th>Trials 11 to 20</th></tr>
    ${Object.keys(c).sort().map(n => { const r = byRound(n); return `<tr><td>${fullName(n)}</td><td>${pct(r[0])}</td><td>${pct(r[1])}</td></tr>`; }).join("")}</table>
    <p><b>Statistics.</b> Shares per trial. 95% bootstrap confidence intervals. Two-sided permutation tests against the original structure, 20 trials per structure, no correction for multiple comparisons.</p>`;
  document.getElementById("method").innerHTML = `
    <table>
    <tr><td>Task</td><td>The murder mystery of the original study: 41 clues in two waves, broadcasts at 0, 5 and 10 minutes, 15 minutes divided into 30 turns of 30 seconds. The second wave changes which suspect is the murderer.</td></tr>
    <tr><td>Agents</td><td>gpt-6-luna via the OpenAI Responses API. In each turn an agent returns a structured action: search query, message, answers, and private notes.</td></tr>
    <tr><td>Final settings</td><td>One search per turn with repeat search, mixed reasoning effort, time costs for messages, persona cards including susceptibility to influence, memory of three turns with a 15-word notepad, neutral payment wording.</td></tr>
    <tr><td>Trials</td><td>${S.n_trials_all} trials across all calibration and final runs; this page includes the ${S.n_trials_site - 1} trials with the final settings and one pilot trial.</td></tr>
    <tr><td>Cost</td><td>$${S.cost.toFixed(0)} in API fees across all runs.</td></tr>
    </table>`;
})();

/* ---------------- raw data page ---------------- */
(function rawData() {
  const f = { ds: document.getElementById("f-ds"), net: document.getElementById("f-net"), out: document.getElementById("f-out"), q: document.getElementById("f-q") };
  const table = document.getElementById("d-table"), count = document.getElementById("d-count"), panel = document.getElementById("d-detail");
  const rh = t => t.final.filter(x => x === "RH").length;
  const cols = [["dataset", "Dataset", t => t.dataset], ["network", "Network", t => fullName(t.network)], ["trial", "Trial", t => t.pilot ? "pilot " + t.trial : t.trial],
    ["players", "Agents", t => t.nodes.length], ["correct", "Correct", t => t.num_correct], ["rh", "Red herring", rh],
    ["other", "Other / none", t => t.nodes.length - t.num_correct - rh(t)], ["messages", "Messages", t => t.messages.length], ["searches", "Searches", t => t.searches]];
  let sort = ["dataset", 1], rows = [], open = null;
  for (const d of ["Original treatments", "Counterfactual structures", "Pilot"]) f.ds.appendChild(el("option", { value: d }, d));
  function nets() {
    const keep = f.net.value;
    f.net.innerHTML = '<option value="">All networks</option>';
    [...new Set(T.filter(t => !f.ds.value || t.dataset === f.ds.value).map(t => t.network))].forEach(n => f.net.appendChild(el("option", { value: n }, fullName(n))));
    f.net.value = [...f.net.options].some(o => o.value === keep) ? keep : "";
  }
  const OUT = { "": () => true, all: t => t.num_correct === t.nodes.length, hi: t => t.num_correct / t.nodes.length > 0.66,
    lo: t => t.num_correct <= 1, rh: t => rh(t) >= t.nodes.length - 1 };
  function fill() {
    const q = f.q.value.trim().toLowerCase();
    rows = T.filter(t => (!f.ds.value || t.dataset === f.ds.value) && (!f.net.value || t.network === f.net.value) && OUT[f.out.value](t)
      && (!q || t.messages.some(m => m[3].toLowerCase().includes(q))));
    const [key, dir] = sort, get = cols.find(c => c[0] === key)[2];
    rows.sort((a, b) => { const x = get(a), y = get(b); return (x > y ? 1 : x < y ? -1 : a.trial - b.trial) * dir; });
    count.textContent = `${rows.length} of ${T.length} trials`;
    table.innerHTML = `<thead><tr>${cols.map(([k, l]) => `<th data-k="${k}">${l}${sort[0] === k ? (sort[1] > 0 ? " ▲" : " ▼") : ""}</th>`).join("")}</tr></thead><tbody>` +
      rows.map(t => `<tr data-id="${t.id}" class="${open === t.id ? "sel" : ""}">${cols.map(c => `<td>${esc(c[2](t))}</td>`).join("")}</tr>`).join("") + "</tbody>";
  }
  Object.values(f).forEach(x => x.addEventListener("input", () => { if (x === f.ds) nets(); fill(); }));
  table.onclick = e => {
    const th = e.target.closest("th");
    if (th) { sort = [th.dataset.k, sort[0] === th.dataset.k ? -sort[1] : 1]; return fill(); }
    const tr = e.target.closest("tr[data-id]");
    if (tr) { open = tr.dataset.id; fill(); show(findTrial(open)); }
  };
  document.getElementById("d-csv").onclick = () => {
    const lines = [cols.map(c => c[1]).join(",")].concat(rows.map(t => cols.map(c => `"${String(c[2](t)).replace(/"/g, '""')}"`).join(",")));
    save(new Blob([lines.join("\n")], { type: "text/csv" }), "trials.csv");
  };
  function save(blob, name) { const a = el("a", { href: URL.createObjectURL(blob), download: name }); a.click(); }
  async function show(t) {
    panel.hidden = false;
    panel.innerHTML = `<div class="muted small">Loading…</div>`;
    const d = await detail(t), q = f.q.value.trim().toLowerCase();
    const ids = Object.keys(d.agents);
    let h = `<div class="d-head"><div><h3>${esc(fullName(t.network))}, ${t.pilot ? "pilot " : ""}trial ${t.trial}</h3>
      <div class="muted small">${esc(t.dataset)} · victim ${esc(d.victim)} · murderer ${esc(d.culprit)} · red herring ${esc(d.red_herring)} · run ${esc(t.run)}</div></div>
      <div class="d-actions"><button class="linkbtn" id="d-open">Open in replay</button><button class="linkbtn" id="d-json">Download JSON</button></div></div>`;
    h += `<h4>Agents</h4><div class="scroll"><table class="dt"><tr><th>Node</th><th>Name</th><th>Position</th><th>Effort</th><th>Persona</th><th>Final answer</th><th>Searches</th><th>Messages sent</th></tr>` +
      ids.map(n => { const a = d.agents[n], last = [...a.turns].reverse().find(x => x.murderer); return `<tr data-n="${n}" class="clickable"><td>${n}</td><td>${esc(a.name)}</td><td>${esc(a.position)}</td><td>${esc(a.effort || "")}</td><td class="wrapcell">${esc(a.persona || "")}</td><td><i class="dot c${["none", "correct", "RH", "OA"].indexOf(a.final)}"></i>${last ? esc(last.murderer) + " " + last.confidence + "%" : "none"}</td><td>${a.turns.filter(x => x.search).length}</td><td>${d.messages.filter(m => m.sender === +n).length}</td></tr>`; }).join("") + `</table></div>`;
    h += `<div id="d-agent"></div>`;
    h += `<h4>Messages (${d.messages.length})</h4><div class="scroll"><table class="dt"><tr><th>Time</th><th>From</th><th>To</th><th>Clues</th><th>Text</th></tr>` +
      d.messages.map(m => `<tr class="${q && m.text.toLowerCase().includes(q) ? "hit" : ""}"><td>${mmss(m.seconds)}</td><td>${esc(d.agents[m.sender].name)}</td><td>${m.to.map(x => esc(d.agents[x].name)).join(", ")}</td><td>${m.clues.join(" ")}</td><td class="wrapcell">${esc(m.text) || '<span class="muted">(clues only)</span>'}</td></tr>`).join("") + `</table></div>`;
    h += `<h4>Broadcasts</h4><table class="dt">` + d.broadcasts.map(([s, tx]) => `<tr><td>${mmss(s)}</td><td class="wrapcell">${tx.map(esc).join(" ")}</td></tr>`).join("") + `</table>`;
    panel.innerHTML = h;
    panel.querySelector("#d-open").onclick = () => goTo(t.id, null, 29);
    panel.querySelector("#d-json").onclick = () => save(new Blob([JSON.stringify(d, null, 1)], { type: "application/json" }), t.file);
    panel.querySelectorAll("tr[data-n]").forEach(tr => tr.onclick = () => {
      panel.querySelectorAll("tr[data-n]").forEach(x => x.classList.toggle("sel", x === tr));
      const a = d.agents[tr.dataset.n];
      panel.querySelector("#d-agent").innerHTML = `<h4>Turns of ${esc(a.name)}</h4><div class="scroll"><table class="dt"><tr><th>Turn</th><th>Search</th><th>Clue found</th><th>Murderer</th><th>Notes</th><th>Notepad</th></tr>` +
        a.turns.map(x => `<tr><td>${mmss(x.t)}</td><td>${esc(x.search || "")}</td><td class="wrapcell">${x.clue ? `${x.clue}: ${esc(d.clues[x.clue])}` : ""}</td><td>${x.murderer ? esc(x.murderer) + " " + x.confidence + "%" : ""}</td><td class="wrapcell">${esc(x.notes)}</td><td class="wrapcell">${esc(x.notepad)}</td></tr>`).join("") + `</table></div>`;
    });
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  nets();
  fill();
})();

/* ---------------- tabs: one section per page, routed by the URL hash ---------------- */
const TABS = ["overview", "paper", "game", "counterfactuals", "cf-game", "data"];
function showTab(tab) {
  document.querySelectorAll("main > section").forEach(s => s.classList.toggle("active", s.id === tab));
  document.querySelectorAll(".toc a").forEach(a => a.classList.toggle("on", a.dataset.tab === tab));
  if (tab === "game" || tab === "cf-game") mountPlayer(tab); else stop();
  const video = document.getElementById("ov-video");
  if (tab !== "overview") video?.pause(); // stop the narration when leaving the page
  else if (video && video.readyState === 0) video.load(); // Safari may not load a video that was hidden at page load
}
function route() {
  showTab(TABS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "overview");
  scrollTo(0, 0);
}
addEventListener("hashchange", route);
addEventListener("popstate", route);
// Tab links change the URL without the browser's jump to the section id, which would hide the page top under the tab bar.
document.querySelectorAll(".toc a, a.ov-link").forEach(a => a.addEventListener("click", e => {
  e.preventDefault();
  history.pushState(null, "", a.getAttribute("href"));
  route();
}));
addEventListener("load", () => setTimeout(() => scrollTo(0, 0), 0)); // the browser jumps to the section id on load
route();
