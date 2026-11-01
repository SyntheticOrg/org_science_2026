# Measuring interactions with a coder

Use automated coding only when it is appropriate to the measurement task. Choose the unit, categories, and validation approach from the research question. Manual interpretation or deterministic measurement may be sufficient for some material.

Ground the coding scheme in the study's concepts and, where relevant, the source protocol. Explain what each category includes and excludes. Keep the information available to the coder appropriate to the task; avoid supplying conditions or expected results that would contaminate the intended judgement.

Examine coding quality on material relevant to the decisions it must support. Choose human checks and agreement measures that can reveal consequential errors, including missed instances. Report the selection of checked material and its limits rather than treating agreement in a selected subset as population accuracy.

Preserve the rubric, coder configuration, source-unit identity, and validation evidence associated with reported findings. Keep revisions distinguishable so changes to measurement do not silently alter earlier results.

## Optional kit helper

The bundled coding.py provides fixed-rubric calls, output records, and resume support. It checks rubric and schema consistency when resuming; use distinct output files for different source material or model configurations.

Its review() helper displays positive cases and a seeded random share of all units (10% by default). Select a validation strategy suited to the study rather than assuming this default is sufficient. Its agreement() reports the share of hand-checked units confirmed, not a general estimate of coder accuracy.

The helper illustrates one coding workflow. Report the actual procedure and its evidence under [reporting guidance](../../study-protocol/references/reporting.md).
