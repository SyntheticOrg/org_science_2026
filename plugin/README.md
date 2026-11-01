# synthetic-organisations (v1)

A plugin for Claude Code and Codex that helps researchers construct synthetic organisations for replication, counterfactual exploration, and theory development. It guides researchers in making assumptions explicit, choosing how to represent them, examining the resulting behaviour, and judging what the findings can support.

## Start with the research question

Use `/design-study` with a paper or organisational question. The plugin drafts a study plan from the available material and asks about consequential gaps. Researchers can pursue replication, counterfactual exploration, or both, using an existing simulation or constructing one appropriate to the question.

| Stage | Researcher considers | Plugin supports |
|---|---|---|
| **Design** | What is being investigated, and which assumptions does the argument depend on? | An explicit account of the organisation, proposed explanation, and evidence needed |
| **Check** | Does the construction represent those assumptions, and what could undermine the interpretation? | Proportionate implementation checks and examination of relevant behaviour |
| **Run** | Which comparisons or observations address the question, and what must be recorded? | Execution of the chosen design with traceable settings, changes, and outcomes |
| **Counterfactuals** | What might change under an alternative arrangement, and which assumptions would that comparison depend on? | Construction and comparison of theoretically motivated alternatives, with remaining uncertainties explicit |
| **Interpret** | What was observed, which explanations remain plausible, and where do the claims apply? | Comparison with available evidence and propositions with an explicit scope |

The five stages can be revisited as evidence develops. Counterfactuals may be planned from the outset or developed from earlier findings; record that distinction. A replication-only study can leave counterfactual exploration out of scope. Construction changes and their influence on interpretation remain visible.

## Assumptions lead the guidance

Social preferences, behavioural variation, memory and communication limits, and disclosure of private information are useful starting points. They are examples of assumptions that may matter; the research question determines which differences deserve attention and whether other assumptions need investigation.

For example, when a proposed mechanism depends on conflicting interests, the plugin asks how those interests are represented and what behaviour would show that they matter. The researcher can choose evidence appropriate to the setting. A particular payoff probe, model, or intervention is not prescribed for every study.

Potential threats, observed deviations, and supported boundaries are kept distinct. A matching outcome alone does not establish a shared mechanism. Where human correspondence is weak or untested, counterfactual findings remain propositions about the specified simulation. If AI organisations themselves are the subject, agent characteristics can be part of the phenomenon.

## Construction and research records

The agent helps select and verify a suitable implementation. The bundled [Python kit](skills/simulation-harness/references/kit-workflow.md) is one starting point; existing harnesses and other suitable approaches can be used. Its role histories, execution modes, files, and commands describe that implementation.

[Study protocol](skills/study-protocol/SKILL.md) states the shared methodological principles. [Validity guidance](skills/validity-audit/SKILL.md) supplies relevant considerations. [Construction guidance](skills/simulation-harness/SKILL.md), [setup](skills/setup-synthetic-organisations/SKILL.md), and [study map](skills/study-map/SKILL.md) support the next useful action without a sequence of commands for the researcher to learn.

Keep a coherent study plan, the implemented specification, and records linking observations to their configuration. New kit studies use APPROACH.md, harness/, runs/, and results/. Other implementations can keep equivalent records. The plugin helps prepare [GUIDE-LLM reporting](skills/study-protocol/references/reporting.md) from the evidence actually available.

## Validation

Run `python3 plugin/scripts/validate.py` from the repository root for structural and offline kit checks. Each study still needs checks suited to its construction and intended claims.
