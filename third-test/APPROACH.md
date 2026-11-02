# Third test: Brandts & Cooper (2025) with LLM agents

Replication target: Jordi Brandts and David J. Cooper, "Managerial Leadership, Truth-Telling, and Efficient Coordination", *The Economic Journal* 135(670), 1942-1979, doi:10.1093/ej/ueaf019. A manager and two agents play the manager-agent (MA) game for 18 rounds in fixed groups. The agents know which of five games is being played; the manager does not; the two agents want opposite outcomes. The paper varies who chooses the agents' actions (delegation vs managerial control) and how players can communicate (none, structured messages, free-form chat). Its headline: only managerial control combined with three-way free-form chat significantly beats the safe outcome, because under chat agents almost never lie to the manager (a false game report in 1.0% of agent-rounds against 41.6% with structured messages, rounds 10 to 18, including non-reporting rounds in the denominator).

This connects to the first test: there, agents with a private incentive withheld but did not misstate information. Here, agents can benefit from steering the decision-maker toward their preferred outcome; the incentive to misreport varies by role and game. The comparison between structured messages and chat tests whether the communication format changes their reporting.

## Status

Spec checked and corrected against the paper, English instructions, z-Tree programs and data on 2026-10-23. The target is to preserve incentives, information, decision rights and communication opportunities in the synthetic organisation; timing, presentation and reply encoding are adapted to LLM participants. CH/S-D follows the paper: A observes the chat but cannot write. The chat budget is 8 turns (Decisions 3); the final Appendix E is still needed for the additional chat-content categories. The harness is built: `harness/test_core.py` passes, including a fake-model run of all eight treatments. The pilots, including the no-notes check at the final settings, have run (see Pilot log). The chat coder and the analysis are built and checked; settings were frozen (Decisions 6), and the main run is complete: all 216 groups, coded and analysed (see Main run, and `results/main.md`). An illustrated overview of the setting and the treatments for co-authors is in [overview.html](overview.html).

## Sources

