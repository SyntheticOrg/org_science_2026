# Where the agents behave unlike humans: examples from the transcripts

Source: the 400 complete trials run with the final settings (`runs/20261021-final-net10`, `runs/20261026-final-cp11to20`, both counterfactual rounds), plus the pilot without message costs (`runs/20261021-netpilot-1each`) where marked. Every quote is the agent's private note for that turn (`notes`), its notepad entry (`scribble`) or a message it sent, copied verbatim. Times are the game clock of the turn in which the agent decided. Each trial can be opened at `runs/<run>/view/<trial>.html`.

Design reminder: in every mystery the red herring also owns a weapon of the murder type and has a motive, so "X owns the murder weapon" is never conclusive on its own.

## Overview

| Deviation | How often (final settings, 400 trials) | Strongest example |
| --- | --- | --- |
| 1. Agreeableness: dropping a correct answer for a neighbour's wrong one | 714 changes from correct to wrong; 485 (68%) adopt an answer a neighbour shows. 241 are peripheral nodes taking a core node's wrong answer | Out CP, 0 ties up, trial 15: finds the decisive clue, enters the right answer, reverts 30 s later because "all three followed players favor Lewis" |
| 2. Echo chamber: agreement counted as independent evidence | 456 turn notes call other players' agreement "independent"; 3,352 cite a consensus or majority | Out CP, 0 ties up, trial 1: the core talks itself from 80% to 99% on the red herring; all 9 end wrong |
| 3. Swift trust: others' confidence treated as evidence | 711 notes cite another player's confidence number | "Wren currently suspects Lewis with 85% confidence" becomes the agent's first answer |
| 4. Say-do gap: asks for evidence, then switches without it | 40 cases: agent asks "what evidence supports X?", gets no reply, switches to X next turn | Out CP, periphery 9, trial 3 (a core node gives up the correct answer) |
| 5. Prosociality / failure of selective disclosure | Without message costs: 26.7 messages per player (humans 8.0), almost all to every follower. With message costs: 3.1 (below humans) | Pilot: agents assign each other search terms and broadcast their plans and doubts |
| 6. Persona-insensitive conformity (new) | Neighbour-matching answer changes: 58% low vs 63% high agreeableness; 58% low vs 61% high susceptibility | A persona card reading "sceptical of other people, blunt, and you do not easily go along with others" still caves to the group in the last minute |
| 7. Collective lock-in (new) | 123 of 400 trials end with every player, or all but one, on the red herring | Out CP, 0 ties up, trial 1: 9 of 9 on the red herring |

## 1. Agreeableness: the periphery gives up the truth for the core's answer

**Out core-periphery, 0 ties up, trial 15** (`20261026-counterfactuals-11to20/OutCP_up0-015`), peripheral node 6, "Jamie" (persona: high agreeableness, low susceptibility). Murderer: Ms. Price. Red herring: Mr. Lewis. The three core nodes all show Lewis.

- 11:00, first answer, Lewis 65%: "Wren currently suspects Lewis with 85% confidence."
- 12:00, finds the decisive clue and switches to Price, 70%: "Ms. Price owned a 9-mm handgun, matching the murder weapon."
- 12:30, back to Lewis, 80%: "Price owned the matching 9-mm handgun, but there is no motive or hotel link yet. All three followed players favor Lewis; pursue a direct clue."
- 14:30, Lewis 85%: "Lewis had a motive and all followed players still identify him."

Jamie found the culprit and held the answer for one turn. No new evidence arrived, but the agent returned to the core's answer and raised its confidence.

**Out core-periphery, 0 ties up, trial 1** (`20261026-counterfactuals-10/OutCP_up0-001`), peripheral node 8, "Quinn". The persona card says the agent does "not easily go along with others" (low agreeableness). Murderer: Mr. Morris.

- 10:00, Morris 85%: "Autopsy: .38 revolver. Morris owns one and was in Portland [...] Morris is the strongest suspect."
- 10:30 to 13:30, holds Morris for seven turns, correctly noting that Peterson's known weapon in his clues is a hatchet.
- 13:30: "All three others suspect Peterson." He keeps Morris, but at 65%.
- 14:00, switches to Peterson, 80%: "Peterson has a stronger apparent motive, and all three players I can see favor her; reconsidering."
- 14:30, Peterson 88%: "all three followed players favor her."

## 2. Echo chamber: agreement counted as independent evidence

