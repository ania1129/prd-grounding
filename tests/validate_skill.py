#!/usr/bin/env python3
"""Validate the prd-grounding skill package.

Checks structure, frontmatter, referenced files, PRD template sections, and runs
the two bundled scripts (inventory + state/gate machine) as functional tests.

Usage:
    python3 tests/validate_skill.py
    python3 tests/validate_skill.py --json
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(ROOT, "SKILL.md")

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "agents/openai.yaml",
    "assets/prd-template.md",
    "assets/checkpoint-template.md",
    "references/workflow.md",
    "references/code-scan-checklist.md",
    "references/solution-design.md",
    "references/generation-rules.md",
    "scripts/scan_codebase.py",
    "scripts/prd_state.py",
    "examples/example-requirement.md",
    "examples/example-walkthrough.md",
    ".github/workflows/validate.yml",
]

PRD_REQUIRED_HEADINGS = [
    "背景与目标",
    "用户与场景",
    "目标与提升指标",
    "需求内容",
    "数据验证",
    "权限与安全",
    "术语表",
]


def run(cmd, cwd=None, timeout=120):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def check_structure():
    errors = []
    for rel in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(ROOT, rel)):
            errors.append("missing file: %s" % rel)
    return errors


def check_frontmatter():
    errors = []
    if not os.path.isfile(SKILL_MD):
        return ["SKILL.md not found"]
    with open(SKILL_MD, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return ["SKILL.md must start with YAML frontmatter (---)"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return ["SKILL.md frontmatter is not closed with ---"]
    block = "\n".join(lines[1:end])
    if "name: prd-grounding" not in block:
        errors.append("frontmatter missing name: prd-grounding")
    if "description:" not in block:
        errors.append("frontmatter missing description")
    if "license:" not in block:
        errors.append("frontmatter missing license")
    return errors


def check_template():
    errors = []
    path = os.path.join(ROOT, "assets/prd-template.md")
    if not os.path.isfile(path):
        return ["assets/prd-template.md not found"]
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for heading in PRD_REQUIRED_HEADINGS:
        if heading not in text:
            errors.append("PRD template missing heading: %s" % heading)
    return errors


def check_references_exist():
    errors = []
    with open(SKILL_MD, "r", encoding="utf-8") as handle:
        text = handle.read()
    for rel in [
        "references/workflow.md",
        "references/code-scan-checklist.md",
        "references/solution-design.md",
        "references/generation-rules.md",
        "assets/prd-template.md",
        "assets/checkpoint-template.md",
        "scripts/scan_codebase.py",
        "scripts/prd_state.py",
    ]:
        if rel in text and not os.path.isfile(os.path.join(ROOT, rel)):
            errors.append("SKILL.md references missing file: %s" % rel)
    return errors


def check_scan_script():
    errors = []
    script = os.path.join(ROOT, "scripts/scan_codebase.py")
    proc = run([sys.executable, script, "--root", ROOT, "--format", "json"])
    if proc.returncode != 0:
        return ["scan_codebase.py exited %d: %s" % (proc.returncode, proc.stderr.strip()[:400])]
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return ["scan_codebase.py output is not JSON: %s" % exc]
    if data.get("total_files", 0) <= 0:
        errors.append("scan_codebase.py scanned no files")
    for key in ("languages", "manifests", "routes", "tests", "docs"):
        if key not in data:
            errors.append("scan_codebase.py JSON missing key: %s" % key)
    help_proc = run([sys.executable, script, "--help"])
    if help_proc.returncode != 0:
        errors.append("scan_codebase.py --help failed")
    return errors


def check_state_machine():
    errors = []
    script = os.path.join(ROOT, "scripts", "prd_state.py")
    with tempfile.TemporaryDirectory() as tmp:
        ws = os.path.join(tmp, "ws")

        def call(*args):
            return run([sys.executable, script] + list(args))

        if call("--help").returncode != 0:
            errors.append("prd_state.py --help failed")
            return errors
        if call("init", "--root", ws, "--slug", "demo", "--title", "Demo").returncode != 0:
            errors.append("prd_state.py init failed")
            return errors
        # Not ready right after init.
        if call("check", "--root", ws).returncode == 0:
            errors.append("check should not pass right after init")
        # Gate must fail before prerequisites.
        if call("gate", "--root", ws, "--gate", "solution-choice", "--result", "passed").returncode == 0:
            errors.append("gate passed before prerequisite stages")
        for stage in ("01-requirement", "02-analysis", "03-goals-metrics",
                      "04-code-baseline", "05-solution-options"):
            if call("set", "--root", ws, "--stage", stage, "--status", "done").returncode != 0:
                errors.append("set stage failed: %s" % stage)
        if call("gate", "--root", ws, "--gate", "solution-choice", "--result", "passed",
                "--note", "方案A").returncode != 0:
            errors.append("solution-choice gate should pass after prerequisites")
        # The old second gate no longer exists.
        if call("gate", "--root", ws, "--gate", "open-questions", "--result", "passed").returncode == 0:
            errors.append("open-questions gate should no longer be accepted")
        for stage in ("07-approach", "08-flows-open-questions", "09-decision-log"):
            call("set", "--root", ws, "--stage", stage, "--status", "done")
        # Still not ready without final PRD.
        if call("check", "--root", ws, "--require-final").returncode == 0:
            errors.append("check --require-final passed without PRD.md")
        with open(os.path.join(ws, "PRD.md"), "w", encoding="utf-8") as handle:
            handle.write("# Demo PRD\n")
        call("set", "--root", ws, "--stage", "PRD", "--status", "done")
        if call("check", "--root", ws, "--require-final").returncode != 0:
            errors.append("check --require-final should pass with all stages and both gates")
    return errors


def check_examples_mention_workflow():
    errors = []
    path = os.path.join(ROOT, "examples/example-walkthrough.md")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        for marker in ("阶段 1", "阶段 5", "检查点 2", "自动决策", "PRD"):
            if marker not in text:
                errors.append("example-walkthrough.md missing marker: %s" % marker)
    return errors


CHECKS = [
    ("structure", check_structure),
    ("frontmatter", check_frontmatter),
    ("prd-template", check_template),
    ("references", check_references_exist),
    ("scan-script", check_scan_script),
    ("state-machine", check_state_machine),
    ("examples", check_examples_mention_workflow),
]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the prd-grounding skill package.")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args(argv)

    results = []
    total_errors = 0
    for name, func in CHECKS:
        try:
            errors = func()
        except Exception as exc:  # noqa: BLE001 - report any failure
            errors = ["check crashed: %r" % exc]
        status = "PASS" if not errors else "FAIL"
        total_errors += len(errors)
        results.append({"check": name, "status": status, "errors": errors})
        if not args.json:
            print("[%s] %s" % (status, name))
            for error in errors:
                print("       - %s" % error)

    if args.json:
        print(json.dumps({"ok": total_errors == 0, "results": results}, ensure_ascii=False, indent=2))
    else:
        print("")
        print("RESULT: %s (%d error(s))" % ("PASS" if total_errors == 0 else "FAIL", total_errors))
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
