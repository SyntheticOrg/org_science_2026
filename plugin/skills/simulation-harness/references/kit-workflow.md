# Optional Python kit workflow

Use this reference when the bundled kit fits the chosen construction. It illustrates one implementation of the shared workflow; its roles, repeated groups, filenames, and command flags are not requirements for every synthetic-organisation study. See [construction guidance](../SKILL.md) for the general principles.

## Prepare a kit study

The kit uses Python 3.10 or later and only the standard library. Run `python3 <plugin>/skills/simulation-harness/kit/test_kit.py` to check it locally. For a new study, create `harness/`, `runs/`, and `results/` without overwriting existing files.

Copy `agent.py`, `runner.py`, `probe.py`, `study.py`, `chat.py`, `coding.py`, `stats.py`, `personas.py`, `analysis.py`, and `instructions.md` from `kit/` to `harness/`, and copy `test_kit.py` as `test_core.py`. Preserve existing ignore rules and add missing `.env` and `__pycache__/` entries. Retain fake smoke runs as labelled records.

Use `APPROACH.md` for the study plan. A separate legacy `analysis_plan.md` can remain; the runner includes both when present. Check the selected backend's access configuration only when live execution is needed, without printing secrets. The adapters support the Responses API or an OpenAI-compatible chat endpoint.

## Adapt construction, analysis, and checks together

- [study.py](../kit/study.py) is a toy reporting game. Replace its task and define `TREATMENTS`, `FOCAL`, `MODEL`, `EFFORT`, and `run_group(group)`. `FOCAL` contains the treatments reserved for focal evaluation, including replication comparisons. The calibration command refuses them.
- [instructions.md](../kit/instructions.md) stores prompt sections read by `load_sections` and assembled with `fill`. Verify what each role actually receives and when.
- [analysis.py](../kit/analysis.py) calculates the toy game's accuracy and contrast. Replace these with the study's measurements and analysis; it is not a generic analyser. The kit writes one record per launched group. Specify what that unit represents and how the analysis handles dependence in the chosen design.
- [test_kit.py](../kit/test_kit.py) supplies task checks and generic self-tests. Adapt the task checks to verify permitted information, valid decisions, timing, constraints, and outcome/contrast calculations against known cases.

[agent.py](../kit/agent.py) provides isolated histories and optional memory/notepad helpers; [chat.py](../kit/chat.py) provides turn-taking; [runner.py](../kit/runner.py) provides execution and records. Open [probe.py](../kit/probe.py), [personas.py](../kit/personas.py), [coding.py](../kit/coding.py), or [stats.py](../kit/stats.py) for a concrete study need.

Check the operational meaning of optional settings. Bounded history currently requires an explicitly pinned prompt; a notepad's word limit applies per entry rather than to its entire history. Effort mixtures affect the Responses adapter; the chat adapter's `with_effort` does not vary its configuration. These implementation details need to match the intended construction and be checked in actual requests.

The kit defaults to no private reasoning notes and refuses `--main --notes`. If elicitation itself is part of the research design, represent and verify it explicitly in the study rather than treating that flag as a general methodological rule. Generated reasons remain self-reports.

## Execution example

Run from the study root, using the conditions and repetition counts justified by the plan. These commands illustrate a study with separate calibration and evaluation conditions; skip calibration when it does not fit the design.

```bash
# Offline checks of the implemented task and analysis
python3 harness/test_core.py
python3 harness/study.py --fake

# Early work on conditions available for adjustment
python3 harness/study.py --treatments <non_focal_code> --groups <pilot_n>
python3 harness/study.py --calibration --treatments <non_focal_code> --groups <calibration_n>

# Fix the specification for the planned evaluation
python3 harness/study.py --freeze --groups <evaluation_n>
python3 harness/study.py --main

# Check and analyse the selected run
python3 harness/test_core.py runs/<selected_run>
python3 harness/analysis.py runs/<selected_run> > results/main.md

# Separately recorded sensitivity, when justified
python3 harness/study.py --main --variant <label>
```

Keep the frozen plan unchanged while interpreting its results; record later changes and rationales separately. The freeze records file hashes, not recovered copies of old code. See [kit provenance](../../study-protocol/references/reproducibility.md) for the record format and [reporting guidance](../../study-protocol/references/reporting.md) for using the evidence available. Passing the kit's checks does not establish human correspondence.
