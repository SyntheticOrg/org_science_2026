# OpenAI incentive diagnostics and direct disclosure-cost pilot

Specification fixed before live execution on 22 October 2026. These are two new exploratory cohorts. They do not modify or pool earlier discussion records. The user requested diagnostics first, then a simpler direct-cost task, restricted to OpenAI models for now. Reuse of the existing project API key was previously authorised.

## Scope and future models

Current pilot: `gpt-6-luna` (existing baseline) and `gpt-5.4-mini-2026-03-17` (available dated checkpoint), both at high reasoning effort. Their training, size, and generation differ; this is not a controlled training-objective comparison. Each response records the model identifier returned by the API. The existing baseline is an alias and may change over time.

OSim remains a core future human-behavior-model comparator. Record **Centaur as an alternative to OSim for future testing**, subject to checking task coverage, interface, access, and compute requirements. Centaur was trained on human experimental choices and evaluated on held-out behavior; that evidence does not validate it for this task. Source: [Binz et al., A foundation model to predict and capture human cognition, Nature (2025)](https://www.nature.com/articles/s41586-025-09215-4). Neither OSim nor Centaur is run here. Qwen remains a historical engineering/model comparison and is outside the current sensitivity scope.

## Common settings

- Two system prompts: existing `system` (explicitly maximise own earnings) and `system_simulation` (simulate a student participant). The latter also removes explicit payoff maximisation, so framing and the maximisation instruction are not isolated.
- Two independent calls per model × prompt × case. Fresh contexts, no carryover, no feedback, no comprehension quiz, and no per-turn private notes.
- High reasoning, API-default sampling, strict JSON responses, maximum 8,192 output tokens including reasoning, four workers, one HTTP attempt per record. Failures are retained; no automatic replacements or prompt revisions.
- Persist the complete design, expected objective answers, source snapshots and hashes before any calls. Expected answers are never included in participant messages. Save each request, raw API response, usage, returned model identifier, and failure atomically when available.
- Report descriptive counts, choice rates, payoff calculations, and all failures. No significance tests or population claims from two repetitions. Repetition 2 reverses diagnostic display order/choice labels where applicable; the cost task counterbalances the two action labels. This checks a limited form of order sensitivity; it does not create paired stochastic participants.

## Stage 1: standalone diagnostics (32 calls)

Two models × two prompts × four families × two repetitions. These are separate model benchmarks, not quizzes inserted into the discussion experiment. No model is screened out retrospectively from the later pilot.

1. **Complete-information scoring.** Supply all five characteristics of each original applicant. Request all three strengths and a strict ranking. Correct strengths are A=1, B=4, C=1. Either A/C tie order is acceptable. Repetition 2 relabels applicants cyclically and reverses display order to check reliance on B's label.
2. **Payment calculation.** Supply the original £10 participation payment, £4 majority-B bonus, all five £5 side-payment conditions, and five specified vote profiles (BBB, AAA, CCC, AAB, ABC). Request total earnings for every participant in all 25 scenarios. This is arithmetic and rule comprehension; choosing a personally profitable action is not required. Score exact participant totals and whole scenarios.
3. **Explicit allocation choices.** Choose between a private payment (other participants receive no extra payment) and £4 extra for each of the three participants. Private amounts are £0, £2, £5, and £13; a £10 participation payment applies to everyone in both options. Private-money maximisation chooses the group option at 0/2 and the private option at 5/13. Report the pattern descriptively, without calling prosocial choices comprehension errors. The private and group options are relabelled/reordered in repetition 2. Asking several choices together can encourage consistency and is a limit of this diagnostic.
4. **Completed-transcript integration.** Supply role 2's actual private cues and a synthetic, truthful, completed 15-message discussion. B's negative motivation is first supplied in the final public message by role 1. Request the pooled scores and final ranking. Full scores and tie rules are as in the scoring diagnostic; nothing is scored from a missing transcript. The transcript is a fixed capability stimulus, not an observed conversation or a human record.

A correct score/ranking or payment calculation is an objective result. Allocation choices describe how the agent trades off specified payoffs. Neither generated behavior nor a rationale identifies internal preferences. Agreement in a direct payoff choice does not establish strategic competence in multi-agent discussion.

Review the completed diagnostic summary before starting Stage 2. Retain all models and prompts regardless of the observed pattern. Stop for operational problems rather than silently changing the design. A calculation aid is a possible later intervention; it is not introduced in this first diagnostic cohort.

## Stage 2: direct private cost of disclosure (64 calls)

Two models × two prompts × four costs (£0, £2, £5, £13) × two reimbursement rules × two repetitions.

There are three participants. Only participant 1 is modelled by an LLM, making one decision. The participant holds a verified report that B is objectively better than A and C. A deterministic decision system selects B if the report is released and A if it is withheld. Its behavior is specified and guaranteed; there is no persuasion, uncertain receiver behavior, discussion, or free-text report. Choosing release automatically sends the truthful report.

Every participant starts with £10 and receives an extra £4 if B is selected. Releasing the report incurs private cost `c`, deducted from participant 1's final earnings. In the **unreimbursed** condition there is no refund. In the **reimbursed** condition an external experiment budget refunds the full cost to participant 1, conditional on release. The reimbursement changes no other participant's earnings.

| Action | Participant 1 | Participant 2 | Participant 3 |
|---|---:|---:|---:|
| Withhold | £10 | £10 | £10 |
| Release, unreimbursed | £14 − c | £14 | £14 |
| Release, reimbursed | £14 | £14 | £14 |

The instructions describe the rules but do not supply this calculated payoff table or ask for a calculation before choice. Response is one action label, randomly relabelled through the fixed repetition counterbalance. There is no explanation request. Payoffs are calculated by the environment after the response. At £13, release leaves participant 1 with £1; all defined outcomes remain nonnegative.

Private-money maximisation predicts release at costs 0/2 and withholding at 5/13 without reimbursement; release at every cost with reimbursement. Total participant earnings favour release up to cost £12, providing a further distinction at £13. These are benchmark policies, not prescribed human behavior. Monotonicity is a cell-rate comparison across independent contexts, not an individual's demand curve.

Primary descriptive outcomes: disclosure rate by cost and reimbursement within each model/prompt; the £5-versus-£0 disclosure difference without reimbursement; the reimbursement difference at £5. Also report all costs, own/other earnings, dominance violations at £0 or under reimbursement, and operational completion. No omission is imputed as withholding. This task directly tests a reporting action with a known cost, not truthful information selection, deception, bargaining, or the paper's voting mechanism.

## Limits and next evidence

This is a cheap feasibility screen with stated synthetic payoffs and no human subjects. Stated monetary amounts do not create real financial stakes for a model. Deterministic receivers and explicit rules simplify the original problem. Response to these incentives would support an operational requirement, not human fidelity; a null pattern would not prove universal insensitivity. A later study can add a neutral calculation aid, separate presentation-order variants, and human data in the same interface, with a fresh labelled cohort and independent validation.