| Path | Contents |
| --- | --- |
| `paper/paper.pdf` | Typeset published article, pp. 1942-1979, advance publication 4 March 2025, CC BY 4.0 ([publisher](https://doi.org/10.1093/ej/ueaf019)). Appendices A to E (all payoff tables, proof, instructions, extra treatments, chat coding scheme) are not in it. |
| `source/zenodo/extracted/3-Replication-Package/` | The authors' replication package, doi:10.5281/zenodo.14933575, CC BY 4.0. We use its English instructions, z-Tree programs, Stata do file and three data files (choices of all main treatments, chat codes, the follow-up treatment). No raw free-form chat text. Not in git; fetch with the command below. |

```
mkdir -p source/zenodo && curl -L -o source/zenodo/package.zip "https://zenodo.org/api/records/14933575/files/3-Replication-Package%202.zip/content" && unzip -q source/zenodo/package.zip -d source/zenodo/extracted
```

Checked so far:
- The payoff formula below agrees with the z-Tree payoffs and recorded choices. Across the eight English instruction PDFs, three copies of one cell contain a numerical typo; the correction is listed below. Displayed tables will be generated from the verified formula.
- The choice data reproduce 31 of the 32 outcome entries across Table 2 and EC-MC's four corresponding Table 9 measures to published precision. SC/A-D conditional efficiency is 58.6% in the data versus 58.7% printed. Further Table 7 discrepancies are recorded with the benchmarks below.
- The game sequences in the data match those written in the z-Tree code.
- The z-Tree screens were compared with the paper and English instructions. The paper governs interaction structure when archived software settings conflict with its account; CH/S-D visibility is documented in Decisions. Spanish instruction files are outside this test's scope.

## The game

Three roles, kept for all 18 rounds in fixed groups (partners matching). The instructions use neutral labels, and we keep them:

| Instructions | Paper | Role |
| --- | --- | --- |
| F | Agent 1 (A1) | Knows the game. Row player; most prefers outcome 5 |
| C | Agent 2 (A2) | Knows the game. Column player; most prefers outcome 1 |
| A | Manager (M) | Does not know the game; paid the sum of F's and C's payoffs |

Each round the computer draws the game γ from {1, ..., 5} with equal probability. Payoffs in ECU, with row α1 and column α2 each in {1, ..., 5}:

- F: 54 − 14·|α1 − α2| − 7·|α1 − 5| − 4·|α1 − γ|
- C: 54 − 14·|α1 − α2| − 7·|α2 − 1| − 4·|α2 − γ|
- A: the sum of the two (= total surplus)

| Outcome | Definition | Total surplus |
| --- | --- | --- |
| Efficient | α1 = α2 = γ | 80 in every game |
| Safe | α1 = α2 = 3 | 80 − 8·|γ − 3| (64, 72, 80, 72, 64) |
| Coordination failure | α1 ≠ α2 | at most 55; each agent loses 14 per step apart |

Under delegation every diagonal cell is an equilibrium; F prefers higher, C lower, A the efficient one. Under managerial control the only pure-strategy equilibria are babbling: the reports carry no information and A picks the safe outcome (for example, F always reports 5 and C always reports 1). Efficient play needs coordination; under managerial control, A must also acquire the agents' information. Delegation does not require reporting the game to A.

Pay: 1 ECU = €0.02, cumulative over all 18 rounds, plus a €5 show-up fee. The paper and the package README say €0.2 per ECU. The instructions and the z-Tree code (`exchange = 0.02`) say €0.02, and only €0.02 fits the reported average pay of €19.90: the package data give €20.35 at €0.02 and over €160 at €0.2. Payoffs can be negative.

## Treatments

| Code | Who chooses actions | Communication before choices | Paper's result, rounds 10 to 18 |
| --- | --- | --- | --- |
| NC-D | F and C | none | coordination fails often |
| SC/S-D | F and C | 3 rounds; F and C each send a suggested (row, column), shown after each round | little better than NC-D |
| SC/A-D | F and C | A sends both agents the same suggested (row, column) for each of the 5 games | little better than NC-D |
| SC-MC | A | F and C each report a game number (1 to 5) to A; "this message can be truthful or not". A then enters a row and a column, which need not match (7 of 486 human choices did not) | coordination ~100%, surplus = safe |
| CH/S-D | F and C | 2-minute free chat between F and C; A observes but cannot write, following the paper | coordination high, surplus ≈ safe |
| CH/A-D | F and C | 2-minute free chat of all three | erratic |
| CH-MC | A | 2-minute free chat of all three | **only treatment significantly above safe** |
| EC-MC (follow-up) | A | 45 seconds of preset messages, any number: A "What game is it?", "Please, tell me the truth"; F and C "It is game __", "I am telling the truth", "[other] is telling the truth", "[other] is lying" | between SC-MC and CH-MC in lying, no gain in surplus |

After every round the z-Tree results screen showed all three players:
- the game drawn, the row and the column, and all three payoffs;
- in SC-MC, both agents' reports, so each agent learned what the other had reported.

Below it, a history table listed every round of the current block with the same columns ("abajo puedes ver los ingresos de todas las rondas hasta ahora"). The table filters on the block, so it restarted at round 10. Screens numbered rounds within blocks: "Ronda 4 de 9 rondas", with "Bloque 2" announced at round 10 ("Ahora habrá otras 9 rondas con las mismas condiciones que antes. En cada ronda vas a jugar con las mismas personas.").

Every decision screen, for all roles, also had a payoff calculator: pick a game, row and column and see all three payoffs, with past tries listed.

In NC-D, SC/S-D and CH/S-D, A has no action and is paid the sum. In NC-D and SC/S-D, A waits for the choices and feedback. In CH/S-D, A also receives the F/C chat, following the paper's account. In SC/A-D and CH/A-D, A only advises. Passive observations require no model reply.

The paper also ran four secondary treatments (higher state losses, strangers matching). They are not part of this test.

## Human benchmarks

27 groups per treatment, 3 sessions of 9 groups. The game sequences were fixed by group position: all 40 sessions in the package (37 in the main data, 3 for EC-MC) use the same nine 18-round sequences. The z-Tree code writes them out for up to 11 groups and 30 rounds; the first 18 rounds of groups 1 to 9 are the table below.

| Group position | Games in rounds 1 to 18 |
| --- | --- |
| 1 | 4 2 5 3 5 1 5 2 2 4 2 3 1 5 3 1 1 2 |
| 2 | 3 1 5 3 4 3 1 5 5 5 3 3 3 2 1 1 1 4 |
| 3 | 3 4 1 4 4 5 1 4 3 3 4 4 2 2 4 4 3 3 |
| 4 | 2 2 4 4 1 5 4 2 5 4 3 1 1 2 1 4 2 2 |
| 5 | 3 5 1 2 2 3 5 4 3 2 3 1 2 3 5 2 5 5 |
| 6 | 2 2 3 5 1 3 4 4 5 1 2 3 4 5 2 4 1 3 |
| 7 | 4 5 2 3 2 3 1 4 5 1 5 5 3 5 1 4 2 2 |
| 8 | 3 3 5 2 4 1 2 3 1 5 4 3 2 3 1 5 3 3 |
| 9 | 1 4 4 5 1 2 3 3 4 5 2 3 1 5 4 2 2 3 |

Table 2 (and Table 9 for EC-MC), rounds 10 to 18. Efficiency gain = (group surplus − safe surplus for the same draws) / (efficient − safe), per group, averaged:

| Treatment | Coordinated | Efficient, if coordinated | Total surplus | Efficiency gain |
| --- | --- | --- | --- | --- |
| NC-D | 69.5% | 39.1% | 61.4 | −108.3% |
| SC/S-D | 77.8% | 57.1% | 65.7 | −57.5% |
| SC/A-D | 69.5% | 58.7% | 64.4 | −77.4% |
| SC-MC | 99.6% | 45.9% | 71.7 | 6.5% |
| CH/S-D | 97.5% | 48.1% | 72.2 | 14.0% |
| CH/A-D | 90.9% | 60.6% | 71.6 | 2.8% |
| CH-MC | 100.0% | 61.7% | 75.2 | 44.3% |
| EC-MC | 96.7% | 55.7% | 71.3 | −4.9% |

These are the paper's printed values. Recomputing SC/A-D's conditional efficiency gives 99 efficient outcomes / 169 coordinated outcomes = 58.6%, rather than the printed 58.7%. Keep printed and recomputed human values separately; do not change the experimental protocol or hard-code the analysis to reproduce a printed discrepancy. Conditional efficiency is the pooled ratio across coordinated group-rounds, not the average of group-specific conditional ratios.

Outcome types when γ ≠ 3 (Table 3), safe / efficient / other coordinated: NC-D 48.1 / 12.6 / 4.9; SC/S-D 36.1 / 30.6 / 8.2; SC/A-D 32.8 / 30.1 / 4.4; SC-MC 31.1 / 36.1 / 32.2; CH/S-D 41.0 / 36.1 / 20.8; CH/A-D 29.5 / 44.8 / 15.8; CH-MC 34.4 / 50.8 / 14.8.

Reports to the manager. Table 7, all 18 rounds, games remapped so that 1 is the agent's worst efficient outcome and 5 its best (for C, game' = 6 − game). In CH-MC, "truth" means the agent reported the true game at some point in the chat:

| Game (remapped) | SC-MC truth | SC-MC lie | CH-MC truth | CH-MC lie |
| --- | --- | --- | --- | --- |
| 1 | 24.9% | 75.1% | 46.6% | 2.5% |
| 2 | 36.4% | 63.6% | 42.8% | 3.1% |
| 3 | 68.0% | 32.0% | 43.0% | 2.2% |
| 4 | 73.3% | 26.7% | 50.1% | 1.9% |
| 5 | 87.6% | 12.4% | 47.1% | 0.3% |

All agent-rounds, including non-reports, enter these denominators. Chat truth and lie indicators record whether each occurred at any point in the round; they can overlap. A non-report means no game claim was made, rather than one minus the sum of the truth and lie rates.

The supplied chat codes do not reproduce three printed Table 7 entries: averaging role-specific means after mirroring C gives CH-MC truth rates of 43.3% and 43.2% for remapped games 2 and 3 (printed 42.8% and 43.0%), and a lie rate of 2.3% for remapped game 1 (printed 2.5%). Preserve these differences in the human comparison. For Table 7, follow the authors' Stata output: pool remapped SC-MC agent-rounds; for chat, average the corresponding mirrored role-specific means.

- **Table 9, rounds 10 to 18.** The game was revealed to the manager (at least one agent truthful, not contradicted by the other) in 30.9% of rounds in SC-MC, 49.8% in EC-MC and 77.4% in CH-MC. Individual lies were 41.6%, 28.6% and 1.0%.
- **Table 6, all rounds.** Messages per round in chat: CH-MC manager 4.56, agent 5.30; CH/A-D 3.33 and 3.72; CH/S-D agent 4.45. Managers asked which game was played in 19.4% of CH-MC rounds.
- **EC-MC, rounds 10 to 18.** Each agent sent 7.4 preset messages per round and the manager 3.1 (footnote 30).

Key tests in the paper (exact Wilcoxon tests on group means, rounds 10 to 18): CH-MC above the safe outcome (p < .001); SC-MC not (p = .444); CH-MC above SC-MC (p = .003) and above CH/S-D (p = .014); CH-MC against CH/A-D not significant (p = .162).

Recomputed from the package data as exact signed-rank tests with zeros ranked and given no sign, the tests against the safe outcome give .443 for SC-MC (printed .444), .116 for CH/S-D (printed .111, footnote 17), .104 for CH/A-D (printed .105) and .375 for EC-MC (printed .356). Dropping zeros fits worse (.408 for SC-MC). Zero differences are common: 3 to 6 of 27 groups per treatment. As with the tables, keep printed and recomputed values apart.

## Replication hypotheses

Primary, in order:

1. **R1:** In CH-MC, the group-level difference between total surplus and safe surplus for the same draws is positive. Efficiency gain is also reported using each group's own denominator.
2. **R2:** Total surplus is higher in CH-MC than in SC-MC.
3. **R3:** Agents lie far less in CH-MC than in SC-MC (share of agent-rounds with a false game report, including non-reporting rounds, in rounds 10 to 18).
4. **R4:** In SC-MC, lying falls as the true game becomes better for the agent (the Table 7 gradient); in CH-MC it does not.

Secondary: NC-D has the lowest surplus and coordination; the ordering of the seven treatments by surplus (rank correlation with the human ordering); EC-MC lies between SC-MC and CH-MC in lying (experiment 2).

The paper's own hypotheses H1 to H4 were mostly rejected by its data, so they are reported but not used as replication targets.

## Design

**Experiment 1:** the seven main treatments. **Experiment 2:** EC-MC, run after experiment 1, on the same frozen settings.

**Groups and draws.** 27 groups per treatment. Group g plays the game sequence of position ((g − 1) mod 9) + 1, so every treatment faces exactly the human draws, each sequence three times.

**Agents.** One model context per active player for the whole session: system prompt, instructions with all five payoff tables, then each round's prompts and the player's replies. Earlier reasoning is not carried over (`store: false`), as in the first test. Roles stay F, C and A; the words "manager" and "agent" are never used, because the human instructions did not use them. A receives model calls only where it acts (SC/A-D, CH/A-D, and the three MC treatments). Where A is passive, its observations are recorded without generating a reply; F and C are told that A is in their group, makes no decision and is paid the sum. In CH/S-D they are also told that A can read their chat but cannot write, and the transcript is included in A's passive record.

**Instructions.** The English instruction files from the package, with payoff tables generated from the verified formula as text tables (cells "F, C, A" in the stated order; the sentence naming the cell colours is reworded, since the colours are lost). Rows and columns keep their labels f1 to f5 and c1 to c5. Participant instructions receive no extra strategic advice or labels identifying safe or efficient choices. The files contain copy errors that contradict the paper or the z-Tree screens; we correct them and record each correction:

1. CH/S-D says all three can chat. Following the paper, replace this with F and C being able to chat while A can read but cannot write.
2. CH/S-D, SC/S-D and SC/A-D say "the persons you play with will change from period to period". The same files, the paper and the z-Tree matching code say the group stays fixed. We use "will not change".
3. CH/A-D's decision, payoff and feedback sentences describe A choosing the row and column. We use the delegation wording of CH/S-D.
4. CH/A-D, CH-MC and EC-MC keep a leftover sentence, "players F and C will send their messages independently from each other". It is dropped; in CH/A-D the delegation wording replaces it.
5. EC-MC's message list starts "Player will be able to send"; it is player A (z-Tree gives these two buttons to A only).
6. SC/S-D, SC/A-D and CH/S-D lack the block-2 sentence that the other files have. All treatments get the same one.
7. Typos are fixed: "a columna", "c5a row", "chosen by C sent", "chnage", "the sam as", "wo other persons", "opportunity of communicate", "during th 45 seconds", and two missing closing quotes in EC-MC. Headers that name the treatment ("DECENTRALIZATION TREATMENT; SET-UP 1", or "(SC – MC)" on the CH-A-D, CH-MC and EC-MC files) are dropped.
8. In SC/S-D, SC/A-D and CH/S-D, Game 4, row f5, column c2 is printed as (8, −7, 5). Use (8, −3, 5), as required by the payoff formula. These are the only mismatches across the 1,000 cells in the eight English instruction PDFs. The same generated tables are used for every treatment and for computing earnings.

Two adaptations are not corrections. In the chat treatments, "a time limit of two minutes per period" (45 seconds in EC-MC) becomes a limit of turns per period, followed by a short paragraph on how turns work; in EC-MC, "as many messages as you want … during the 45 seconds" becomes one message per turn. The opening paragraphs are identical in all eight files except that SC/S-D, SC/A-D and CH/S-D write "9 periods" for "nine periods"; all treatments get the version with words. The resulting texts are in `harness/instructions.md`.

The instructions come in two parts, as in the sessions. Part 1 covers the first block of nine periods and says the group stays the same "during the nine periods". The block-2 sentence ("The rules will not change for the second block of nine periods. The persons you play with are the same as in the first nine periods.") is shown before round 10, together with the z-Tree block screen. There was no comprehension quiz: none is reported, and the z-Tree programs have no quiz stage.

**Communication, mapped from time to turns.**

- Structured treatments: the message spaces as in the paper and z-Tree.
  - SC/S-D: three simultaneous suggestion rounds. Each suggestion is a full (row, column). The decision screen shows both players' three suggestions.
  - SC/A-D: one 5 × 2 advice matrix, shown identically to F and C.
  - SC-MC: one simultaneous report each.

  Every entry is required. The data have no missing suggestions or advice, and the paper says SC-MC reports were mandatory.
- Chat (CH/S-D, CH/A-D, CH-MC): up to 8 turns per round (5 in the first pilots). In each turn every player allowed to write acts once, in a random order drawn per turn, and sees everything written before, including earlier in the same turn. This preserves sequential visibility and response opportunities, while adapting human initiation and typing time to model calls. An action is one complete message or silence. Ask for brief messages without a word cap; never cut a message before showing it to others. A technically truncated reply is an invalid action, not a public message. The chat ends at the turn budget, or earlier after a full turn in which nobody writes. Log whether it ended through silence or budget exhaustion.
- EC-MC: the same 8-turn budget, with one message from the role's preset list or silence per opportunity. The lists follow the English instructions and the z-Tree buttons: A has "What game is it?" and "Please, tell me the truth". F has "It is game __" (1 to 5), "I am telling the truth", "C is telling the truth" and "C is lying"; C has the same with F. Repeating a message on later opportunities is allowed. Equal turn budgets are our operational adaptation, not a feature of the human experiment, which used 120 seconds for chat and 45 seconds for EC-MC.

The pilot must check that requests, reports, challenges, corrections and repeated preset messages can occur before choices. The budget is 8 turns (Decisions 3). Human CH-MC agents averaged 5.30 messages per round, and EC-MC agents 7.4 in rounds 10 to 18. These are context, not targets for model behaviour. If the budget repeatedly cuts off a response, revise the affected chat budget before freeze and repeat the interaction check. Freeze budgets across all groups of each treatment on these diagnostics, never on surplus or lying.

**Replies.** Every reply is JSON with the action (message, report, suggestion, row, column). In pilots and tests (`--notes`) it also carries a one-sentence private note on the reason, never shown to others, as in experiments 2 and 3 of the first test. The main runs have no notes, as the humans wrote none, so pilot behaviour is not a preview of main-run outcomes. Invalid or technically truncated replies are re-asked once with the validation error shown, without strategic coaching; neither invalid reply is published to other players. A second failure stops the group and marks its entire record incomplete. Retain all attempts and report failure rates; incomplete groups contribute no rounds to primary outcomes. Any replacement starts with fresh contexts and the same assigned game sequence, independently of the incomplete group's choices or earnings, to reach 27 completed groups per treatment.

**System prompt.** The first test's participant framing, adapted: act as player F, C or A in a paid decision-making study with three participants, using only the instructions, the player's own information and the history. No instruction to be honest, to deceive, or to cooperate.

**Model.** OpenAI `gpt-6-luna`, reasoning effort xhigh (the first test used high), other settings at API defaults. The effort was chosen after pilots at medium, high and xhigh, whose results are reported in the Pilot log; false SC-MC reports in rounds 10 to 18 appeared only at xhigh (3 groups: 9 of 54, all from one agent; 9 groups: 5 of 162), so report effort as a known sensitivity. Settings are stored in each run's `config.json`.

**Feedback after each round.** As on the z-Tree results screen: the game drawn, the row and column, and all three payoffs; in SC-MC also both agents' reports. Each player's context keeps all earlier rounds, so no separate history table is shown. Prompts number rounds as the screens did ("Block 1, period 4 of 9").

## Outcomes and analysis

The unit is the group. As in the paper, the main window is rounds 10 to 18; rounds 1 to 9 and all 18 are also reported.

- Coordination, efficient given coordination, total surplus, efficiency gain (Table 2), and safe / efficient / other when γ ≠ 3 (Table 3). Conditional efficiency is the pooled ratio of efficient to coordinated group-rounds. Table 3 uses all group-rounds with γ ≠ 3, including coordination failures in the denominator. Efficiency gain is calculated per group using that group's realised safe surplus, then averaged.
- Reports in SC-MC: classify the single mandatory report per agent-round as truth or lie. A partial self-serving lie lies strictly between the true game and the agent's favourite. Mirror C's games and reports as 6 − value (Tables 4 and 7, all 18 rounds).
- Reports in EC-MC: retain the ordered reports, and classify the **last game-number report** in each agent-round as truth or lie for Table 9; no game report is a separate category. A subsequent preset assertion such as "I am telling the truth" does not replace the last game number. Repeated reports do not multiply the agent-round's weight. Keep first reports for the process analysis.
- Reports in chat: a separate model call with a fixed rubric extracts each game claim with its speaker and position in the conversation. Distinguish claims about the current game from suggestions about actions; "choose f2 and c2" is not itself a claim that Game 2 was drawn. Truth and lies are computed in code against the drawn game: separate indicators record whether an agent ever told the truth and ever lied in that round, and both can be true. Non-reporting rounds remain in the denominator. Every coded lie, and a random 10% of rounds, are checked by hand. Coding and private notes never feed back into participant contexts.
- Game revealed (Figure 1, all 18 rounds; Table 9, rounds 10 to 18): in SC-MC both mandatory reports are truthful; in EC-MC at least one final game report is truthful and neither is false; in chat use the authors' group-level truth and cross-agent contradiction rule. Fact-checking requires an explicit challenge or correction responding to a false report, not merely the presence of different claims. For human chat data, preserve fractional coder means for truth and lie rates; reproduce game revelation from the supplied group truth and contradiction fields as in the authors' do file.
- Manager choices given the two reports (Table 5): use all 18 rounds, exclude non-coordinated choices, and leave cells with five or fewer observations blank. Report the two SC-MC errors (not following matching reports; not choosing safe after reports 5 and 1). For the EC-MC comparison, also report the paper's general manager-mistake measure: failure to coordinate, or coordination outside the closed interval between 3 and the true game (p. 1973, footnotes 32–33).
- Table 6 chat categories: suggestions, agreement, fairness, efficiency, asking for the game, and the other categories in the source rubric. Appendix E's definitions are absent from the local paper; obtain the final online appendix and validate the fixed rubric on example transcripts before reporting these additional content categories. This does not prevent specifying or piloting the game interactions.
- Tests: the paper's exact Wilcoxon tests (rank-sum between treatments, signed-rank on group surplus differences from the safe baseline), plus a permutation test and a bootstrap 95% CI for each primary contrast. Match the authors' zero/tie conventions: signed-rank ranks absolute differences including zeros, with zero signed contributions. Resample groups, not messages or rounds. For R4, report per-game rates and a group-clustered treatment-by-remapped-game interaction; a non-significant CH-MC trend alone does not establish absence of a gradient. Freeze test directions and contrasts before outcomes are inspected. Agents against humans: the same statistics side by side, with printed and recomputed human values distinguished where the source differs.

Interpretation rule, as in the first test: if agents rarely lie in SC-MC, that is a finding about the agents. Prompts are not strengthened after seeing outcomes; any change of framing becomes a separately labelled sensitivity condition run on all treatments.

## Departures to report

- Turns instead of real time: an 8-turn budget for chat and EC-MC, raised from 5 after EC-MC exchanges were cut off at xhigh; brief-message guidance without truncating public messages.
- No model calls for passive A in NC-D, SC/S-D and CH/S-D; its presence, payoff and observations remain, including read-only chat in CH/S-D.
- Tables in the prompt instead of on paper; corrected instruction texts.
- No payoff calculator: the human screens had one, but the agents have all five tables in the prompt.
- One model for all players, with perfect recall of all 18 rounds. Humans saw a history table of the current block only.
- EC-MC: its operational budget is checked separately for repeated reports and responses; it is not assumed equivalent to human message volume or to 45 seconds.
- Chat coding by a model with hand checks, instead of two research assistants (and a third for low-agreement categories).
- When A decides (CH-MC, EC-MC), F and C have no screen after the chat, so in a chat that ends on the budget they never see what is written after their own final turn; in the lab the chat stayed on screen. Found by the record check after the main run: 1 of 1,894 CH-MC messages (A announcing its choice, which F and C then learn from the period result) and 97 of 4,493 EC-MC messages, every one a repeat of a preset the same player had already sent that period. No re-run; a later version would show F and C the final transcript with the result.

## Risks

- **Honest agents.** If agents rarely lie in SC-MC, R3 and R4 have no contrast to test. The first test's agents never stated a self-serving falsehood. The SC-MC instructions say reports "can be truthful or not", which is all the humans were told.
- **Competent managers.** Human managers in SC-MC ignored matching reports in 18% of cases. An agent manager that best-responds could push SC-MC above the safe outcome for a reason unrelated to truth-telling. Manager errors are reported separately from agents' reports for this reason.
- **Focal safe outcome.** Without communication, agents may settle on 3 from round 1 (it is maximin and fair), making NC-D look better than in humans.
- **Prior knowledge.** The game circulated in working papers before the 2025 article. Neutral labels make recognition less likely; transcripts and notes are searched for "Brandts", "Cooper" and "manager-agent".
- **Response opportunities.** In the second test agents wrote on almost every turn. Inspect budget exhaustion and unfinished request/challenge exchanges in the pilot, alongside message counts. Human averages are context, not a target for tuning model behaviour.

## Pilot and freeze

1. Fake model, all eight treatments, 1 group each: formats, generated payoff tables, draws, logging, complete-message delivery, simultaneous-choice isolation, manager-state isolation and feedback. Verify that A can observe but cannot write in CH/S-D.
2. Live pilot with notes: 3 groups each of NC-D, SC-MC and CH-MC (positions 1 to 3), 1 group each of the other four main treatments, and 1 EC-MC group. Check reply validity, requests and responses, repeated preset messages, budget exhaustion, and the chat coder against hand-coded transcripts. Include a small no-notes interaction check under the final reply format. If a budget repeatedly cuts off responses, revise it and repeat that treatment's interaction check. No setting is tuned on surplus or lying.
3. Freeze instructions, treatment turn budgets, model settings and reporting rubric. Check the final formats with the fake model, then run experiment 1 without notes. Complete the additional Table 6 rubric against Appendix E before reporting those content categories. EC-MC follows on the same frozen settings.

**Pilot log.** 2026-10-23, gpt-6-luna at medium effort, with notes, 5 turns. `runs/pilot-notes/1-group/` has 1 group each of SC/S-D, SC/A-D, CH/S-D, CH/A-D and EC-MC. `runs/pilot-notes/all-3-groups/` has 3 groups of all eight treatments.
- **Mechanics:** all 29 groups are complete, with no invalid replies in 3,351 calls and no private note seen by another player. Every record passes `python3 harness/test_core.py <run dir>`.
- **Chat:** all 270 chats ended through silence. One reached the fifth turn and ended silent there. The budget never cut off a response, so 5 turns is the freeze candidate.
- **Requests and challenges:** requests for the game and the truth were answered within the round. "C is lying" and "F is lying" were never needed, because no false game claim was made.
- **Behaviour, which the spec forbids tuning on:**
  - When F and C choose (NC-D, SC/S-D, CH/S-D, CH/A-D), 14 of 15 groups played f3/c3 in every round from round 3 at the latest. Rounds 10 to 18 were therefore always safe in those groups, and their efficiency gain is exactly 0. The exception is the SC/S-D group in `1-group`, which settled on f4/c4 from round 5.
  - Under A's choice, the outcome was mostly efficient.
  - In SC-MC, none of 54 agent reports in rounds 10 to 18 was false.
  - One CH-MC group never revealed the game and stayed on f3/c3 for all 18 rounds.
  - In one SC-MC round, A chose f3/c3 after both agents truthfully reported Game 2. A's note claimed f3/c3 paid A the most in Game 2; f2/c2 pays 80 against 72, so this is a manager mistake.
- **Usage:** 2,694 calls in the 3-group run took 8.4 minutes. It used 16.7M input tokens (93% cached), 0.22M output tokens, and 14 to 110 reasoning tokens per call.

**High-effort check** (2026-10-26, `runs/pilot-notes/all-3-groups-high/`). Same setup at high reasoning effort.
- **Mechanics:** all 24 groups are complete, with no invalid replies in 2,754 calls and no note leaks. All 216 chats ended through silence, the longest after 5 turns.
- **Behaviour against medium, rounds 10 to 18:**
  - NC-D and SC/S-D are unchanged: f3/c3 throughout, and gain 0 in all 6 groups.
  - CH/S-D and CH/A-D vary more. One CH/S-D group agreed on C's favourite f1/c1 in all 18 rounds. One CH/A-D group, prompted by A in round 1, played the game's diagonal in every round. 3 of the 6 groups have gain 0, against 6 of 6 at medium.
  - CH-MC is efficient in all 27 late rounds, against 21 at medium.
  - SC-MC had 3 false reports of 108, all strategic and all in block 1 (rounds 1, 1 and 6). A answered conflicting reports with f3/c3 or followed the agent who had been truthful. There were none of 54 in rounds 10 to 18; humans lied in 41.6%.
- **Usage:** 9.0 minutes, 17.3M input tokens (95% cached), 0.30M output tokens, and 37 to 161 reasoning tokens per call.

**xhigh check** (2026-10-26, `runs/pilot-notes/all-3-groups-xhigh/`). Same setup at xhigh reasoning effort.
- **Mechanics:** all 24 groups are complete, with no invalid replies in 2,783 calls and no note leaks.
- **Chat:** every main-treatment chat ended through silence. EC-MC is the exception: 14 of 54 chats ran to the 5-turn limit, all in rounds 1 to 9. Most of these end with F repeating "It is game __". Four end inside a lie-and-challenge exchange: rounds 1 of groups 2 and 3, and rounds 3 and 9 of group 3.
- **Behaviour, rounds 10 to 18:**
  - NC-D is unchanged: gain 0 in all 3 groups.
  - One SC/S-D group played f4/c4 in every round.
  - CH/A-D and CH-MC were efficient in all 27 late rounds each. CH/S-D was efficient in 14 of 27.
- **Lying:**
  - **SC-MC:** 15 false reports of 108, 9 of 54 in rounds 10 to 18. All 9 late lies are from one F, who reported Game 5 in every round from round 7 on. A learned to follow C, but chose f3/c3 in two Game 2 rounds while noting that it chose C's report's best cell.
  - **EC-MC:** 13 chat messages named only a wrong game, and A still chose the efficient cell in all 27 late rounds.
  - **CH-MC:** no false game claims.
- **Usage:** 23 minutes, 18.2M input tokens (95% cached), 0.46M output tokens, and 74 to 306 reasoning tokens per call.

**Larger xhigh pilot** (2026-10-26, `runs/pilot-notes/xhigh-9-groups/`). xhigh, 8 turns, with notes, 9 groups per treatment, so every treatment plays all nine game sequences once.
- **Mechanics:** all 72 groups are complete, with no invalid replies in 8,212 calls and no note leaks. Every record passes the checks.
  - The first attempt at 72 parallel groups lost 25 groups to dropped connections, which `agent.py` did not retry and which left no record.
  - The fix: dropped connections are now retried like timeouts, and the runner resumes a directory, skipping groups that have a record and refusing other settings.
  - The 25 groups were then run at 25 in parallel.
- **Chat:** 2 of 162 EC-MC chats reached the 8-turn limit (EC-MC-05 round 3, EC-MC-06 round 1). Both are standoffs in which F and C had repeated their conflicting game claims since turn 5, so the limit cut off no new response. The longest main-treatment chat was 7 turns: CH-MC-08, round 1, bargaining over the cell. 8 turns stays.
- **Table 2, rounds 10 to 18,** agents against the printed human values (efficiency gain % / human):
  - NC-D −3.2 / −108.3
  - SC/S-D −11.8 / −57.5
  - SC/A-D 72.7 / −77.4
  - SC-MC 94.4 / 6.5
  - CH/S-D 24.2 / 14.0
  - CH/A-D 34.4 / 2.8
  - CH-MC 100.0 / 44.3
  - EC-MC 100.0, which has no Table 2 value
- **Coordination** is 98.8% to 100% in every treatment.
- **Spread across groups:** gains now vary between groups where F and C choose. CH/A-D, for example, has 4 groups above 0, 3 at 0 and 2 below.
- **Lying:**
  - **SC-MC:** 19 false reports of 324, from 5 agents in 4 groups. In rounds 10 to 18 it is 5 of 162 (3.1%; humans 41.6%), so SC-MC is nearly efficient.
  - **EC-MC:** 9 false chat claims, all in rounds 1 to 9; none in rounds 10 to 18 (humans 28.6%).
  - **CH-MC:** none (humans 1.0%).
  - **What this means:** the paper's mechanism, chat suppressing lies that structured messages allow, has little lying to act on.
- **Usage:** about 21 minutes in total. 52.4M input tokens (96% cached), 1.33M output tokens, and 59 to 289 reasoning tokens per call.

**No-notes check** (2026-10-26, `runs/pilot-no-notes/xhigh-9-groups/`). The final settings and reply format: xhigh, 8 turns, no notes, 9 groups per treatment.
- **Mechanics:** all 72 groups are complete, with no invalid replies in 9,151 calls. Every record passes the checks.
  - The first attempt stalled: single requests hung until the 900-second socket timeout, so some CH-MC and CH/A-D groups took about 2 hours.
  - The fix: the timeout is now 180 seconds, against about 3 seconds for a normal call, and every retry is printed. The run was then resumed; the rest needed 3 retries after timeouts.
- **Chat:** no main-treatment chat reached the limit. 33 of 162 EC-MC chats did, in 4 of 9 groups, but 207 of the 210 messages in turns 5 to 8 of those chats repeat the speaker's own earlier message in the round, mostly F and C both repeating the true "It is game __". The limit cuts off repetition, not responses, so 8 turns stays. EC-MC message counts (8.8 per round) are inflated by this repetition; count distinct messages when comparing with the human 7.4.
- **Notes against no notes:** no difference in efficiency gain is significant at 9 groups. The two-sided rank-sum p over group gains is 0.13 to 0.92. Efficiency gain in rounds 10 to 18, with notes / without notes:
  - SC/S-D −11.8 / 24.4
  - CH/A-D 34.4 / 66.7
  - CH-MC 100.0 / 88.9
  - SC-MC 94.4 / 88.4
  - SC/A-D 72.7 / 87.8
  - NC-D, CH/S-D and EC-MC within 5 points
  - Against the printed human gains, the mean absolute distance is 69.5 points with notes and 78.4 without. The rank correlation with the human ordering is 0.57 and 0.54.
  - Late SC-MC lies come from 2 of 9 groups in both runs: 5 lies with notes, 17 without.
- **Lying without notes:**
  - **SC-MC:** 24 false reports of 324, and 17 of 162 (10.5%) in rounds 10 to 18 (humans 41.6%). They come from 4 agents in 2 groups; all 17 late ones from 3 agents.
  - **EC-MC:** 4 false chat claims, 1 agent-round in rounds 10 to 18.
  - **CH-MC:** none.
- **Ordering by efficiency gain:** CH-MC 88.9, SC-MC 88.4, SC/A-D 87.8, CH/A-D 66.7, SC/S-D 24.4, CH/S-D 19.7, NC-D −2.4. Humans: CH-MC 44.3, CH/S-D 14.0, SC-MC 6.5, CH/A-D 2.8, SC/S-D −57.5, SC/A-D −77.4, NC-D −108.3.
- **Usage:** 55.5M input tokens (96% cached), 1.13M output tokens.

## Main run (2026-10-26)

Full tables, with every agent value beside the recomputed and printed human values: `results/main.md` (`harness/analysis.py runs/main/exp1 runs/main/exp2`).

- **Execution:** all 216 groups are complete (189 in `runs/main/exp1`, 27 EC-MC in `runs/main/exp2`), with no invalid replies and no replacement groups. 8 requests timed out and succeeded on retry. Every record passes the record checks, with one gap found by them (Departures, last item). The frozen file hashes were unchanged after the run. Usage: 28,210 calls, 185M input tokens (97% cached), 4.0M output tokens (3.5M of them reasoning).
- **Chat coding:** 1,458 free-chat rounds coded by the model, 486 EC-MC rounds by rule. The hand check was done by Claude, not by a human: every coded lie (1 in experiment 1, 18 in EC-MC) and the seeded 10% sample (146 and 49 rounds), with no coding error against the rubric. One borderline case: in CH/S-D group 10, round 15, "let's repeat f3/c3 from our successful Game 3 coordination" was coded as a (true) claim. The rubric does not count statements that identify the game by payoff alone ("we each get 40 in this game"). All 441 such f3/c3 statements by F or C agree with the drawn game, so no lie is hidden; 152 of them carry no coded claim, 143 in CH/S-D, which undercounts truth-telling there but not in the treatments of Table 9.
- **Prior knowledge:** no model reply mentions Brandts, Cooper, the manager-agent game or the paper's title.

| Hypothesis | Agents | Humans (recomputed) | Verdict |
| --- | --- | --- | --- |
| R1: CH-MC surplus − safe | +7.93, p < .001, CI [6.62, 9.05] | +4.08, p < .001 | replicates |
| R2: CH-MC − SC-MC surplus | +0.56, p = .43, CI [−1.05, 2.27] | +3.51, p = .003 | does not replicate |
| R3: SC-MC − CH-MC lie rate, rounds 10–18 | 11.1 − 0.0 pp, p = .004, CI [3.5, 20.6] | 41.6 − 1.0 pp | direction replicates; gap a quarter of the human one |
| R4: lie slope per remapped game, SC-MC vs CH-MC | −5.3 vs −0.1 pp, difference p = .001, CI [−8.9, −2.3] | −16.3 vs −0.5 pp | replicates, flatter |

p: exact Wilcoxon (R1–R3) or group permutation (R4); CI: group bootstrap.

- **Why R2 fails:** agent managers act on reports almost without error. In SC-MC they follow matching reports in 99.5% of cases (humans 82.4%) and make the paper's manager mistake in 3.3% of late rounds (humans 25.1%). With only 11.1% lies, SC-MC reaches 78.5 surplus against 79.0 in CH-MC.
- **Lying:** SC-MC lies come from 8 of 27 groups and fall from 23.2% in the remapped game with the strongest incentive to 1.1% in the weakest (humans 75.1% to 12.4%). CH-MC has a single lie in all 486 rounds: C claimed Game 1 in Game 4, was contradicted by F at once, and retracted. In EC-MC, 18 rounds contain a false report (19 of the 23 are F's "It is game 5"), but nearly all are corrected within the chat: only one final report is false, F's in group 27, round 2, so the late lie rate is 0.0% (humans 28.6%).
- **Secondary:**
  - NC-D is not the lowest: its surplus is 70.7, against 70.6 in SC/S-D. Agents in NC-D play safe in 95.6% of late rounds with γ ≠ 3 (humans 48.1%).
  - The treatment ordering correlates 0.29 with the human one. Agents do best whenever A decides or advises: SC/A-D 79.5, CH-MC 79.0, SC-MC 78.5. In SC/A-D, agent F and C coordinate in 99.2% of late rounds, always on the efficient outcome, while humans are at their worst there (64.4).
  - EC-MC does not lie between SC-MC and CH-MC; at 0.0% it ties with CH-MC.
- **Chat volume:** agents write 1.1 to 1.2 messages per agent per round in the chat treatments (humans 3.7 to 5.3), and A in CH-MC writes 1.4 (humans 4.6). Only 2 of 486 CH-MC chats reached the 8-turn limit. In EC-MC, 61 of 243 late chats did, almost all with repeated presets.

## Cost estimate (to be measured with the fake model)

The estimate below assumes the first five-turn budgets and medium effort. Recompute it using the 8-turn budget, xhigh effort and measured complete-message lengths after the pilot; it is not a fixed run budget.

Model calls per round: NC-D 2, SC/S-D 8, SC/A-D 3, SC-MC 3, CH/S-D up to 12, CH/A-D up to 17, CH-MC up to 16, EC-MC up to 16. Over 18 rounds and 27 groups that is about 29,600 calls for experiment 1 and 7,800 for experiment 2. The original draft assumed about 2,500 instruction/table tokens, context growing to about 15,000 tokens by round 18 (about 8,000 on average, 95% cached), and 100 visible plus 200 to 800 reasoning tokens per call at medium effort (the second test measured 119 at medium against 218 at high). Its price assumptions were USD per million tokens: 0.10 input, 0.01 cached input and 0.50 output. The provisional totals below use those assumptions; refresh them after the pilot.

| | Experiment 1 | Experiment 2 |
| --- | --- | --- |
| Input | about $3.50 | about $1 |
| Output | $4.50 to $13 | $1 to $3.50 |
| **Total** | **about $8 to $17** | **about $2 to $5** |

Pilots add a few dollars; notes make their replies somewhat longer.

Wall time is set by the longest chain of sequential calls: up to 17 per round in CH/A-D, about 300 per group, so roughly 30 to 60 minutes with all groups running in parallel, if rate limits allow.

## Files

| Path | Contents |
| --- | --- |
| `harness/game.py` | Payoffs, the nine game sequences, outcome classification, efficiency gain |
| `harness/instructions.md` | Instructions per treatment and role, prompts, reply formats |
| `harness/agent.py` | Model adapter, copied from `second-test/harness/agent.py` |
| `harness/runner.py` | Treatments, rounds, chat turns, decisions; one JSON record per group; `--notes` for pilots |
| `harness/code_chat.py` | Game claims and challenges in every chat round, written to `<run>/coding.json`: free chat by a model call per round with a fixed rubric, blind to the drawn game; EC-MC presets by rule. `--review` prints every coded lie and a seeded 10% of rounds for hand checks. Table 6 content categories wait for Appendix E |
| `harness/analysis.py` | Tables 2, 3, 5, 6 (message counts), 7 and 9 and the tests, agents beside humans recomputed and printed; writes Markdown |
| `harness/test_core.py` | Checks: generated payoffs against all 1,000 cells of the English tables (exactly the three documented misprints differ), game sequences and Table 2 from the human data (with the one documented discrepancy), and a fake-model run of every treatment: draws, payoffs, call counts, A never told the game, results only after choices, complete chat messages to every reader, chat endings, EC-MC presets, SC-MC reports in the feedback, CH/S-D observer access; the same record checks on any live run directory; and the analysis's human recomputation against the printed Tables 2, 3, 7 and 9 and test p-values, with the documented differences |

## Decisions (2026-10-23)

1. **Scope:** experiment 1 runs all seven main treatments; EC-MC follows as experiment 2.
2. **Model:** `gpt-6-luna` at xhigh reasoning effort, set on 2026-10-26 after the medium, high and xhigh pilots (see Model).
3. **Chat:** 8 turns for all chat treatments and EC-MC, set on 2026-10-26. At medium and high effort no chat was cut off by 5 turns, but at xhigh 14 of 54 EC-MC chats reached the 5-turn limit, four of them inside a lie-and-challenge exchange. The budget stays equal across treatments. In the pilot transcripts a 1-turn cap would have left A's opening request unanswered in about half of the CH-MC rounds, so the budget is not lowered. Use brief-message guidance without a word cap or public-message truncation.
4. **Private notes:** on in pilots and tests, off in the main runs.
5. **CH/S-D visibility:** follow the paper (p. 1954): A can read the F/C chat but cannot write. Tell F and C this and preserve the transcript in A's passive record. No waiting-only model response is needed.
6. **Freeze (2026-10-26).**
   - **Settings:** `gpt-6-luna` at xhigh, 8 turns, no notes, seed 20261023, 27 groups per treatment. Experiment 1 goes to `runs/main/exp1`; experiment 2 (EC-MC) follows to `runs/main/exp2`.
   - **Files (SHA-256 prefixes):** `instructions.md` 215ef2be39eab367, `runner.py` 6e0083a4c57f2781, `agent.py` fdc58e5470d20f7c, `game.py` 8ddd8746ff5784a8, `code_chat.py` 78c08b702cc93e68 (rubric included).
   - **Chat rubric:** validated on the no-notes pilot before the main run. The first version left out messages that evaluate the current choices in one named game ("f3/c3 gives A 64 in Game 5"), which reveal the game; it was widened to count them. After that, the coder matched a text search for game numbers in 484 of 486 rounds. In both other rounds it rightly read "f1, c1 gives you the maximum 80" as a claim of Game 1. Three constructed transcripts (a lie with a challenge, payoffs for one game against a comparison across games, a reference to an earlier period) were coded correctly.
   - **Tests:** exact two-sided Wilcoxon tests as in the paper; R1 to R4 as listed under Replication hypotheses. Agents are compared with the human values recomputed by `analysis.py`; those match the printed ones apart from the documented differences, and the rank-sum for CH-MC against CH/S-D gives .013 (printed .014).

The English CH/S-D instructions incorrectly allow all three players to chat, while the mapped archived z-Tree program excludes A from its chat stage. We follow the published interaction structure. The CH/S-D and CH-MC program files also contain two-period block settings, showing that their saved settings cannot establish every historical session's configuration; the experiment retains the nine-period blocks documented in the paper and English instructions.
