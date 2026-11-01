# Reporting and GUIDE-LLM support

Use the plan and actual records to draft a report suited to the research question. Populate technical details automatically where possible; ask the researcher to interpret evidence and supply facts the records cannot establish. GUIDE-LLM (Feuerriegel et al., 2026, *Nature Human Behaviour*, `https://doi.org/10.1038/s41562-026-02492-7`) supports transparency and reproducibility.

## What the report should make clear

Explain the question, relevant assumptions, their construction, and the evidence obtained. Use quantitative or qualitative comparisons appropriate to the design. Where human correspondence is claimed, state the target and evidence available; where it is untested, say so.

Distinguish assumptions raised as potential threats, observed deviations, and boundaries supported by evidence. Consider competing explanations, dependence among observations, uncertainty, failed attempts, and consequential departures. A matched outcome alone does not establish a shared mechanism.

For the Counterfactuals step, report the alternative's theoretical motivation, what changed, what remained comparable, and which assumptions extend beyond the evidence examined. Compare outcomes and processes with the reference setting. Identify comparisons planned in advance and those developed from earlier findings, keeping organisational counterfactuals and implementation sensitivities distinguishable. A replication report is complete without counterfactuals.

Choose an appropriate report structure rather than requiring a section for every diagnostic theme. Do not invent unavailable benchmarks, validation results, model identifiers, consent facts, or disclosures.

## GUIDE-LLM reporting support

The following mapping supports the checklist's 14 items. Use equivalent records from the chosen implementation; kit filenames and functions are examples rather than a universal storage format. Describe participant models, coders, and other substantive LLM uses separately where their roles differ.

| Item | What to establish | Evidence to use |
|---|---|---|
| **A.1 Purpose** | Where and why LLMs were used | Actual roles in study construction, participation, measurement, or other research work |
| **A.2 Automation** | What was automated and where humans contributed | The implemented workflow and actual researcher review or validation |
| **B.1 Model identity** | Provider, requested and returned model/version, access dates | Available model and call metadata; leave unavailable snapshot information explicit |
| **B.2 Access and context mode** | API, local, or other access; interaction context | The chosen implementation's configuration and actual request construction |
| **B.3 Configuration** | Behaviourally relevant settings and repetitions | Configuration, supported sampling/reasoning settings, seeds and their scope, and the design's observation units |
| **B.4 Customization** | Fine-tuning, prompts, personas, or scaffolding used | Actual construction choices and their rationale |
| **B.5 Persistent memory** | What information persisted and between which interactions | The implemented access to histories, state, retrieval, and external memory |
| **C.1 Exact prompts** | Instructions and dynamic prompt assembly | Preserved templates, code, and records of what actors received |
| **C.2 System instructions** | System-level directions | Preserved instructions and relevant system configuration |
| **D.1 Data and privacy** | What human or sensitive information was used or sent | Actual input provenance, handling, and applicable consent or de-identification facts supplied by the researcher |
| **E.1 Validation** | What evidence checked outputs or interpretations | Relevant benchmarks, construction checks, behavioural comparisons, and any coder validation; identify missing evidence |
| **E.2 Post-processing** | Transformations, retries, filtering, exclusions, and failures | Actual processing code and records, including failed or interrupted attempts |
| **F.1 Reproducibility** | What another researcher can inspect or reproduce | Exact study specification, code, inputs, configuration, and permitted output records; hashes alone do not recover file contents |
| **G.1 Competing interests** | Funding, compute/API support, and affiliations | The researcher's disclosures; leave unknown facts unresolved rather than assuming none |

For kit studies, APPROACH.md, harness/, FREEZE.json, and runs/ provide much of this record; include a legacy analysis_plan.md if used. See [kit provenance](reproducibility.md) for their meaning. Transparent reporting does not establish the validity of an organisational inference.
