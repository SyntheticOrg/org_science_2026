# Results: 20261020-100851-pilot

## Outcomes

| Condition | Triads complete | Mean B votes (0–3) | Before interaction | Unanimous | Majority | Human mean | Human unanimous |
|---|---|---|---|---|---|---|---|
| discussion | 3 of 3 | 3.00 | 1.00 | 3/3 (0.44–1.00) | 3/3 (0.44–1.00) | 2.27 | 8/15 |
| market | 3 of 3 | 0.33 | 1.00 | 0/3 (0.00–0.56) | 0/3 (0.00–0.56) | 1.27 | 1/15 |

Vote distribution (triads with 0/1/2/3 B votes):

- discussion: [0, 0, 0, 3]
- market: [2, 1, 0, 0]

## Test (discussion > market, unit = triad)

- Mean B votes difference: 2.67, bootstrap 95% CI 2.00 to 3.00, one-sided permutation p = 0.0482
- Unanimous: Fisher one-sided p = 0.0500
- Majority: Fisher one-sided p = 0.0500

## Market spreads (mean per period, ECU; negative = more buying)

| Period | B (agents) | A and C (agents) | B (humans) | A and C (humans) |
|---|---|---|---|---|
| 1 | -666.7 | -100.0 | 17.1 | 103.2 |
| 2 | -466.7 | -100.0 | -15.8 | 122.6 |
| 3 | -199.7 | -133.5 | -75.4 | 108.0 |
| 4 | 0.0 | 33.3 | 19.5 | 88.7 |
| 5 | -133.3 | -200.0 | 43.1 | 79.0 |
| 6 | -400.0 | -200.0 | -117.0 | 124.0 |
| 7 | 0.0 | -233.3 | -155.3 | 90.4 |
| 8 | -200.0 | -333.3 | -204.1 | 120.2 |
| 9 | -133.3 | -433.3 | -121.9 | 116.1 |
| 10 | -266.7 | -233.3 | -88.3 | 58.7 |

Trades per market (10 periods): mean 82.3, range 77–89

## Failures and usage

| Condition | Failed triads | Quiz failed | Invalid rankings | Invalid market actions | Calls | Cache hit | Cost (USD) |
|---|---|---|---|---|---|---|---|
| discussion | 0 | 0 | 0 | 0 | 72 | 38% | 0.01 |
| market | 0 | 0 | 0 | 17 | 927 | 96% | 0.38 |

Cost uses list prices for uncached input, cached input, and output; cache-write charges are not included.
