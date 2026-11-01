---
name: setup-synthetic-organisations
description: Prepare the environment and research records for the implementation chosen for a synthetic-organisation study, reusing an existing project or the optional Python kit as appropriate.
---

# Prepare the chosen implementation

Use from [design-study](../design-study/SKILL.md) when construction or execution is needed. This helper remains available explicitly. Begin with the research question and intended construction; access credentials are not needed to draft a plan.

Inspect the existing project, environment, and authorisation before changing anything. Reuse the chosen implementation and its conventions. Check its runtime and local verification procedures, preserve existing files and records, and create only the study structure it needs.

If the bundled Python kit fits the study and no appropriate implementation exists, follow [kit workflow](../simulation-harness/references/kit-workflow.md) to scaffold and check it. Its filenames, model adapters, and command flags apply to kit studies.

Resolve model access when live execution becomes relevant. Check the selected backend's credential or endpoint configuration without exposing secret values, following the host's authorisation rules. If access is unavailable, explain what is missing and continue independent design or offline verification.

Continue with [construction guidance](../simulation-harness/SKILL.md). Keep one coherent study plan in APPROACH.md or the existing project's format and retain enough provenance to connect results to the construction used.
