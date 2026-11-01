# Results: 20261020-115514-main

## Outcomes

| Institution | Manipulation | Triads complete | Mean B votes (0–3) | Before interaction | Unanimous | Majority | Human mean | Human unanimous |
|---|---|---|---|---|---|---|---|---|
| discussion | control | 50 of 50 | 3.00 | 1.02 | 50/50 (0.93 to 1.00) | 50/50 (0.93 to 1.00) | 2.27 | 8/15 |
| market | control | 50 of 50 | 2.06 | 1.00 | 30/50 (0.46 to 0.72) | 35/50 (0.56 to 0.81) | 1.27 | 1/15 |

Vote distribution (triads with 0/1/2/3 B votes):

- discussion control: [0, 0, 0, 50]
- market control: [12, 3, 5, 30]

## Experiment 1: discussion > market in the control condition (unit = triad)

- Mean B votes difference: 0.94, bootstrap 95% CI 0.58 to 1.30, one-sided permutation p = 0.0000
- Unanimous: Fisher one-sided p = 0.0000
- Majority: Fisher one-sided p = 0.0000

## Market spreads (ECU; negative = more buying)

Mean over periods and markets, agents vs humans (Data B):

| Manipulation | A | B | C | Human A | Human B | Human C |
|---|---|---|---|---|---|---|
| control | -129.6 | -348.2 | 94.5 | 89.3 | -69.5 | 112.9 |

Control markets by period:

| Period | B (agents) | A and C (agents) | B (humans) | A and C (humans) |
|---|---|---|---|---|
| 1 | -318.6 | -13.9 | 17.1 | 103.2 |
| 2 | -391.4 | -44.2 | -15.8 | 122.6 |
| 3 | -385.2 | -53.4 | -75.4 | 108.0 |
| 4 | -378.5 | -4.1 | 19.5 | 88.7 |
| 5 | -416.5 | -10.9 | 43.1 | 79.0 |
| 6 | -380.6 | -9.8 | -117.0 | 124.0 |
| 7 | -304.4 | 1.0 | -155.3 | 90.4 |
| 8 | -328.7 | -18.7 | -204.1 | 120.2 |
| 9 | -258.5 | 6.6 | -121.9 | 116.1 |
| 10 | -320.2 | -28.0 | -88.3 | 58.7 |

Trades per market (10 periods):

- control: mean 64.7, range 29–96

## Failures and usage

| Institution | Manipulation | Failed triads | Quiz failed | Invalid rankings | Invalid market actions | Calls | Cache hit | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| discussion | control | 0 | 0 | 0 | 0 | 1200 | 36% | 0.23 |
| market | control | 0 | 0 | 0 | 102 | 15450 | 96% | 7.54 |

Cost uses list prices for uncached input, cached input, and output; cache-write charges are not included.