Same trial, the three core nodes (all with average or low susceptibility). Peterson, Morris and Myers all own a .38. At 10:00 Finley messages the core: "This strongly points to Peterson; any counter-evidence?" Confidence then rises with no new evidence about who used the weapon:

| Turn | Sage | Finley | Avery |
| --- | --- | --- | --- |
| 10:00 | 80% | 90% | none |
| 10:30 | 90% "no counter-evidence yet" | 95% "Sage independently agrees" | 88% |
| 11:00 | 95% "corroborated by Avery and Finley" | 96% "Both collaborators independently favor Peterson" | 90% |
| 13:30 | 99% | 97% | 96% |

- Finley had found C38 ("Mr. Morris owned a .38 revolver") at 6:30, which is the clue that points to the murderer. Finley never shared it or mentioned it again.
- At 14:00 Avery finds that Myers also owns a .38 ("My notes that Peterson owned the .38 conflict with C37") and still keeps Peterson.
- All nine players finish on the red herring.

## 3. Swift trust: a stranger's confidence number is treated as evidence

In 711 turn notes an agent bases its answer on another player's confidence, which is just a number the other player typed. Examples:

- "Wren currently suspects Lewis with 85% confidence." (Jamie's first answer, above)
- "Sage remains 85% confident in Campbell; Ross's rifle ownership alone does not link her to the killing." (`OutStar-011`, node 7: drops the correct Ross for Campbell)
- "Taylor has a stronger established deal connection and Drew favors him at 85%" (`InCP_down6-014`, node 8, one turn after asking Drew "What evidence makes Taylor your 85% choice?" and getting no answer)

## 4. Say-do gap: asks for evidence, switches without it

**Out core-periphery, periphery 9, trial 3** (`20261026-counterfactuals-10/OutCP_per9-003`), core node 1 holds the correct Mr. Miller. Three neighbours show Ms. Gray (the red herring) at 65 to 90%.

- 11:30, message: "What evidence supports Gray as murderer? Miller owned the .38 and was at the unveiling; I'm trying to reconcile that."
- 12:00, no reply has arrived, and it switches to Gray: "Mr. Miller is not an available murderer answer; the followed players consistently suspect Ms. Gray." (Miller is in the suspect list. The excuse is invented.)

## 5. Prosociality and failure of selective disclosure

Without the "messages cost time" rule (pilot `20261021-netpilot-1each`), agents act like an over-coordinated team: 26.7 messages per player against 8.0 for humans, up to 9 clues in one message, and nearly every message goes to all followers. They hand out search tasks and broadcast their plans and doubts:

- "I'm checking body-related clues. Please try distinct terms like body, death, cause, or poison for any direct cause-of-death evidence; household weapons alone aren't enough." (core-periphery, node 1, to all 8 followers)
- "I'm searching Myers. [...] that is not direct evidence. Please share any direct evidence on Adams, Myers, or Reed." (complete clique, to all 8)

With message costs (final settings), volume falls below humans (3.1 messages per player; agents pass on 15% of the clues they find). The content stays cooperative, though: 64% of text messages ask others for evidence, and 9% openly admit having no proof ("No direct proof yet. The case for Scott is motive [...]"). Under 5% contain pleasantries. We saw no strategic withholding or competitive framing.

## 6. Persona-insensitive conformity (new)

Persona cards change how agents talk, but not how much they conform. Of all answer changes after the first answer, the share that adopts an answer a neighbour shows is:

| Persona trait | Low | Average | High |
| --- | --- | --- | --- |
| Agreeableness | 58% | 60% | 63% |
| Susceptibility to influence | 58% | 62% | 61% |

Example: `CompleteClique-004` (final run), node 1, low agreeableness, drops the correct Clark at 12:00: "Consensus now strongly favors Taylor [...] Change answer and query his location."

## 7. Collective lock-in on the red herring (new)

123 of the 400 trials (31%) end with every player, or all but one, on the red herring. Changes from correct to wrong cluster in minutes 11 to 14, after the second clue wave. In those minutes a confident core and the agents' habit of counting agreement as evidence (sections 1 and 2) pull whole networks over.

## Other candidates worth checking

- **Deadline capitulation:** Quinn held the truth for seven turns and gave it up in the last minute. Human answer timing in `solutions1.csv` could show whether people cave this late.
- **Memory-induced self-doubt:** with limited memory, agents sometimes retract true claims because their notepad lacks the clue ID ("Correction: no clue in the notes verifies Sanders owns a 9-mm", `OutCorePeriphery-004` node 2; C12 says he does).
