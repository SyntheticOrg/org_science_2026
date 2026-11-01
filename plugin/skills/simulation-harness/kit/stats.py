"""Statistics for group-level comparisons (standard library only).

Kit file of the synthetic-organisations plugin, from first-test/harness/analysis.py. The unit is the group: pass one
value per group, never one per message or round. Exact rank tests (as in the Brandts & Cooper replication) need scipy and
belong in the study's analysis when the source paper used them.
"""

import random
import statistics as st
from math import comb, sqrt


def wilson(k, n, z=1.96):
    """Wilson interval for k successes in n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (c - h, c + h)


def fisher_greater(k1, n1, k2, n2):
    """One-sided Fisher exact p for P(success | group 1) > P(success | group 2)."""
    K, N = k1 + k2, n1 + n2
    return sum(comb(K, x) * comb(N - K, n1 - x) for x in range(k1, min(K, n1) + 1)) / comb(N, n1)


def permutation_diff(a, b, reps=20000, seed=1):
    """Difference in means a - b and its two-sided label-permutation p."""
    obs = st.mean(a) - st.mean(b)
    pool, rng, hits = list(a) + list(b), random.Random(seed), 0
    for _ in range(reps):
        rng.shuffle(pool)
        hits += abs(st.mean(pool[: len(a)]) - st.mean(pool[len(a):])) >= abs(obs) - 1e-12
    return obs, (hits + 1) / (reps + 1)


def bootstrap_ci(groups, stat, reps=20000, seed=2, level=0.95):
    """Percentile interval of stat(*resampled groups), resampling the units within each list."""
    rng = random.Random(seed)
    d = sorted(stat(*[rng.choices(g, k=len(g)) for g in groups]) for _ in range(reps))
    tail = (1 - level) / 2
    return d[int(tail * reps)], d[int((1 - tail) * reps) - 1]


def extreme_share(values, low, high):
    """Share of groups at either bound: all-or-nothing group outcomes (module C2)."""
    return sum(v in (low, high) for v in values) / len(values)
