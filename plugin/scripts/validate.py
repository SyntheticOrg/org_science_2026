#!/usr/bin/env python3
"""Structural checks for the synthetic-organisations plugin (standard library only).

Adapted from WRITING_INSTRUCTIONS/scripts/validate.py. Checks the manifests of both hosts, every skill's frontmatter
and agents/openai.yaml (user-invoked skills must be user-invoked in both hosts), the challenge modules, relative
links, the hook configuration and the house style (no em dashes), then runs the hook's and the kit's self-tests.
Usage: python3 scripts/validate.py [--quick]   (--quick skips the kit self-test)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "synthetic-organisations"
USER_INVOKED = {"study-map", "design-study"}
MODEL_INVOKED = {"setup-synthetic-organisations", "study-protocol", "validity-audit", "simulation-harness"}
MODULES = {f"{f}{n}" for f, k in (("A", 5), ("B", 7), ("C", 2), ("D", 4)) for n in range(1, k + 1)}
LINK = re.compile(r"\]\(([^)#\s]+\.(?:md|py|json))(?:#[^)]*)?\)")
PROSE = ["README.md", *[p.relative_to(ROOT).as_posix() for p in (ROOT / "skills").rglob("*.md")]]
errors = []


def fail(msg):
    errors.append(msg)


def load(rel):
    try:
        return json.loads((ROOT / rel).read_text())
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read {rel}: {e}")
        return {}


def frontmatter(path):
    text = path.read_text()
    if not text.startswith("---\n") or text.count("---\n") < 2:
        fail(f"{path.relative_to(ROOT)}: no YAML frontmatter")
        return {}
    return dict(line.split(":", 1) for line in text.split("---\n", 2)[1].splitlines() if ":" in line)


def main():
    claude, codex = load(".claude-plugin/plugin.json"), load(".codex-plugin/plugin.json")
    for label, m in (("Claude", claude), ("Codex", codex)):
        if m.get("name") != NAME:
            fail(f"{label} manifest name is not {NAME}")
    if claude.get("version") != codex.get("version"):
        fail("Claude and Codex manifest versions differ")
    if codex.get("skills") != "./skills/":
        fail("Codex manifest must point to ./skills/")
    for label, rel in (("Claude", ".claude-plugin/marketplace.json"), ("Codex", ".agents/plugins/marketplace.json")):
        plugins = load(rel).get("plugins", [])
        if len(plugins) != 1 or plugins[0].get("name") != NAME:
            fail(f"{label} marketplace must list exactly the {NAME} plugin")

    found = {p.name for p in (ROOT / "skills").iterdir() if p.is_dir()}
    if found != USER_INVOKED | MODEL_INVOKED:
        fail(f"skills found {sorted(found)}, expected {sorted(USER_INVOKED | MODEL_INVOKED)}")
    for name in sorted(found):
        skill = ROOT / "skills" / name / "SKILL.md"
        if not skill.is_file():
            fail(f"missing skills/{name}/SKILL.md")
            continue
        meta = {k.strip(): v.strip() for k, v in frontmatter(skill).items()}
        if not set(meta) <= {"name", "description", "disable-model-invocation"} or meta.get("name") != name or not meta.get("description"):
            fail(f"skills/{name}/SKILL.md: frontmatter must hold name (= folder), description, and optionally disable-model-invocation")
        if len(skill.read_text().splitlines()) > 500:
            fail(f"skills/{name}/SKILL.md exceeds 500 lines")
        yaml = ROOT / "skills" / name / "agents" / "openai.yaml"
        if not yaml.is_file() or "display_name:" not in yaml.read_text():
            fail(f"skills/{name}/agents/openai.yaml missing or without display_name")
            continue
        user = meta.get("disable-model-invocation") == "true"
        if user != (name in USER_INVOKED) or user != ("allow_implicit_invocation: false" in yaml.read_text()):
            fail(f"skills/{name}: invocation must match in SKILL.md and openai.yaml ({'user' if name in USER_INVOKED else 'model'}-invoked)")

    modules = {p.name.split("-")[0] for p in (ROOT / "skills" / "validity-audit" / "references" / "modules").glob("*.md")}
    if modules != MODULES:
        fail(f"challenge modules found {sorted(modules)}, expected {sorted(MODULES)}")

    for rel in PROSE:
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing {rel}")
            continue
        text = path.read_text()
        if "\u2014" in text:  # em dash
            fail(f"{rel}: contains an em dash")
        for target in LINK.findall(text):
            if "://" not in target and not (path.parent / target).resolve().is_file():
                fail(f"{rel}: broken link {target}")

    hooks = ROOT / "hooks" / "hooks.json"
    if hooks.exists() and (load("hooks/hooks.json") and codex.get("hooks") != "./hooks/hooks.json"):
        fail("Codex manifest must reference ./hooks/hooks.json")

    tests = [(ROOT / "hooks", ["study_guard.py", "--test"])]
    if "--quick" not in sys.argv:
        tests.append((ROOT / "skills" / "simulation-harness" / "kit", ["test_kit.py"]))
    for cwd, cmd in tests:
        r = subprocess.run([sys.executable, *cmd], cwd=cwd, capture_output=True, text=True)
        if r.returncode:
            fail(f"{cmd[0]} self-test failed:\n{r.stdout[-1500:]}{r.stderr[-1500:]}")

    if errors:
        print("\n".join(f"ERROR: {e}" for e in errors), file=sys.stderr)
        sys.exit(1)
    print(f"OK: {NAME} {codex['version']} ({len(found)} skills, {len(modules)} modules)")


if __name__ == "__main__":
    main()
