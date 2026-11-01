# Second test: Bernstein, Shore & Jang (2023) with LLM agents

Replication target: Bernstein, Shore and Jang, "Network Centralization and Collective Adaptability to a Shifting Environment", *Organization Science* 34(6), 2064-2096. Nine participants per network solve a 15-minute murder mystery whose information shifts in three 5-minute phases. The outcome is the number of the nine with the correct answer at the end. The paper reports that centralised networks (hub-and-spoke, core-periphery) beat the decentralised controls, but only with two-way ties.

## Status

Calibration and pilots finished on 2026-10-21; the final run (personas with susceptibility, memory 3, 15-word notepad, plain pay wording) is the last one within budget. Its results are at the end of the calibration log. Nothing is committed yet.

## Files

| Path | Contents |
| --- | --- |
| `harness/task.py` | Clue sets (Appendix B.1 and B.3), name randomisation, the platform's search rule |
| `harness/networks.py` | The six treatments plus `Empty` for calibration, position labels as in the authors' code |
| `harness/engine.py` | One game: clock, search, messaging along ties, answers, what each player sees |
| `harness/agent.py` | Model adapter, adapted from `first-test/harness/agent.py` (copied, so first-test stays untouched) |
| `harness/instructions.md` | Agent instructions; verbatim passages from the paper where it quotes them |
| `harness/runner.py` | Practice stage, then 30 synchronous turns; one JSON record per trial |
| `harness/personas.py` | Persona cards drawn from the MTurk population (demographics, Big Five, susceptibility) |
| `harness/viewer.py` | HTML page per trial (network, answers per turn, what each agent saw, reasoning summary, notes, actions, switches, messages) and an index per run |
| `harness/summary.py` | One CSV row per trial of every run (settings and outcomes) |
| `harness/report.py` | The findings PDF, built from the summary table and the authors' data (needs matplotlib) |
| `harness/fetch_data.py` | Downloads the authors' replication package into `source/dataverse/` |
| `harness/test_core.py` | Checks, no API calls |
| `results/trials_summary.csv` | Every trial of all 31 runs (424 records): what the calibration log and the PDF are computed from |
| `results/second-test-findings.pdf` | Findings: four portrait pages of figures and tables |
| `runs/20261021-final-empty10/`, `runs/20261021-final-net10/` | Full records of the final run (isolates, then 10 trials per network) |
| `source/dataverse/` | The authors' replication package (doi:10.7910/DVN/X2HQXD); not in git, fetch with `harness/fetch_data.py` |

Only the final run's raw records are in git. The other 29 runs named in the calibration log (pilots, calibration, variants) are summarised trial by trial in `results/trials_summary.csv`; their full transcripts are kept outside the repository (see `.gitignore`).

## Running it

Python 3.12, standard library only. Run from `second-test/`:

```
python3 harness/test_core.py                                     # checks
python3 harness/runner.py --trials 1 --fake --workers 6          # one fake trial per treatment
python3 harness/runner.py --networks Empty --trials 10 --workers 10   # calibration
python3 harness/runner.py --trials 30 --workers 20               # main run, 6 x 30 trials
python3 harness/viewer.py runs/<run>                             # writes runs/<run>/view/index.html
python3 harness/fetch_data.py                                    # the authors' data, for test_core.py and report.py
python3 harness/summary.py                                       # results/trials_summary.csv from runs/
python3 harness/report.py                                        # results/second-test-findings.pdf (needs matplotlib)
```

Add `--reasoning-summary auto` (or `concise`, `detailed`) to any real run to save a summary of the model's reasoning with every call. The raw reasoning is never returned by the API; the summary is the model provider's paraphrase of it, so treat it as a description, not a transcript. Summaries are stored in each agent's `reasoning` list, one entry per reply, and are not fed back into the agent's context. The `notes` field in every reply is separate: it is what the agent itself chose to write down.

## Design

**Materials.** All 41 main-trial clues (26 searchable from the start, 15 from minute 5) and the three headquarters broadcasts (0, 5 and 10 minutes) are taken from Appendix B.3. Names, genders, cities, hotels, companies, event names and weapons are redrawn for every trial, as the authors did across versions. This also guards against the model having seen the published clue list. Times of day are fixed. Clue labels (C1 to C41) are shuffled so they do not reveal the phase.

**Search.** Follows the platform's `SearchController`: the query is split into words, the first word that matches a keyword wins, and one random matching clue is returned that is unlocked and that the player has not already found by search. The keyword list of the original is not public. Here a clue's keywords are the names in it: people's surnames, cities, hotels, companies, event words and weapon words. This is a departure to report.

