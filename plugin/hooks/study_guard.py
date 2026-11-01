"""Guard hook for synthetic-organisation studies (PreToolUse on Edit, Write and apply_patch; standard library only).

Works in Claude Code and Codex: both send the tool call as JSON on stdin, block on exit code 2 with the reason on
stderr, and accept hookSpecificOutput.additionalContext for a note that does not block. Claude Code names the file in
tool_input.file_path; Codex reports edits as apply_patch with the patch text in tool_input.command.

- Run records (config.json, group records, ledger, probe and coding files under runs/) are written by code only:
  edits are blocked at any time.
- When FREEZE.json exists, edits to frozen harness/plan files pass with a reminder to use a labelled variant
  (--variant LABEL) or document a revised design before a new freeze.
- Before a freeze, once live pilot runs exist, edits to harness files pass with a reminder to log the change.

STUDY_GUARD_LOG=<file> appends every payload to that file, to check what a host sends. --test runs the self-test.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

RECORD = re.compile(r"(^|/)(config\.json|ledger\.jsonl|probe\.jsonl|coding\.json|[^/]*-\d{3}\.json)$")
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$|^\*\*\* Move to: (.+)$", re.M)


def targets(payload):
    """Absolute paths the tool call would change."""
    tool, inp, cwd = payload.get("tool_name"), payload.get("tool_input") or {}, Path(payload.get("cwd") or ".")
    if tool in ("Edit", "Write") and inp.get("file_path"):
        paths = [inp["file_path"]]
    elif tool == "apply_patch":
        command = inp.get("command", "")
        text = command if isinstance(command, str) else "\n".join(map(str, command))
        paths = [a or b for a, b in PATCH_FILE.findall(text)]
    else:
        paths = []
    return [(cwd / p.strip()).resolve() for p in paths]


def study_root(path):
    for d in path.parents:
        if (d / "APPROACH.md").is_file() and (d / "harness").is_dir():
            return d
    return None


def live_pilots(root):
    ledger = root / "runs" / "ledger.jsonl"
    return ledger.exists() and any(
        e.get("event") == "start" and not e.get("fake") for e in map(json.loads, ledger.read_text().splitlines()))


def decide(payload):
    """(exit code, stderr text, stdout JSON or None)."""
    notes = []
    for path in targets(payload):
        root = study_root(path)
        if not root:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("runs/") and RECORD.search(rel):
            return 2, (f"{rel} is part of the run record of {root.name} and is written by the harness only. "
                       "Rerun or add a labelled variant instead of editing a record."), None
        freeze = root / "FREEZE.json"
        if freeze.exists() and rel in json.loads(freeze.read_text()).get("files", {}):
            notes.append(f"{rel} is listed in {root.name}/FREEZE.json. Run this change as a labelled variant "
                         "(--main --variant LABEL), keeping the original plan and recording the rationale in results/. "
                         "For a revised main design, document the changes in APPROACH.md before a new --freeze; "
                         "earlier focal inspection remains exploratory.")
        elif not freeze.exists() and rel.startswith("harness/") and live_pilots(root):
            notes.append(f"Live pilot runs exist for {root.name}: note this change to {rel} and its reason in "
                         "APPROACH.md before the next run.")
    if notes:
        return 0, "", {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": " ".join(notes)}}
    return 0, "", None


def main():
    raw = sys.stdin.read()
    if os.environ.get("STUDY_GUARD_LOG"):
        with open(os.environ["STUDY_GUARD_LOG"], "a") as f:
            f.write(raw.strip() + "\n")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0  # not a tool call this hook understands: let the host's own rules apply
    code, err, out = decide(payload)
    if out:
        print(json.dumps(out))
    if err:
        print(err, file=sys.stderr)
    return code


def test():
    root = Path(tempfile.mkdtemp()) / "study"
    (root / "harness").mkdir(parents=True)
    (root / "runs" / "r1").mkdir(parents=True)
    (root / "APPROACH.md").write_text("spec\n")
    edit = lambda p: {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": str(root / p)}}
    patch = lambda p: {"hook_event_name": "PreToolUse", "tool_name": "apply_patch", "cwd": str(root),
                       "tool_input": {"command": f"*** Begin Patch\n*** Update File: {p}\n@@\n-a\n+b\n*** End Patch\n"}}
    assert decide(edit("harness/instructions.md")) == (0, "", None)  # nothing frozen, no pilots
    assert decide(edit("runs/r1/config.json"))[0] == 2 and decide(patch("runs/ledger.jsonl"))[0] == 2
    (root / "runs" / "ledger.jsonl").write_text(json.dumps({"event": "start", "fake": False}) + "\n")
    code, _, out = decide(patch("harness/instructions.md"))
    assert code == 0 and "note this change" in out["hookSpecificOutput"]["additionalContext"]
    (root / "FREEZE.json").write_text(json.dumps({"files": {"harness/instructions.md": "x", "APPROACH.md": "y"}}))
    code, _, out = decide(edit("harness/instructions.md"))
    assert code == 0 and "--variant LABEL" in out["hookSpecificOutput"]["additionalContext"]
    code, _, out = decide(patch("APPROACH.md"))
    assert code == 0 and "revised main design" in out["hookSpecificOutput"]["additionalContext"]
    assert decide(edit("results/main.md")) == (0, "", None)  # not frozen, not a record
    assert decide({"tool_name": "Bash", "tool_input": {"command": "ls"}}) == (0, "", None)
    print("study_guard: all checks passed")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        sys.exit(main())
