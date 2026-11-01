# Results: 20261020-100851-pilot, 20261020-110221-pilot2-market

## Outcomes

| Institution | Manipulation | Triads complete | Mean B votes (0–3) | Before interaction | Unanimous | Majority | Human mean | Human unanimous |
|---|---|---|---|---|---|---|---|---|
| discussion | control | 3 of 3 | 3.00 | 1.00 | 3/3 (0.44 to 1.00) | 3/3 (0.44 to 1.00) | 2.27 | 8/15 |
| market | control | 6 of 6 | 1.33 | 1.00 | 2/6 (0.10 to 0.70) | 2/6 (0.10 to 0.70) | 1.27 | 1/15 |

Vote distribution (triads with 0/1/2/3 B votes):

- discussion control: [0, 0, 0, 3]
- market control: [2, 2, 0, 2]

## Experiment 1: discussion > market in the control condition (unit = triad)

- Mean B votes difference: 1.67, bootstrap 95% CI 0.67 to 2.67, one-sided permutation p = 0.1157
- Unanimous: Fisher one-sided p = 0.1190
- Majority: Fisher one-sided p = 0.1190

## Market spreads (ECU; negative = more buying)

Mean over periods and markets, agents vs humans (Data B):

| Manipulation | A | B | C | Human A | Human B | Human C |
|---|---|---|---|---|---|---|
| control | -426.1 | -299.7 | 264.0 | 89.3 | -69.5 | 112.9 |

Control markets by period:

| Period | B (agents) | A and C (agents) | B (humans) | A and C (humans) |
|---|---|---|---|---|
| 1 | -452.0 | -54.3 | 17.1 | 103.2 |
| 2 | -386.8 | -46.7 | -15.8 | 122.6 |
| 3 | -304.2 | -79.2 | -75.4 | 108.0 |
| 4 | -128.3 | 55.2 | 19.5 | 88.7 |
| 5 | -318.5 | -95.9 | 43.1 | 79.0 |
| 6 | -418.5 | -90.7 | -117.0 | 124.0 |
| 7 | -94.3 | -92.2 | -155.3 | 90.4 |
| 8 | -333.5 | -152.8 | -204.1 | 120.2 |
| 9 | -258.2 | -159.8 | -121.9 | 116.1 |
| 10 | -302.7 | -94.4 | -88.3 | 58.7 |

Trades per market (10 periods):

- control: mean 79.2, range 64–94

## Failures and usage

| Institution | Manipulation | Failed triads | Quiz failed | Invalid rankings | Invalid market actions | Calls | Cache hit | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| discussion | control | 0 | 0 | 0 | 0 | 72 | 38% | 0.01 |
| market | control | 0 | 0 | 0 | 26 | 1854 | 96% | 0.82 |

Cost uses list prices for uncached input, cached input, and output; cache-write charges are not included.
