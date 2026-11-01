# Bundled kit research record

This reference describes the optional Python kit's records. Other implementations should preserve equivalent evidence suited to their construction; they do not need these filenames or repeated-group structure. The shared principles are in [study protocol](../SKILL.md). The agent can use actual records to draft [reporting entries](reporting.md).

## What is recorded

- **runs/<run_id>/config.json:** Run mode, variant, requested settings and model, full prompt templates, hashes of the harness and study plan, and git/environment provenance.
- **Group JSON records:** Treatment, group, local seed, status, timing, role messages and replies, and per-call returned model identifiers, usage, and retries where available.
- **runs/ledger.jsonl:** Start and end events for every study/probe launch. A start without an end keeps an interrupted launch visible.
- **Editor guard:** The configured edit/write/patch hook blocks direct changes to matching run-record files and flags changes to frozen files. Keep records harness-written.

New studies use APPROACH.md for design and analysis. The runner freezes it along with harness/ and also includes a legacy analysis_plan.md when present. Existing copied harnesses and historical freezes are not migrated.

Hashes detect changes but do not recover old file contents. Preserve the exact plan and harness in version control or the shared study archive alongside the run records. Returned identifiers record what the server reported; they do not guarantee that an API alias always serves unchanged weights.

## Random streams and independent groups

Group.stream(name) provides a deterministic local stream for a given base seed, treatment, group, and stream name. Toggling an optional feature leaves other local draws unchanged within the same treatment and group across variants. Different treatments have different streams; common random draws across treatments require an explicit study-specific design. These local seeds do not make API responses deterministic.

The kit's repeated-group examples use fresh role histories for independent groups. If that is the design being implemented, analyse repeated rounds and messages within their group rather than counting them as independent groups. Other designs must establish their own units and treatment of dependence.

## Calibration, freezing, and variants

- **Calibration:** List treatments reserved for focal replication and counterfactual evaluation in study.FOCAL. The calibration command refuses these treatments. Ordinary pilots and probes are not automatically held out; follow the plan and disclose any focal inspection.
- **Freeze:** Fix settings and hashes of the complete plan, prompts, code, analysis, and checks before the main run.
- **Main:** The runner verifies frozen settings and files. Keep the plan unchanged during interpretation; write findings and later sensitivity rationales in results/.
- **Variants:** Label deliberate departures and analyse each variant separately from the exact primary run. A revised main design needs a documented new freeze. Refreezing does not undo earlier outcome inspection.

Use failure counts by treatment and the ledger together: complete, incomplete, or error records describe finished attempts, while a missing end event or missing planned group record can reveal an interrupted run. Do not silently replace failures or omit aborted attempts.
