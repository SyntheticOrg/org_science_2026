# Synthetic organizations: replications with LLM agents

Code, data, and a plugin for replicating organizational experiments with LLM agents. All agent runs use OpenAI `gpt-6-luna`. The approach is described in [GENERAL_IDEA.md](GENERAL_IDEA.md).

Website with results and trial replays for the network replication: https://orgscience2026.vercel.app

## Contents

| Path | Contents |
| --- | --- |
| `index.html`, `app.js`, `style.css`, `data/`, `media/` | The website (static, served from the repository root) |
| `plugin/` | `synthetic-organisations` plugin for Claude Code and Codex |
| `first-test/` | Replication of Maciejovsky and Budescu (2020), Study 1 |
| `second-test/` | Replication of Bernstein, Shore, and Jang (2023), with 16 counterfactual networks |
| `GENERAL_IDEA.md` | Research approach |

## Plugin

Skills for designing, checking, running, and interpreting synthetic replications and counterfactual studies:

- `study-map`, `setup-synthetic-organisations`: orientation and project setup
- `design-study`: study plan from a paper or research question (`templates/APPROACH.md`)
- `study-protocol`: methodological rules, reproducibility, and GUIDE-LLM reporting
- `validity-audit`: 18 modules on human-agent differences (A1 to A5 social behavior and disclosure, B1 to B7 memory, communication, and reasoning, C1 and C2 population variation, D1 to D4 measurement and model)
- `simulation-harness`: Python kit (`kit/`) for agents, chat, personas, coding, statistics, and runs, with worked examples from the three replications

`hooks/study_guard.py` blocks manual edits to run records and flags edits to frozen harness and plan files. Install in Claude Code:

```
/plugin marketplace add ./plugin
/plugin install synthetic-organisations@synthetic-organisations
```

Codex reads `plugin/.codex-plugin/plugin.json` and the local marketplace in `plugin/.agents/plugins/marketplace.json`. Offline checks: `python3 plugin/scripts/validate.py`.

## first-test: hidden profiles in groups and markets

Three agents pool distributed evidence on three job applicants, by discussion or in a double-auction market.

- Experiment 1 (controls): 3.00 correct votes per triad in discussion and 2.06 in the market, against 2.27 and 1.27 for humans. The ranking replicates.
- Experiment 2 (conflict-of-interest side payments): the interaction reverses. Buy incentives push markets to 0.10 to 0.14 correct votes; discussion stays at 2.96 to 3.00. Paid agents argue for their target but keep sharing their cues truthfully.
- Experiment 3 (side-payment size): pilots at £100 only.
- Incentive tests: individual disclosure diagnostics, hidden incentives in groups, and disclosure under private costs (`INCENTIVE_DIAGNOSTICS.md`, `GROUP_INCENTIVES.md`, `runs/sensitivity/`).

Specification in `APPROACH.md`, design overview in `overview.html`, results in `results.html` and `results/`. Raw runs in `runs/exp1/`, `runs/exp2/`, `runs/exp3/`, and `runs/sensitivity/`, one JSON file per triad.

## second-test: network centralization and adaptability

Groups of nine agents solve a murder mystery in 30 turns. Early clues point to a wrong suspect; later clues reveal the murderer. Six network treatments and isolates, as in the original study. Final runs: 10 trials per network, 10 more for the one-way core-periphery networks, 10 with isolates. Counterfactuals: 16 variants of the one-way core-periphery networks (core-periphery ties, core size, periphery size, star), 20 trials each.

Specification and calibration log in `APPROACH.md`, findings in `results/second-test-findings.pdf`, one row per trial in `results/trials_summary.csv`. Raw runs in `runs/`; calibration and pilot transcripts are not included but are summarized in the CSV.

## Third replication

The worked examples in `plugin/skills/simulation-harness/references/worked-examples.md` summarize a replication of Brandts and Cooper (2025). Its harness and runs are not included in this repository.

## Running

Python 3.12, standard library only (`second-test/harness/report.py` needs matplotlib). Put the API key in `.env` at the repository root as `OPENAI_API_KEY=...`.

```
cd first-test
python3 harness/test_core.py                         # checks, no API calls
python3 harness/runner.py --triads 1 --fake          # full pipeline with a scripted model
python3 harness/runner.py --triads 50 --workers 100  # experiment 1
python3 harness/runner.py --triads 50 --workers 400 --manipulations weak-buy weak-sell strong-buy strong-sell

cd second-test
python3 harness/fetch_data.py                        # the authors' replication data
python3 harness/test_core.py                         # checks
python3 harness/runner.py --trials 1 --fake --workers 6
python3 harness/runner.py --trials 10 --workers 20   # one run over all treatments
python3 harness/summary.py                           # results/trials_summary.csv
python3 harness/report.py                            # results/second-test-findings.pdf
```

New runs are written to `runs/<timestamp>/` in each test folder.
