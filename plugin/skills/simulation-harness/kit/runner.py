"""Runner: runs the groups of a study and keeps the research record (standard library only).

Kit file of the synthetic-organisations plugin, generalised from third-test/harness/runner.py. The study module
(harness/study.py) defines TREATMENTS, FOCAL, MODEL, EFFORT and run_group(group), and calls runner.main(study):

    python3 harness/study.py --fake                          # every treatment once, no API calls
    python3 harness/study.py --treatments A --groups 3        # non-focal pilot; no private notes by default
    python3 harness/study.py --calibration --treatments A B  # refuses focal treatments
    python3 harness/study.py --freeze --groups 30            # writes FREEZE.json and stops; then commit and tag
    python3 harness/study.py --main                          # the frozen settings and files only
    python3 harness/study.py --main --variant short-chat     # a labelled variant, run on all treatments

Each run folder holds config.json (settings, model, file hashes, provenance) and one JSON record per group, failures
included. Every launch is appended to runs/ledger.jsonl when it starts and when it ends, so an aborted run shows a
start without an end. Rerunning into an existing --out folder resumes it and refuses changed settings.
"""

import argparse
import hashlib
import json
import platform
import random
import re
import subprocess
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import agent

SETTINGS = ("treatments", "groups", "first_group", "seed", "backend", "model", "effort", "effort_mix", "url", "revision")


class Group:
    """What run_group receives: the treatment, group number, seeded random streams and the model."""

    def __init__(self, treatment, number, seed, model, notes, effort_mix):
        self.treatment, self.number, self.notes, self.model, self.effort_mix = treatment, number, notes, model, effort_mix
        self.seed = f"{seed}-{treatment}-{number}"
        self.rng = random.Random(self.seed)
        self.efforts = {}

    def stream(self, name):
        """An independent random stream, so that switching one feature (personas, efforts) leaves the other draws unchanged."""
        return random.Random(f"{self.seed}-{name}")

    def model_for(self, role):
        """The model for one participant; with an effort mix, an effort drawn for this participant (module B3)."""
        if not self.effort_mix:
            return self.model
        self.efforts[role] = self.stream(f"effort-{role}").choice(self.effort_mix)
        return self.model.with_effort(self.efforts[role])


