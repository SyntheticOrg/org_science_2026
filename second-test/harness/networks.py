"""Network treatments (Figure 5, Appendix E). Nodes 1-9; an edge (i, j) means j sees i's answer and can receive
clues and messages from i. Position labels follow the authors' replication code (CNCopencode.R)."""

NODES = range(1, 10)
CORE = (1, 2, 3)
PERIPHERY = tuple(range(4, 10))


def _both(pairs):
    return {e for i, j in pairs for e in ((i, j), (j, i))}


def _clique(nodes):
    return {(i, j) for i in nodes for j in nodes if i != j}


_CP_CORE_TO_PERI = {(c, p) for c in CORE for p in PERIPHERY}
_OUT_CP = _clique(CORE) | _CP_CORE_TO_PERI | {(4, 1), (6, 2), (8, 3)}

EDGES = {
    "HubAndSpoke": _both((1, p) for p in range(2, 10)),
    "CorePeriphery": _clique(CORE) | _both(_CP_CORE_TO_PERI),
    "OutCorePeriphery": _OUT_CP,
    "InCorePeriphery": {(j, i) for i, j in _OUT_CP},
    "LocallyClustered": _clique((1, 2, 3)) | _clique((4, 5, 6)) | _clique((7, 8, 9))
                        | _both([(2, 6), (3, 8), (5, 9)]) | {(1, 7), (7, 4), (4, 1)},
    "CompleteClique": _clique(NODES),
    "Empty": set(),  # calibration only: nine independent players
}

# The paper's six run treatments; isolates are resampled from InCorePeriphery nodes 5, 7 and 9 at analysis time.
TREATMENTS = ("HubAndSpoke", "CorePeriphery", "OutCorePeriphery", "InCorePeriphery", "LocallyClustered", "CompleteClique")
ISOLATE_SOURCE = ("InCorePeriphery", (5, 7, 9))

POSITIONS = {
    "HubAndSpoke": {1: "C1core", **{n: "C1peri" for n in range(2, 10)}},
    "CorePeriphery": {**{n: "CBcore" for n in CORE}, **{n: "CBperi" for n in PERIPHERY}},
    "OutCorePeriphery": {**{n: "COcore" for n in CORE}, **{n: "COperi" for n in PERIPHERY}},
    "InCorePeriphery": {**{n: "CIcore" for n in CORE}, **{n: "CIperi1" for n in (4, 6, 8)},
                        **{n: "CIperi0" for n in (5, 7, 9)}},
    "LocallyClustered": {n: "SW" for n in NODES},
    "CompleteClique": {n: "nineClique" for n in NODES},
    "Empty": {n: "isolate" for n in NODES},
}


# --- counterfactual core-periphery structures (not in the paper) -----------------------------------------------
# Core nodes 1..c (fully connected both ways), periphery c+1..c+p. "Out": every core node sends to every peripheral
# node, plus ties back up; "In": the same edges reversed. Back ties up follow the paper's pattern spread evenly:
# core node k+1 hears from peripheral node P[k * p // c] ("one per core node"; with c=3, p=6 that is 4->1, 6->2,
# 8->3 as in the paper), or every peripheral node P[i] reaches core node i * c // p + 1 ("all").


def core_periphery(c, p, back="one_per_core", direction="out"):
    core, peri = list(range(1, c + 1)), list(range(c + 1, c + p + 1))
    edges = _clique(core) | {(i, j) for i in core for j in peri}
    if back == "one_per_core":
        edges |= {(peri[k * p // c], k + 1) for k in range(c)}
    elif back == "all":
        edges |= {(peri[i], i * c // p + 1) for i in range(p)}
    else:
        assert back == "none", back
    return edges if direction == "out" else {(j, i) for i, j in edges}


def star(direction="out"):
    """Core 1-3 fully connected; each core node sends only to its own two peripheral nodes (1: 4, 5; 2: 6, 7;
    3: 8, 9), plus the paper's ties back up 4->1, 6->2, 8->3. "In" reverses every edge."""
    edges = _clique(CORE) | {(k, 4 + 2 * (k - 1) + d) for k in CORE for d in (0, 1)} | {(4, 1), (6, 2), (8, 3)}
    return edges if direction == "out" else {(j, i) for i, j in edges}


COUNTERFACTUALS = {  # name -> (edges, core size, periphery size)
    "OutCP_up0": (core_periphery(3, 6, "none"), 3, 6),
    "OutCP_up6": (core_periphery(3, 6, "all"), 3, 6),
    "InCP_down0": (core_periphery(3, 6, "none", "in"), 3, 6),
    "InCP_down6": (core_periphery(3, 6, "all", "in"), 3, 6),
    **{f"{d.title()}CP_core{c}": (core_periphery(c, 6, direction=d), c, 6) for d in ("out", "in") for c in (1, 2, 4)},
    **{f"{d.title()}CP_per{p}": (core_periphery(3, p, direction=d), 3, p) for d in ("out", "in") for p in (3, 9)},
    "OutStar": (star("out"), 3, 6),
    "InStar": (star("in"), 3, 6),
}
for _name, (_edges, _c, _p) in COUNTERFACTUALS.items():
    EDGES[_name] = _edges
    POSITIONS[_name] = {n: "core" if n <= _c else "periphery" for n in range(1, _c + _p + 1)}


def nodes(network):
    """The players of a network: 1-9 for the paper's treatments, 1..core+periphery for the counterfactuals."""
    if network in COUNTERFACTUALS:
        _, c, p = COUNTERFACTUALS[network]
        return range(1, c + p + 1)
    return NODES


def core(network):
    """Core nodes of a core-periphery structure (the paper's or a counterfactual), else ()."""
    if network in COUNTERFACTUALS:
        return tuple(range(1, COUNTERFACTUALS[network][1] + 1))
    return CORE if "CorePeriphery" in network else ()


def sources(network, node):
    """Nodes whose answers and messages this node can see (people it follows)."""
    return sorted(i for i, j in EDGES[network] if j == node)


def targets(network, node):
    """Nodes that see this node (its followers): the only people it can send messages to."""
    return sorted(j for i, j in EDGES[network] if i == node)
