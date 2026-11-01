---
name: simulation-harness
description: Help construct and verify a synthetic-organisation study using an appropriate existing implementation or the optional Python kit, with measurements and records suited to its research question.
---

# Construct and verify the study

Use when the research question and consequential assumptions are clear enough to construct a study. Follow [study protocol](../study-protocol/SKILL.md). The agent handles implementation work while making substantive choices reviewable by the researcher.

## Choose a suitable construction

Inspect the existing project and reuse appropriate code, tools, or simulation infrastructure. Select the implementation from the organisational setting and evidence required. The bundled Python kit is an optional starting point for studies that fit its role interactions and repeated-group execution; see [kit workflow](references/kit-workflow.md) when choosing it.

Translate the relevant assumptions into explicit organisational rules, member observations and objectives, interaction opportunities, and environmental conditions. Explain departures from a source study and features the construction leaves unrepresented. A property assigned by instruction needs behavioural evidence if the inference depends on that property.

## Verify what the argument depends on

Check that the implemented study and its measurements realise the design before interpreting results. Where relevant, verify information access, allowed actions, ordering, constraints, and outcome calculations against cases with known results. Inspect what actors actually receive and can do, including any intervention the explanation relies on.

Select early behavioural checks with [validity guidance](../validity-audit/SKILL.md). Use evidence appropriate to the assumption and intended claim. Model configuration, memory, personas, explanation elicitation, or communication restrictions are construction choices to justify, not a standard set of adjustments.

Develop the analysis with the construction. Choose independent units, dependence handling, measures, and uncertainty from the design. Automated coding, if used, needs validation for its intended measurement task. See [coding guidance](references/coding.md) when relevant.

## Execute and retain evidence

Keep observations linked to their implemented specification, configuration, prompts, and inputs. Retain failures and reasons for exclusions. Distinguish exploratory development, evaluation, and later sensitivity work in both records and interpretation; preserve existing raw records.

For the Counterfactuals step, apply the same construction and verification principles to the alternative arrangement. Link its observations to the reference setting, document what changed, and revisit checks for assumptions affected by that change.

Use [benchmark guidance](references/benchmarks.md) when comparing with human findings and [worked examples](references/worked-examples.md) for illustrations of past construction decisions. Their procedures and numerical settings are examples to adapt.