def git(root, *cmd):
    try:
        return subprocess.run(["git", "-C", str(root), *cmd], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def frozen_files(root):
    """Freeze the harness and consolidated study plan, including a separate legacy analysis plan when present."""
    files = [p for p in sorted((root / "harness").rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    return files + [root / name for name in ("APPROACH.md", "analysis_plan.md") if (root / name).is_file()]


def hashes(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in frozen_files(root)}


def provenance(root):
    """git state of the frozen files and of FREEZE.json, kit version and environment."""
    paths = [p.relative_to(root).as_posix() for p in frozen_files(root)] + ["FREEZE.json"] * (root / "FREEZE.json").exists()
    status = git(root, "status", "--porcelain", "--", *paths) if paths else ""
    return {"git_commit": git(root, "rev-parse", "HEAD") or None,
            "uncommitted": sorted(line[3:] for line in status.splitlines()),
            "kit_version": agent.KIT_VERSION, "python": sys.version.split()[0], "platform": platform.platform(),
            "argv": sys.argv}


def ledger(root, entry):
    (root / "runs").mkdir(exist_ok=True)
    with open(root / "runs" / "ledger.jsonl", "a") as f:
        f.write(json.dumps({"time": agent.now(), **entry}) + "\n")


def record_name(treatment, number):
    return f"{re.sub(r'[^A-Za-z0-9_.-]', '-', treatment)}-{number:03d}.json"


def records(run_dir):
    """The group records of a run folder, in file order."""
    for p in sorted(Path(run_dir).glob("*-[0-9][0-9][0-9].json")):
        yield json.loads(p.read_text())


def run_one(study, group, out_dir):
    started = agent.now()
    try:
        rec = study.run_group(group)
    except Exception as e:  # a bug in the study code: keep a record of it
        rec = {"status": "error", "error": repr(e), "traceback": traceback.format_exc()}
    rec = {"treatment": group.treatment, "group": group.number, "seed": group.seed, "notes": group.notes,
           "efforts": group.efforts or None, "started": started, "status": "unknown", **rec, "finished": agent.now()}
    path = out_dir / record_name(group.treatment, group.number)
    path.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    return path, rec


def main(study, argv=None):
    root = Path(study.__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=(study.__doc__ or "").split("\n")[0])
    ap.add_argument("--treatments", nargs="+", help="treatment codes, or 'all' (default)")
    ap.add_argument("--groups", type=int, help="groups per treatment (default 1)")
    ap.add_argument("--first-group", type=int, help="number of the first group, to add or rerun groups (default 1)")
    ap.add_argument("--seed", type=int, help="default 1")
    ap.add_argument("--backend", choices=("openai", "chat"), help="openai (default) or an OpenAI-compatible chat endpoint")
    ap.add_argument("--model")
    ap.add_argument("--effort")
    ap.add_argument("--effort-mix", nargs="+", help="draw each participant's reasoning effort from these (module B3)")
    ap.add_argument("--url", help="chat endpoint URL (backend chat)")
    ap.add_argument("--revision", help="pinned checkpoint the chat endpoint serves, recorded for replicability")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--notes", action="store_true", help="a private note on the reason with every reply (pilots only)")
    ap.add_argument("--fake", action="store_true", help="schema-valid random replies, no API calls")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--calibration", action="store_true", help="refuses focal treatments")
    mode.add_argument("--freeze", action="store_true", help="write FREEZE.json for the main run and stop")
    mode.add_argument("--main", action="store_true", help="run with the frozen settings and files")
    ap.add_argument("--variant", metavar="LABEL", help="a labelled departure from the frozen design (sensitivity condition)")
    ap.add_argument("--out", type=Path, help="run folder (default runs/<time>-<mode>); an existing one is resumed")
    args = ap.parse_args(argv)

    defaults = {"treatments": ["all"], "groups": 1, "first_group": 1, "seed": 1, "backend": "openai",
                "model": getattr(study, "MODEL", None), "effort": getattr(study, "EFFORT", None), "effort_mix": None,
                "url": None, "revision": None}
    given = {k: getattr(args, k) for k in SETTINGS if getattr(args, k) is not None}
    files = hashes(root)
    prov = provenance(root)

    if args.freeze:
        settings = defaults | given
        (root / "FREEZE.json").write_text(json.dumps({"frozen_at": agent.now(), "settings": settings, "files": files,
                                                      "git_commit": prov["git_commit"]}, indent=1))
        print("Wrote FREEZE.json with frozen settings and file hashes.")
        return None
    if args.main:
        if not (root / "FREEZE.json").exists():
            sys.exit("--main refused: no FREEZE.json. Run --freeze first.")
        frozen = json.loads((root / "FREEZE.json").read_text())
        changed = sorted(k for k, v in given.items() if frozen["settings"].get(k) != v)
        edited = sorted(k for k in set(frozen["files"]) | set(files) if frozen["files"].get(k) != files.get(k))
        if (changed or edited) and not args.variant:
            sys.exit("--main refused: the frozen design changed.\n"
                     + "".join(f"  {label}: {', '.join(x)}\n" for label, x in
                               (("settings", changed), ("files", edited)) if x)
                     + "Restore the frozen state, re-run --freeze, or run the change as a labelled variant "
                       "(--variant LABEL).")
        if args.notes:
            sys.exit("--main refused: private notes are for pilots only (module B7).")
        settings = frozen["settings"] | given
    else:
        settings = defaults | given

    treatments = list(study.TREATMENTS) if settings["treatments"] == ["all"] else settings["treatments"]
    unknown = set(treatments) - set(study.TREATMENTS)
    if unknown:
        sys.exit(f"unknown treatments: {sorted(unknown)}")
    if args.calibration and set(treatments) & set(study.FOCAL):
        sys.exit(f"--calibration refused: {sorted(set(treatments) & set(study.FOCAL))} are focal treatments. "
                 "Calibrate only on conditions without them.")

    mode_name = "main" if args.main else "calibration" if args.calibration else "pilot"
    if args.fake:
        model = None
    elif settings["backend"] == "chat":
        model = agent.ChatModel(settings["model"], settings["url"] or "http://127.0.0.1:8000/v1/chat/completions",
                                settings=getattr(study, "CHAT_SETTINGS", {}), revision=settings["revision"],
                                key=agent.env_key("CHAT_API_KEY", required=False))
    else:
        model = agent.OpenAIModel(settings["model"], settings["effort"])

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{mode_name}" + (f"-{args.variant}" if args.variant else "") \
        + ("-fake" if args.fake else "")
    out_dir = args.out or root / "runs" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    config = {"run_id": run_id, "mode": mode_name, "variant": args.variant, "fake": args.fake, "notes": args.notes,
              "settings": settings, "model": model.describe() if model else {"backend": "fake"}, "files": files,
              "instructions": (root / "harness" / "instructions.md").read_text()
              if (root / "harness" / "instructions.md").exists() else None,
              "provenance": prov, "started": agent.now()}
    jobs = [(t, g) for t in treatments for g in range(settings["first_group"], settings["first_group"] + settings["groups"])]
    if (out_dir / "config.json").exists():  # resume: never mix settings, never overwrite a record
        old = json.loads((out_dir / "config.json").read_text())
        differ = [k for k in ("mode", "variant", "fake", "notes", "settings", "model", "files") if old[k] != config[k]]
        if differ:
            sys.exit(f"{out_dir} was run with other {', '.join(differ)}; use a new --out.")
        jobs = [(t, g) for t, g in jobs if not (out_dir / record_name(t, g)).exists()]
        print(f"resuming {out_dir}: {len(jobs)} groups without a record", flush=True)
    else:
        (out_dir / "config.json").write_text(json.dumps(config, indent=1, ensure_ascii=False))

    ledger(root, {"event": "start", "run_id": run_id, "dir": out_dir.relative_to(root).as_posix() if out_dir.is_relative_to(root)
                  else str(out_dir), "mode": mode_name, "variant": args.variant, "fake": args.fake, "groups": len(jobs),
                  "git_commit": prov["git_commit"]})
    t0, done = time.time(), {}
    with ThreadPoolExecutor(args.workers) as pool:
        futures = [pool.submit(run_one, study, Group(t, g, settings["seed"], model or agent.FakeModel(f"{settings['seed']}-{t}-{g}"),
                                                     args.notes, settings["effort_mix"]), out_dir) for t, g in jobs]
        for f in as_completed(futures):
            path, rec = f.result()
            done[rec["status"]] = done.get(rec["status"], 0) + 1
            print(f"{path.name}: {rec['status']}" + (f": {rec.get('error')}" if rec["status"] != "complete" else ""), flush=True)
    ledger(root, {"event": "end", "run_id": run_id, "statuses": done})
    print(f"done in {time.time() - t0:.0f}s -> {out_dir}")
    return out_dir
