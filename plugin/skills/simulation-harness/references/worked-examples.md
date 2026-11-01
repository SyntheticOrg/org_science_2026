# Worked examples: the three replications

Each test was a replication of a published organisational experiment with the same model (gpt-6-luna), built by hand before this kit existed. The kit took its parts from them. Outcome correspondence and a plausible diagnostic explanation are distinct; these examples do not establish that every suspected difference caused the result.

## first-test: hidden profiles, discussion vs market (Maciejovsky & Budescu, 2020)

- **Design:** triads pool scattered evidence on three applicants, by discussion or in a double-auction market. Side payments create conflicts of interest.
- **Replicated:** discussion beat the market by 0.94 correct votes per triad (humans 1.00).
- **Did not:** with conflicting side payments, discussion stayed at 2.96 to 3.00 correct votes (humans 0.53 to 1.80), so the paper's interaction reversed.
- **Diagnosis:**
  - Agents put nearly all their cues on the table in the first round (module A2).
  - Paid agents argued for their target without stating a self-serving falsehood (A3); that observation alone does not identify prosociality (A1).
  - In incentive probes, models disclosed at costs of £0 and £2, withheld at £5 and £13, and disclosed again when reimbursed (A1, D3).
  - Open models made scoring errors already in control groups (B5).
  - An earlier open-model pilot sent the final-ranking request without the complete transcript; the corrected rerun was checked against the saved requests (D2).
- **Kit parts:** the probe shape of `probe.py` (`incentive_diagnostics.py`); `ChatModel` (`vllm_model.py`); the statistics helpers.

## second-test: network centralisation (Bernstein, Shore & Jang, 2023)

- **Design:** nine players search for clues and message along network ties in 30-second turns; six networks.
- **Replicated:** overall accuracy (3.4 vs 3.8 of 9).
- **Did not:** with full context, the centralisation advantage reversed (−1.15 vs +1.17 correct).
- **Diagnosis:**
  - Agents kept every clue in context (B1).
  - They sent about ten times as many messages as humans until writing a message cost the turn (B2).
  - In pilots, agents with low reasoning effort mostly ended on the red herring (B3).
  - Agents copied visible neighbours at 87% against 59 to 75% for humans (A4).
  - A susceptibility persona was ignored (C1).
- **Intervention evidence:** a memory window of three or four turns plus a short notepad restored the direction (+1.30 in exploratory work); the final run kept little of it (+0.25, p = .43). Initial calibration used isolated players, but later interventions were selected while inspecting network pilots, including the focal contrast. Final settings were fixed before the last run; this does not remove that exploratory selection. The plugin's rule for future evaluation is stricter.
- **Kit parts:** the memory window, persona and reasoning summaries in `agent.py`; `personas.py`; the effort mix; and the `Notepad`, taken from its engine.

## third-test: manager and agents (Brandts & Cooper, 2025)

Summary in `third-test/README.md`.

- **Design:** a manager and two agents in seven communication and decision-rights treatments, with the authors' replication package.
- **Replicated:** chat beat the safe outcome, and agents lied less in chat than with structured reports.
- **Did not:**
  - With structured reports, agents misreported in 11.1% of late rounds against 41.6% for humans (A3).
  - Agent managers almost never erred: 3.3% against 25.1% (B4).
  - Structured reports already reached 78.5 of 80, so chat added 0.56 against 3.51 (a ceiling).
- **Diagnosis:**
  - In pilots, late false reports appeared only at the highest effort (B3).
  - Asking for private notes changed behaviour: late false reports under structured reports rose from 5 with notes to 17 without (B7).
  - Transcripts were scanned for the authors' names (D1).
  - Human values were recomputed from the package: 31 of the 32 outcome entries checked matched the paper, and the discrepancies were recorded.
- **Kit parts:**
  - `agent.py`'s re-ask with the problem shown and `GroupFailed`;
  - the runner's resume rule and per-group records;
  - `chat.py`;
  - `coding.py` (`code_chat.py`);
  - the record checks in `test_kit.py` (`test_core.py`).

## What carried over

- In every test, whether agents reproduced the human contrast depended on how the arrangement met a human–agent difference. Run the validity audit before building, not after the first surprising result.
- The checks that caught real defects were record invariants and fake runs, not reading transcripts.