**Networks.** Reconstructed from Appendix E and confirmed against the data: for every network and node, the number of visible alters in `solutions2.tab` matches (`test_networks_match_data`). Hub is node 1; the core is nodes 1 to 3. A tie i to j means j sees i's answers and receives i's messages, so a player can send only to the people who follow them (as in the platform's `PlayerController`). Isolates are not run: as in the paper they are resampled from in-core-periphery nodes 5, 7 and 9, which have no incoming ties.

**Time.** 15 minutes become 30 turns of 30 seconds. All nine agents act at once on the state at the start of a turn; actions take effect at the end of the turn and are seen at the start of the next. Per turn an agent may run up to 2 searches, send 1 message (to any subset of its followers, with text, shared clues, a reply or a forward), and enter or change its answers. Answer snapshots are taken every 30 seconds, the same grid as `solutions2.tab`.

**Answers and pay.** Two questions as in the original: the victim (attention check) and the murderer, with confidence (0 to 100). Agents are told the original pay rule: 40 cents base, 14 cents per minute with each correct answer entered.

**Practice.** Each agent first solves the stage 1 puzzle alone (6 turns, 3 minutes as in the paper) and keeps that history. Stage 2 (three-person social practice) is not run; the social features are explained in the instructions instead.

**Departures to report.** Discrete turns instead of continuous time; reconstructed keyword list; no stage 2 and no filtering on practice performance (pass or fail is recorded); no dropout (16% of human trials had some); times of day not randomised; homogeneous agents.

## Calibration (before the main run)

The main risk is that agents find the culprit in phase 2 too easily. Humans mostly held the red herring through phase 2 (under 10% correct), and the authors discarded an earlier version that was too easy. Calibrate only on `Empty` (no social influence), freeze the settings, then run the six treatments, so nothing is tuned on the outcome being tested. Targets from the human isolates: 3.19 of 9 correct at the end on average, and a red-herring majority during phase 2. Levers: model and reasoning effort, searches per turn, turn length. Humans sent 21.8 messages per trial (texts, replies and shares in `trialData.csv`); the fake model sends about 110, so message volume is a second calibration target once the network runs start.

## Cost estimate

Measured with the fake model: 306 calls per trial (9 agents x 30 turns, plus about 4 practice turns each), instruction prompts about 700 tokens, turn prompts about 160 tokens (up to about 380). Real agents write longer messages and notes, so assume about 250 tokens per turn prompt and 200 visible output tokens per call. The context then grows to about 15k tokens by the last turn; average input is about 8k tokens per call, about 2.5M per trial, of which about 95% is cached (first-test: 96%).

At gpt-6-luna list prices (USD per million tokens: 0.10 input, 0.01 cached input, 0.50 output, from `first-test/harness/analysis.py`):

| Item | Per trial | Main run (180 trials) |
| --- | --- | --- |
| Input, 2.5M tokens, 95% cached | $0.04 | $7 |
| Output, 306 calls x (200 visible + 500 to 1,500 reasoning) | $0.11 to $0.26 | $19 to $47 |
| **Total** | **$0.15 to $0.30** | **$26 to $54** |

Add calibration (a few rounds of 10 `Empty` trials, about $5 to $15) and reruns: about $50 to $100 in total. As a check, first-test cost $0.00047 per call at similar context length; 55,000 calls at that rate is $26, the low end of the range. Wall time: each trial is about 36 sequential rounds of calls, so roughly 10 to 20 minutes per trial; with 20 trials in parallel (180 concurrent calls) the main run takes about 2 to 3 hours if rate limits allow.

For comparison, the human study paid its 1,608 main-trial participants $3,131 in bonuses plus $0.40 base each (`individualData.tab`), about $3,800 before the two screening stages.

## Calibration log

Human benchmark over time: the `SyntheticIsolates` rows of `solutions2.tab` are mostly empty (about 6 of 9 "none" at minute 15, against 3.19 correct in `trialData.csv`), so timing is taken from the real isolates they are drawn from, in-core-periphery nodes 5, 7 and 9 (90 people), scaled to nine. The real network rows match `trialData.csv`.

| Minute | Human isolates | Pilot 1 | Pilot 2 |
| --- | --- | --- | --- |
| 5 | 6.8 none, 1.2 red herring, 1.0 other | 9 none | 7 none, 1 red herring, 1 other |
| 8 | 5.4 none, 2.0 red herring, 1.4 other, 0.2 correct | 9 none | 6 none, 1 red herring, 2 other |
| 10 | 4.2 none, 2.0 red herring, 2.1 other, 0.7 correct | 9 none | 5 none, 2 red herring, 1 other, 1 correct |
| 12.5 | 2.5 correct, 2.3 red herring, 2.0 other, 2.2 none | 5 correct, 4 none | 9 correct |
| 15 | 3.1 correct, 3.2 red herring, 1.9 other, 0.8 none | 9 correct | 9 correct |

- **Pilot 1** (2026-10-21, `runs/20261021-pilot1-empty`): gpt-6-luna, effort high, instructions as first written. No agent entered a murderer answer before minute 10.5; all nine were correct at the end. Agents treated an entered answer as a final verdict. $0.06.
- **Pilot 2** (`runs/20261021-pilot2-empty-early-answers`): same model. The payment text now says that an unentered answer earns nothing, so a best guess should be entered as soon as there is one and can be changed at no cost. The practice task no longer says to answer only when you know, and a player's own empty answer is shown as "not entered (earning nothing)". Phases 1 and 2 now look like the human isolates. Phase 3 does not: every agent deduced the culprit within a minute of the weapon clue, where a third of humans stayed on the red herring. $0.07.

- **Pilots 3 and 4** (`runs/20261021-pilot3-empty-medium`, `runs/20261021-pilot4-empty-low`): pilot 2 settings at reasoning effort medium and low. Reasoning fell from 218 tokens per call (high) to 119 (medium) and 24 (low), and cost from $0.07 to $0.05 and $0.03. Answers up to minute 10 were similar to pilot 2, slightly later. Phase 3 still went to all nine correct; at low effort two agents were still on the red herring at minute 12.5 but switched by the end. Effort is not what makes phase 3 easy.
- **Why phase 3 is easy:** with 2 searches per turn each agent found 29 to 38 of the 41 clues (9 to 13 of the 15 phase-2 clues) and keeps all of them in its context. Once the weapon is announced, the alibi clues it already holds settle the case. Humans, judging by their answers, did not have or did not combine that information.

- **Pilots 5 and 6** (`runs/20261021-pilot5-empty-s1-high`, `runs/20261021-pilot6-empty-s1-low`): pilot 2 settings with 1 search per turn instead of 2 (new `--searches` option), at effort high and low. Each agent now found 19 to 27 of the 41 clues and 5 to 10 of the 15 phase-2 clues. End of trial at high effort: 3 correct, 6 red herring (humans: 3.1 correct, 3.2 red herring, 1.9 other, 0.8 none). At low effort: 5 correct, 4 red herring. Finding the decisive alibi clue (the red herring seen at 7:50 pm) did not settle it: at high effort, 2 of the 3 agents who had it still ended on the red herring, and 2 of the 6 without it ended correct. Remaining gaps at high effort: no answers at all before minute 5 (humans: 2.2 of 9), and no "other" answers at the end. $0.05 per trial.

- **Pilots 7 to 9** (two trials each; trial 1 is the same mystery version as pilots 1 to 6, trial 2 a new one). New options: `--repeat-search` (a search can return a clue the player already found, the platform's `unique_factoids` setting off, which is the code's default; the paper does not say which setting was used) and `--effort-mix` (each agent's reasoning effort drawn independently from the listed levels). End of trial, out of nine:
  - Pilot 7, repeat search, 2 searches, high effort: 4 and 5 correct, 5 and 4 red herring. Agents enter answers early again (4 and 7 of 9 by minute 5, humans 2.2), with many red herrings by minute 10, as in the human data. Distinct clues found: 20 to 29, about as few as with 1 search per turn. The first attempt at trial 2 failed on an HTTP 520 from the API (now retried); the failed record is kept as `Empty-002-failed-http520.json`.
  - Pilot 8, 1 search, effort mixed (low, medium, high): 6 and 5 correct. Outcome follows the draw: low-effort agents ended mostly on the red herring (5 of 6), high-effort agents mostly correct (8 of 11).
  - Pilot 9, repeat search, 2 searches, effort mixed: 6 and 6 correct, 3 and 3 red herring. Further from the humans than either change alone.
  - No configuration produced "other" answers at the end (humans 1.9 of 9) or unanswered players (humans 0.8). Agents always narrow down to the two suspects the clues support. This looks like a difference in careless errors rather than in information, and is reported as a known difference rather than tuned away.

- **Calibration run** (`runs/20261021-calib10-empty-repeat-s1-mixed`, 10 trials, all complete, no failed calls, $0.39, 20 minutes): repeat search, 1 search per turn, effort drawn per agent from low, medium and high, current instructions. Against the 90 human isolate trials (`trialData.csv`):

  | | Agents (10 trials) | Humans (90 trials) |
  | --- | --- | --- |
  | Correct at the end, mean (sd) | 3.9 (1.6) | 3.19 (1.38) |
  | Median, range | 3.5, 2 to 7 | 3, 0 to 6 |
  | Trials with 0 or 1 correct | 0% | 10% |
  | Trials with more than 6 correct | 10% | 0% |

  Mean answers per trial of nine (humans from in-core-periphery nodes 5, 7 and 9):

  | Minute | Agents | Humans |
  | --- | --- | --- |
  | 5 | 7.6 none, 0.9 other, 0.5 red herring | 6.8 none, 1.2 red herring, 1.0 other |
  | 10 | 4.9 none, 2.3 red herring, 1.4 other, 0.4 correct | 4.2 none, 2.0 red herring, 2.1 other, 0.7 correct |
  | 15 | 4.3 red herring, 3.9 correct, 0.8 other | 3.2 red herring, 3.1 correct, 1.9 other, 0.8 none |

  The mean difference (0.7 correct, standard error about 0.5) is within noise for 10 trials. Phase 2 matches closely, including a red-herring majority among entered answers. Remaining differences: slightly fewer early answers, no unanswered players at the end, and fewer "other" answers (0.8 against 1.9), though no longer zero. Effort matters less than in pilot 8: correct at the end for 48% of high-effort agents, 50% of medium and 36% of low. Practice: 90 of 90 passed.

**Settings frozen** on 2026-10-21 after the calibration run, before any networked trial: `SEARCHES = 1`, `REPEAT_SEARCH = True`, `EFFORT_MIX = ("low", "medium", "high")` are the runner defaults.

- **Network pilot** (`runs/20261021-netpilot-1each`, one trial per treatment, all complete, $0.53). Agents are far too prosocial:

  | Network | Correct (humans) | Messages with text + replies (humans) | Answer changes matching a visible neighbour (humans) |
  | --- | --- | --- | --- |
  | Hub-and-spoke | 9 (4.7) | 255 (23.1) | 96% (59%) |
  | Core-periphery | 9 (4.4) | 261 (19.1) | 88% (68%) |
  | Out core-periphery | 9 (3.1) | 166 (10.5) | 97% (59%) |
  | In core-periphery | 7 (4.0) | 245 (15.3) | 82% (63%) |
  | Locally clustered | 9 (3.2) | 260 (17.7) | 93% (63%) |
  | Complete clique | 9 (3.5) | 256 (14.9) | 94% (75%) |

  Human figures are means over 30 trials (`trialData.csv`; the human matching share is from `solutions1.csv`, answer entries with at least one visible neighbour answer). Agents send a message on nearly every turn (the maximum is 270 per trial), open by announcing themselves and asking others to share, and then divide the work ("I'll investigate Myers/Foster now"); the hub in hub-and-spoke acts as a coordinator. Pooling the clues solves the mystery in every network, so the treatments cannot differ. Agents never shared a clue without adding text; humans did so about 5 times per trial.

- **Message pilots** (one trial per treatment each, all complete). New options: `--message-costs-time` (in a turn with a message containing the agent's own text, including a reply, no search runs; passing on clues or forwarding without text does not cost the search) and `--message-cap N` (at most N messages per player per game; N = 3 from the human mean of 2.5 per person, counting text messages, shares and replies in `individualData.tab`, set from message counts only). Messages per trial, all kinds (humans in brackets: text + shares + replies from `trialData.csv`):

  | Network | No limit | Messages cost time | Cap of 3 |
  | --- | --- | --- | --- |
  | Hub-and-spoke | 255, 9 correct | 33, 9 correct | 26, 7 correct |
  | Core-periphery | 261, 9 | 9, 9 | 27, 4 |
  | Out core-periphery | 166, 9 | 17, 8 | 17, 8 |
  | In core-periphery | 245, 7 | 37, 6 | 26, 9 |
  | Locally clustered | 260, 9 | 22, 2 | 27, 5 |
  | Complete clique | 256, 9 | 19, 0 | 27, 9 |

  Human messages per trial: 28, 25, 15, 20, 23 and 19 in the same order; human correct: 4.7, 4.4, 3.1, 4.0, 3.2, 3.5.
  - **Messages cost time** brings volume to the human level without a number chosen by us, and the mix becomes human-like: most messages now pass on clues without text (84 of 137), which humans also did; uncapped agents never did. Outcomes now differ between networks (0 to 9 correct). The cost is $0.30 for six trials.
  - **Cap of 3** also matches the totals, but every agent uses its full allowance, nearly all messages carry text, and none pass on clues alone. $0.31.
  - **Copying neighbours** stays above the human level under both (time cost: 85 to 98% of answer changes match a visible neighbour; cap: 71 to 93%; humans 59 to 75%). Part of this is convergence on the same answer from the same clues, but the human figure is measured the same way.
  - One trial per network: the differences between networks are not yet interpretable.

- **Inbox and time-budget pilots** (all 17 trials complete). New options: `--read-costs-time` (messages wait unread; opening them takes the turn, content shown next turn; run together with `--message-costs-time`) and `--time-budget` (30 seconds per turn; reading 238 words per minute from Brysbaert 2019, writing 1.5 seconds per word, search 5 seconds, sending 3 seconds, answer change 5 seconds; the last three are our estimates; reading is charged first and overflow carries into the next turn; per-turn limits do not apply). Correct of 9 per network, one trial each (messages per trial in brackets; humans: mean correct, messages):

  | Network | Humans | Writing costs time | + opening costs time | Time budget |
  | --- | --- | --- | --- | --- |
  | Hub-and-spoke | 4.7 (28) | 9 (33) | 0 (17) | 9 (22) |
  | Core-periphery | 4.4 (25) | 9 (9) | 0 (17) | 9 (11) |
  | In core-periphery | 4.0 (20) | 6 (37) | 6 (20) | 8 (25) |
  | Complete clique | 3.5 (19) | 0 (19) | 0 (24) | 8 (12) |
  | Locally clustered | 3.2 (23) | 2 (22) | 1 (19) | 7 (8) |
  | Out core-periphery | 3.1 (15) | 8 (17) | 9 (8) | 9 (8) |

  - **Opening costs time** keeps message volume at the human level, but outcomes stay all or nothing (five of six trials at 0, 1 or 9), now with hub-and-spoke and core-periphery stuck on the red herring. Slowing the flow of information does not stop groups from converging. $0.28.
  - **Time budget** lets agents search far more: about 82 searches each (2.7 per turn) against at most 30 under the frozen setting. Isolates (5 trials) then score 7.2 of 9 (humans 3.19), and networks 7 to 9. Reading took 12 seconds per turn on average and almost never used up a turn. The rates leave out thinking time, which humans need between searches and agents get for free. $0.37 for networks, $0.27 for isolates.
  - Extreme outcomes persist under every messaging rule tried, which points to agents interpreting shared information identically (one model) rather than to the amount or speed of messaging.

**Settings after the message pilots:** the frozen calibration settings plus `MESSAGE_COSTS_TIME = True` (runner default). The inbox and time-budget options are dropped from the design and stay off; their code is kept so the logged pilots can be reproduced.

- **Persona pilots** (`--personas`, all 16 trials complete, $0.68). Each agent gets a short profile drawn from the MTurk sample of Levay, Freese & Druckman (2016): age (mean 31.6, standard deviation 10 assumed), gender (53.9% male), education (their appendix Table 1), student (22.3%), and each Big Five domain low, average or high with equal chance (`harness/personas.py`). Persona draws use their own random stream, so a trial's mystery, names and effort draws are the same as without personas.
  - **Isolates** (`runs/20261021-persona-empty10`, the same 10 mystery versions as the calibration run): 4.0 of 9 correct (sd 2.0), against 3.9 (sd 1.6) without personas and 3.19 (sd 1.38) for humans. Answers at minutes 5 and 10 are close to the calibration run. The isolate calibration still holds. Trait differences are modest and noisy (about 30 agents per level): correct at the end for 31% of low-agreeableness agents against 58% of high, 32% of low open-mindedness against 56% of average, and 32% of high extraversion against 53% of low.
  - **Networks** (`runs/20261021-netpilot-persona`, one trial each; without personas in brackets): hub-and-spoke 6 (9), core-periphery 2 (9), in core-periphery 6 (6), complete clique 0 (0), locally clustered 4 (2), out core-periphery 9 (8). Two of six trials end at 0, 1, 8 or 9 against four of six before. Copying in hub-and-spoke falls to 58%, the human level (59%); in the other networks it stays at 81 to 91% (humans 59 to 75%). Messages per trial 14 to 36 (humans 15 to 28).

- **Persona network run** (`runs/20261021-persona-net10`, 10 trials per network, all 60 complete, $2.95; defaults plus `--personas`). Number correct of 9 per trial, against the paper's 30 human trials per network:

  | Network | Agents: mean, median | 0 or 1 correct | More than 6 correct | Humans: mean, median | 0 or 1 | More than 6 |
  | --- | --- | --- | --- | --- | --- | --- |
  | Hub-and-spoke | 3.5, 4 | 10% | 0% | 4.70, 4.5 | 10% | 27% |
  | Core-periphery | 6.3, 8.5 | 20% | 60% | 4.37, 4 | 27% | 33% |
  | In core-periphery | 4.7, 5 | 20% | 20% | 4.00, 4 | 10% | 13% |
  | Complete clique | 6.7, 9 | 20% | 70% | 3.53, 1 | 53% | 33% |
  | Locally clustered | 5.4, 6.5 | 30% | 50% | 3.20, 3 | 33% | 10% |
  | Out core-periphery | 6.6, 9 | 20% | 70% | 3.13, 2.5 | 30% | 13% |

  - **The main result does not replicate; it reverses.** Agents rank the networks complete clique, out core-periphery, core-periphery, locally clustered, in core-periphery, hub-and-spoke; humans rank them almost the other way round. Hub-and-spoke and core-periphery against locally clustered and complete clique: agents 1.15 fewer correct (one-sided permutation p = 0.87 for the paper's direction), humans 1.17 more.
  - **Agents learn from clues, humans from answers.** In hub-and-spoke the hub was correct at some point in 7 of 10 trials, but only 33% of spokes not yet correct went on to adopt the answer (humans: 64%). Hub-and-spoke agents end close to the isolates (3.5 against 4.0). In dense networks agents pool clues and solve the case together: 6 or 7 of 10 trials end with all or nearly all correct. The paper's mechanism, conformity locking dense networks onto the red herring, appears only in a minority of dense-network trials (20 to 30% with 0 or 1 correct, humans 33 to 53%).
  - Outcomes are still bimodal in dense networks (70 to 90% of trials at 0, 1, 8 or 9 correct, humans 37 to 67%), but not in hub-and-spoke (10%, humans 30%). Messages per trial 12 to 25 (humans 15 to 28).

- **Three variants for learning from answers** (all with personas, 5 trials per network on the same mystery versions as trials 1 to 5 of the persona run; all 100 trials complete, $6.50). New options: `--answers-first` (each turn opens with the answers of the people followed, with a tally such as "3 of the 8 people you follow have entered ..."), `--memory 4` (after the pinned instructions the agent sees only its last 4 turns and is told to keep a notebook in its notes; the window of 4 is our choice) and `--others-may-know` (one sentence: "The people you follow may have found clues that you have not."). Mean correct of 9 per network:

  | | Hub | Core-per. | In core-per. | Clique | Loc. clustered | Out core-per. | Centralised minus controls | Spokes adopting a correct hub answer |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | Humans (30 per network) | 4.70 | 4.37 | 4.00 | 3.53 | 3.20 | 3.13 | +1.17 | 64% |
  | Personas, no variant | 4.0 | 7.0 | 4.4 | 6.0 | 6.4 | 6.0 | -0.70 | 45% (9 of 20) |
  | Answers first | 4.8 | 5.6 | 5.4 | 7.0 | 5.2 | 7.2 | -0.90 | 41% (11 of 27) |
  | Limited memory | 5.8 | 9.0 | 4.4 | 3.6 | 4.6 | 5.4 | +3.30 | 73% (16 of 22) |
  | Hint | 5.2 | 5.2 | 5.8 | 7.2 | 3.0 | 4.8 | +0.10 | 59% (13 of 22) |

  - **Limited memory** is the only variant that brings the paper's direction back: centralised networks beat the decentralised controls, spokes take over a correct hub answer about as often as humans, and the complete clique (3.6) matches the human value (3.53). Notes mention other players in 10% of turns (2% without). Its isolates (`runs/20261021-var-memory4-empty10`, 10 trials) score 2.7 of 9 (sd 1.6; humans 3.19), so the isolate calibration holds. Remaining gaps: core-periphery ends at 9 in all five trials (humans 4.37), outcomes are still bimodal (27% of trials with 0 or 1 correct and 53% with more than 6; humans 27% and 22%), and cost per trial is about twice as high because the moving window defeats prompt caching.
  - **Answers first** changes nothing measurable. **The hint** raises hub following to 59% but leaves the network contrast at zero.
  - Five trials per network: differences between single networks are not reliable.

- **Memory 3 with an 8-word notepad** (`--memory 3 --notepad-words 8`, personas; 10 isolates and 5 trials per network, all complete, $3.00). Notes are now only for the current turn; each turn the agent can add at most 8 words to a notepad that stays on screen (8 words is our estimate of what a person jots down in 30 seconds). Agents scribbled every turn, 4.9 words on average, and rarely hit the limit (2% of turns); scribbles are short plans and suspects ("Peterson motive + gun, seek corroboration").
  - Isolates (`runs/20261021-var-mem3pad8-empty10`): 2.7 of 9 correct (sd 1.6; humans 3.19), but answers come far too early: 6.4 of 9 entered by minute 5 (humans 2.2), mostly other suspects and the red herring.
  - Networks (`runs/20261021-var-mem3pad8`): the opposite failure. Mean 1.8 correct (humans 3.8); 63% of trials end with 0 or 1 correct (humans 27%); hub-and-spoke 1.4, core-periphery 0.4, locally clustered 0.8, complete clique 3.4, in core-periphery 1.8, out core-periphery 3.0. Spokes adopted a correct hub answer in 1 of 9 cases. Centralised minus controls -1.20 (humans +1.17), rank correlation with the human ordering -0.43.
  - Reading: with this little memory, agents cannot hold the alibi chain (meeting time, drive time, time of death) together, so networks lock onto the red herring through each other's answers. Memory 4 with unlimited notes erred the other way. Two things changed at once (window 4 to 3, notes unlimited to 8 words), so the next step is to separate them.

- **Memory and notepad grid** (personas; 10 isolates and 5 trials per network per setting, all complete; $6.44 for the two new settings). Isolates: mean correct and answers entered by minute 5; networks: mean correct, share of trials with 0 or 1 and more than 6 correct, centralised minus controls, spokes adopting a correct hub answer, rank correlation with the human ordering of networks:

  | Setting | Isolates | Entered by min. 5 | Networks | 0 or 1 | > 6 | Centr. minus controls | Hub followed | Rank corr. |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | Humans | 3.2 | 2.2 | 3.8 | 27% | 22% | +1.17 | 64% | |
  | No memory limit | 4.0 | 2.0 | 5.6 | 20% | 43% | -0.70 | 9 of 20 | -0.26 |
  | Memory 4, notes unlimited | 2.7 | 3.6 | 5.5 | 27% | 53% | +3.30 | 16 of 22 | +0.43 |
  | Memory 4, notepad 8 words | 2.4 | 6.1 | 1.8 | 63% | 13% | +0.40 | 8 of 23 | +0.03 |
  | Memory 3, notepad 15 words | 2.9 | 6.1 | 4.9 | 27% | 43% | +1.30 | 11 of 19 | +0.14 |
  | Memory 3, notepad 8 words | 2.7 | 6.4 | 1.8 | 63% | 10% | -1.20 | 1 of 9 | -0.43 |

  Network means for memory 3, notepad 15 words: hub-and-spoke 4.2 (humans 4.70), core-periphery 6.0 (4.37), in core-periphery 5.6 (4.00), complete clique 3.6 (3.53), locally clustered 4.0 (3.20), out core-periphery 5.8 (3.13).
  - **The notepad size, not the window, decides**: with 8 words, networks collapse onto the red herring under both windows; with 15 words (or unlimited notes) they do not.
  - **Memory 3 with a 15-word notepad** is the closest overall: the centralised advantage (+1.30) and the share of trials with 0 or 1 correct (27%) match the humans, spokes follow a correct hub in 11 of 19 cases (58%, humans 64%), and isolates pass (2.9). It misses hypothesis 4: out core-periphery (5.8) does as well as the centralised networks instead of worst. Too many trials still end with more than 6 correct (43% against 22%).
  - Every notepad setting makes isolates commit early (6.1 to 6.4 of 9 answers entered by minute 5, humans 2.2): without memory of earlier turns, agents enter a guess at once.

- **Out core-periphery diagnosis** (existing records only, no new trials). Share correct at the end, core (nodes 1 to 3) and periphery: humans 32% and 37% (`individualData.tab`); agents with memory 3 and a 15-word notepad 73% and 60%; persona run without memory limit 70% and 75%. The periphery behaves as in the paper: of 33 switches to the correct answer by peripheral agents (memory 3, notepad 15), 26 came right after a core node showed the correct answer, and none after receiving a decisive clue from the core. The core almost never sends the decisive alibi clues (0 to 2 per trial). The core first gets it right at turn 20 or later in most trials, right after the weapon broadcast at minute 10. So the gap is the core, not the periphery: three core agents who see each other's answers behave like "best of three" (isolates are correct about 32% of the time, and 1 - 0.68^3 = 69%), whereas the human cores, a group of three just the same, stayed on the red herring. Agents recognise and adopt a correct answer from a peer once the weapon clue makes it checkable; humans in small clusters locked in. This is a general difference (correct answers win among agents, majority answers among humans), not one specific to this network.

- **Final run, settings and rule fixed before running** (2026-10-21): defaults (1 search per turn, repeat search, effort drawn from low, medium, high, writing a message costs the turn) plus `--personas --susceptibility --memory 3 --notepad-words 15 --plain-pay`. The new persona trait is susceptibility to interpersonal influence (Bearden, Netemeyer & Teel 1989): low ("confident in your own judgment, and you rarely change your mind because of what other people think"), average (not described) or high ("easily swayed by what other people think, and you often go along with them"), one third each, from its own random stream. Its spread was not calibrated on the human matching curve (no budget left); one third each is the same convention as the Big Five. Step 1: 10 isolate trials. Pass if all 10 complete and mean correct is between 2.2 and 4.2 (humans 3.19); answers entered by minute 5 are reported but not part of the rule. Step 2, only if step 1 passes: 10 trials per network.

- **Final run, results.** Step 1 (`runs/20261021-final-empty10`, $0.72): passed, 2.6 of 9 correct (sd 1.3; humans 3.19, sd 1.38). Answers entered: 0.3 of 9 by minute 5 and 2.3 by minute 10 (humans 2.2 and 4.8), so the toned-down wording overcorrects early answering. Step 2 (`runs/20261021-final-net10`, 10 trials per network, all 60 complete, $5.06):

  | Network | Agents: mean, median | 0 or 1 correct | More than 6 | Humans: mean, median | 0 or 1 | More than 6 |
  | --- | --- | --- | --- | --- | --- | --- |
  | Hub-and-spoke | 3.3, 2 | 30% | 20% | 4.70, 4.5 | 10% | 27% |
  | Core-periphery | 4.4, 5 | 40% | 50% | 4.37, 4 | 27% | 33% |
  | In core-periphery | 3.1, 2 | 30% | 20% | 4.00, 4 | 10% | 13% |
  | Complete clique | 3.3, 0.5 | 60% | 40% | 3.53, 1 | 53% | 33% |
  | Locally clustered | 3.9, 4 | 30% | 20% | 3.20, 3 | 33% | 10% |
  | Out core-periphery | 2.3, 1 | 70% | 20% | 3.13, 2.5 | 30% | 13% |
  | All | 3.4 | 43% | 28% | 3.8 | 27% | 22% |

  - **Matches:** overall level (3.4 against 3.8) and the share of trials with more than 6 correct (28% against 22%); core-periphery (4.4 against 4.37) and complete clique (3.3 against 3.53, median 0.5 against 1) almost exactly; hypothesis 4 in direction, out core-periphery is worst (2.3) and below the two-way centralised networks (3.9; humans 3.13 against 4.54). Rank correlation with the human ordering of networks 0.49, the highest of all settings.
  - **Misses:** the main contrast is small and not significant (centralised minus controls +0.25, one-sided permutation p = 0.43; humans +1.17), because hub-and-spoke is too low (3.3 against 4.70): spokes adopt a correct hub answer in 13 of 32 cases (41%, humans 64%). Too many trials get stuck (43% with 0 or 1 correct, humans 27%).
  - **The susceptibility trait had no measurable effect:** answer changes matching a visible neighbour 88% (low), 86% (average), 87% (high), overall 87% (humans 59 to 75%); answer changes per agent 5.7, 6.3, 5.9. Agents ignore this line of their persona.
  - Messages per trial 16 to 34 (humans 15 to 28).

Pilots 1 to 6 are single trials (nine agents) on the same mystery version (culprit Mr. Morris, red herring Ms. Peterson); pilots 7 to 9 add a second version. They show direction, not rates. Trials in one run get different seeds and so different versions.

## Counterfactuals (not in the paper)

Structures from `networks.core_periphery` and `networks.star` (`networks.COUNTERFACTUALS`): core nodes 1..c fully connected, every core node sends to every peripheral node ("out"), plus ties back up; "in" reverses every edge. Back ties follow the paper's pattern spread evenly: core node k+1 hears from peripheral node P[k * p // c] (with c = 3, p = 6: 4->1, 6->2, 8->3 as in the paper). Star: each core node sends only to its own two peripheral nodes, plus the paper's three ties back up. Settings identical to the final run (agent instructions verified identical); the two original networks come from `runs/20261021-final-net10`.

**First round** (`runs/20261026-counterfactuals-10`, 10 trials per condition, all 160 complete, $12.56; a first attempt stalled after a network change and was stopped before any trial was saved). Share of players correct at the end (group sizes differ), share of core nodes correct, and messages per trial:

| Series | Condition | Players | Correct | Core correct | Messages |
| --- | --- | --- | --- | --- | --- |
| Ties, out | 0 up / 3 up (paper) / 6 up | 9 | 38% / 26% / 48% | 40% / 30% / 43% | 10 / 16 / 18 |
| Ties, in | 0 down / 3 down (paper) / 6 down | 9 | 53% / 34% / 27% | 83% / 33% / 27% | 24 / 29 / 35 |
| Core size, out | 1 / 2 / 3 / 4 (periphery 6) | 7 to 10 | 30% / 26% / 26% / 54% | 30% / 30% / 30% / 57% | 5 / 18 / 16 / 20 |
| Core size, in | 1 / 2 / 3 / 4 (periphery 6) | 7 to 10 | 33% / 40% / 34% / 34% | 50% / 55% / 33% / 32% | 15 / 31 / 29 / 36 |
| Periphery, out | 3 / 6 / 9 (core 3) | 6 / 9 / 12 | 28% / 26% / 63% | 30% / 30% / 60% | 18 / 16 / 12 |
| Periphery, in | 3 / 6 / 9 (core 3) | 6 / 9 / 12 | 35% / 34% / 33% | 43% / 33% / 37% | 23 / 29 / 36 |
| Star | out-star vs out (paper) | 9 | 36% vs 26% | 37% vs 30% | 20 vs 16 |
| Star | in-star vs in (paper) | 9 | 44% vs 34% | 53% vs 33% | 29 vs 29 |

With 10 trials and a spread of 30 to 45 percentage points per trial, a condition mean has a standard error of about 10 to 14 points; only differences of roughly 30 points stand out. Three do: (1) a core that hears the whole periphery but sends nothing back down (`InCP_down0`) is right 83% of the time (25 of 30 core agents) and no trial gets stuck, against 33% in the paper's in core-periphery, where three peripheral nodes see the core; as soon as the core broadcasts to the periphery (3 or 6 ties down) its own accuracy falls to about 30%. (2) Out core-periphery with a periphery of 9 (63% correct, core 60%). (3) Out core-periphery with a core of 4 (54%, core 57%). (2) and (3) also change the group size.

**Second round** (`runs/20261026-counterfactuals-11to20`, trials 11 to 20 of every counterfactual, all 160 complete, $12.65; `runs/20261026-final-cp11to20`, trials 11 to 20 of out and in core-periphery with the final run's settings and seeds continued via `runner.py --slots 2 3`, all 20 complete, $1.62). Pooled, 20 trials per condition:

| Series | Condition | Players | Correct | Core correct |
| --- | --- | --- | --- | --- |
| Ties, out | 0 up / 3 up (paper) / 6 up | 9 | 36% / 34% / 42% | 37% / 37% / 40% |
| Ties, in | 0 down / 3 down (paper) / 6 down | 9 | 56% / 31% / 32% | 78% / 28% / 30% |
| Core size, out | 1 / 2 / 3 / 4 (periphery 6) | 7 to 10 | 36% / 32% / 34% / 48% | 40% / 32% / 37% / 50% |
| Core size, in | 1 / 2 / 3 / 4 (periphery 6) | 7 to 10 | 30% / 36% / 31% / 42% | 40% / 45% / 28% / 45% |
| Periphery, out | 3 / 6 / 9 (core 3) | 6 / 9 / 12 | 30% / 34% / 49% | 32% / 37% / 47% |
| Periphery, in | 3 / 6 / 9 (core 3) | 6 / 9 / 12 | 42% / 31% / 30% | 48% / 28% / 32% |
| Star | out-star vs out (paper) | 9 | 36% vs 34% | 37% vs 37% |
| Star | in-star vs in (paper) | 9 | 35% vs 31% | 37% vs 28% |

Permutation tests against the paper's network (two-sided, per-trial shares): only `InCP_down0` differs, share +24 points (p = 0.005) and core +50 points (p = 0.001); it replicated in both rounds (core 83% and 73%). The first-round leads of out core-periphery with a core of 4 (+15, p = 0.25) and a periphery of 9 (+15, p = 0.23) shrank in the second round (54% to 43%, 63% to 34%); the star is no different from the paper's networks.
