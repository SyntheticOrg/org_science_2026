---
name: design-study
description: Guide a researcher from an organisational question or source study through explicit assumptions, suitable construction, evidence checks, execution, and interpretation for replication or counterfactual exploration.
disable-model-invocation: true
---

# Design a synthetic-organisation study

This is the main entrance to **Design -> Check -> Run -> Counterfactuals -> Interpret**. Follow [study-protocol](../study-protocol/SKILL.md). Help the researcher make scientific decisions and handle the construction work those decisions require.

## Establish the question and assumptions

Read the supplied paper, protocol, notes, or existing implementation first. Draft what the sources establish; distinguish missing details, assumptions, and proposed departures. Ask about consequential gaps as they arise without making the researcher restate supplied information.

Establish the intended contribution: replication, counterfactual exploration, or both, and whether agents represent humans or are themselves the subject. Help articulate the proposed explanation, including competing accounts or what remains exploratory. A fully specified mechanism need not be assumed at the start.

Describe the organisational features relevant to the question. Roles, information, objectives, decision rights, and communication are useful prompts; include other features where needed. For comparisons, explain what changes and which features should remain comparable.

Ask which assumptions about members, interactions, or the setting the argument depends on. Use [validity guidance](../validity-audit/SKILL.md) to suggest relevant considerations, including social preferences, behavioural variation, memory and information exchange. These themes guide reflection without restricting the assumptions a researcher can investigate.

## Plan construction and evidence together

Keep one coherent study plan, using [the outline](templates/APPROACH.md) or the researcher's existing format. Adapt its length and sections to the study; preserve existing analysis plans without duplicating them. Record how the assumptions will be represented, what observations would support or challenge the account, how dependence and uncertainty will be handled, and what remains untested.

Use [construction guidance](../simulation-harness/SKILL.md) to reuse or build an appropriate implementation. Use [setup](../setup-synthetic-organisations/SKILL.md) when needed. Select the model, analysis unit, measurements, and diagnostic procedures from the design. The bundled kit is an option; its task structure and commands do not define the method.

## Check and run

Make the implemented design and checks reviewable before interpreting results. Choose proportionate early checks of the assumptions that matter. An instruction assigning a property to an agent is a construction choice, not evidence that the property shaped its behaviour.

Keep exploratory adjustments and evaluation distinguishable; preserve authorisation already given and ask only for missing choices or required approval. Record what informed changes and what specification produced each reported observation.

## Counterfactuals

When counterfactual exploration is intended, help the researcher formulate theoretically motivated alternative arrangements. Explain what changes, what should remain comparable, and which assumptions the alternative preserves or introduces. Revisit construction and relevant checks before comparing its outcomes and processes with the reference setting.

Record whether the comparison was planned in advance or developed from earlier findings, and identify where the alternative extends beyond the evidence examined. Keep substantive organisational counterfactuals distinguishable from sensitivity to implementation choices. A replication-only study can leave this step out of scope.

## Interpret

Use the protocol to examine outcomes, process evidence, competing explanations, and claim scope. Draft reporting details from actual records and ask for researcher judgement where evidence cannot decide. Explain the next useful action in research terms.
