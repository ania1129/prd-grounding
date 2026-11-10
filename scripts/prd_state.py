#!/usr/bin/env python3
"""Track PRD grounding stages, the solution gate and final readiness.

Dependency-free: uses only the Python 3 standard library.

Pipeline: ten stages with exactly ONE hard gate — the product manager's solution
choice. After that choice, every remaining open question is auto-decided by the
skill and recorded in the decision log, so the final PRD does not wait for a
second human confirmation.

Examples:
    python3 prd_state.py init --root prd-workspace/order-refund --slug order-refund --title "订单部分退款"
    python3 prd_state.py status --root prd-workspace/order-refund
    python3 prd_state.py next --root prd-workspace/order-refund
    python3 prd_state.py gate --root prd-workspace/order-refund --gate solution-choice --result passed --note "方案B"
    python3 prd_state.py check --root prd-workspace/order-refund --require-final
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SKILL = "prd-grounding"
VERSION = "0.2.0"
STATE_FILE = "state.json"

# (key, label, artifact) in pipeline order.
STAGES = [
    ("01-requirement", "需求理解", "01-requirement.md"),
    ("02-analysis", "需求分析", "02-analysis.md"),
    ("03-goals-metrics", "目标与提升指标", "03-goals-metrics.md"),
    ("04-code-baseline", "结合历史代码", "04-code-baseline.md"),
    ("05-solution-options", "解决方案候选", "05-solution-options.md"),
    ("06-solution-decision", "方案选择（唯一硬门禁）", "06-solution-decision.md"),
    ("07-approach", "解决方式（详细设计）", "07-approach.md"),
    ("08-flows-open-questions", "逆向流程与候选待确认", "08-flows-open-questions.md"),
    ("09-decision-log", "自动决策记录（skill 决定）", "09-decision-log.md"),
    ("PRD", "完整版 PRD", "PRD.md"),
]
STAGE_KEYS = [item[0] for item in STAGES]
STAGE_LABELS = {item[0]: item[1] for item in STAGES}
STAGE_ARTIFACTS = {item[0]: item[2] for item in STAGES}

GATE_STAGE = {"solution-choice": "06-solution-decision"}

STAGE_STATUSES = ("pending", "in_progress", "blocked", "done")
GATE_RESULTS = ("pending", "passed")

PRE_GATE = ["01-requirement", "02-analysis", "03-goals-metrics", "04-code-baseline", "05-solution-options"]
POST_GATE = ["07-approach", "08-flows-open-questions", "09-decision-log"]

LEGACY_STAGE_RENAMES = {"09-confirmation-log": "09-decision-log"}


def now():
    return datetime.now(timezone.utc).isoformat()


def state_path(root):
    return os.path.join(root, STATE_FILE)


def normalize_state(state):
    """Upgrade state written by older versions (second gate / renamed artifact)."""
    stages = state.setdefault("stages", {})
    for old_key, new_key in LEGACY_STAGE_RENAMES.items():
        if old_key in stages and new_key not in stages:
            stages[new_key] = stages.pop(old_key)
            stages[new_key]["path"] = STAGE_ARTIFACTS[new_key]
    for key in STAGE_KEYS:
        stages.setdefault(key, {"status": "pending", "path": STAGE_ARTIFACTS[key], "updated_at": None})
    gates = state.setdefault("gates", {})
    gates.setdefault("solution-choice", {"result": "pending", "note": "", "updated_at": None})
    # The old second gate no longer exists; drop it to avoid confusion.
    gates.pop("open-questions", None)
    state.setdefault("checkpoints", {})
    state.setdefault("skill", SKILL)
    state["version"] = VERSION
    return state


def load_state(root):
    path = state_path(root)
    if not os.path.isfile(path):
        raise SystemExit("state.json not found in %s (run `init` first)" % root)
    with open(path, "r", encoding="utf-8") as handle:
        return normalize_state(json.load(handle))


def save_state(root, state):
    state["updated_at"] = now()
    with open(state_path(root), "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def default_state(slug, title, repo):
    return {
        "skill": SKILL,
        "version": VERSION,
        "slug": slug,
        "title": title,
        "repo": repo,
        "created_at": now(),
        "updated_at": now(),
        "current_stage": STAGE_KEYS[0],
        "stages": {key: {"status": "pending", "path": STAGE_ARTIFACTS[key], "updated_at": None} for key in STAGE_KEYS},
        "gates": {"solution-choice": {"result": "pending", "note": "", "updated_at": None}},
        "checkpoints": {"checkpoint-1": {"status": "pending", "note": "", "updated_at": None}},
    }


def first_unfinished(state):
    for key in STAGE_KEYS:
        if state["stages"][key]["status"] != "done":
            return key
    return None


def recompute_current(state):
    for key in STAGE_KEYS:
        if state["stages"][key]["status"] != "done":
            state["current_stage"] = key
            return
    state["current_stage"] = STAGE_KEYS[-1]


def cmd_init(args):
    root = os.path.abspath(args.root)
    os.makedirs(root, exist_ok=True)
    path = state_path(root)
    if os.path.isfile(path) and not args.force:
        raise SystemExit("state.json already exists in %s (use --force to overwrite)" % root)
    state = default_state(args.slug, args.title, args.repo or "")
    save_state(root, state)
    print("initialized %s" % path)
    print("slug=%s title=%s" % (args.slug, args.title))
    print("next: %s (%s)" % (state["current_stage"], STAGE_LABELS[state["current_stage"]]))
    return 0


def cmd_status(args):
    state = load_state(args.root)
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0
    print("slug: %s" % state.get("slug", ""))
    print("title: %s" % state.get("title", ""))
    print("repo: %s" % (state.get("repo") or "(not set)"))
    print("updated: %s" % state.get("updated_at", ""))
    print("")
    print("阶段:")
    for key in STAGE_KEYS:
        stage = state["stages"][key]
        print("  [%-11s] %-28s %s" % (stage["status"], key, STAGE_LABELS[key]))
    print("")
    print("门禁（仅方案选择）:")
    for gate in GATE_STAGE:
        item = state["gates"][gate]
        note = (" -- " + item["note"]) if item.get("note") else ""
        print("  [%-6s] %s%s" % (item["result"], gate, note))
    print("")
    print("检查点:")
    for name, item in state.get("checkpoints", {}).items():
        print("  [%s] %s" % (item.get("status", "pending"), name))
    print("")
    print("下一步: %s" % describe_next(state))
    return 0


def describe_next(state):
    current = first_unfinished(state)
    if current is None:
        return "全部阶段已完成，可运行 check --require-final 做最终自检。"
    if current == "06-solution-decision":
        result = state["gates"]["solution-choice"]["result"]
        if result != "passed":
            return "等待唯一硬门禁 solution-choice：PM 选方案并记录到 06-solution-decision.md"
        return "门禁已通过，补写 06-solution-decision.md 后标记该阶段 done"
    if current == "09-decision-log":
        return "自动决策阶段：按 references/solution-design.md 的决策规则逐条给出结论，写入 09-decision-log.md（不需要 PM 确认）"
    return "继续阶段 %s：%s（产物 %s）" % (current, STAGE_LABELS[current], STAGE_ARTIFACTS[current])


def cmd_next(args):
    state = load_state(args.root)
    print(describe_next(state))
    return 0


def cmd_set(args):
    state = load_state(args.root)
    if args.stage not in STAGE_KEYS:
        raise SystemExit("unknown stage: %s (choose from %s)" % (args.stage, ", ".join(STAGE_KEYS)))
    if args.status not in STAGE_STATUSES:
        raise SystemExit("unknown status: %s (choose from %s)" % (args.status, ", ".join(STAGE_STATUSES)))
    gate = GATE_STAGE.get("solution-choice")
    if args.stage == gate and args.status == "done" and state["gates"]["solution-choice"]["result"] != "passed":
        raise SystemExit("stage %s is gated by solution-choice; pass the gate first" % args.stage)
    state["stages"][args.stage]["status"] = args.status
    state["stages"][args.stage]["updated_at"] = now()
    recompute_current(state)
    save_state(args.root, state)
    print("stage %s -> %s" % (args.stage, args.status))
    print("next: %s" % describe_next(state))
    return 0


def cmd_gate(args):
    state = load_state(args.root)
    if args.gate not in GATE_STAGE:
        raise SystemExit("unknown gate: %s (the only gate is solution-choice)" % args.gate)
    if args.result not in GATE_RESULTS:
        raise SystemExit("unknown result: %s (choose from %s)" % (args.result, ", ".join(GATE_RESULTS)))
    gate_stage = GATE_STAGE[args.gate]
    if args.result == "passed":
        for key in PRE_GATE:
            if state["stages"][key]["status"] != "done":
                raise SystemExit("cannot pass %s: stage %s is not done" % (args.gate, key))
    state["gates"][args.gate]["result"] = args.result
    state["gates"][args.gate]["note"] = args.note or ""
    state["gates"][args.gate]["updated_at"] = now()
    state["stages"][gate_stage]["status"] = "done" if args.result == "passed" else "pending"
    state["stages"][gate_stage]["updated_at"] = now()
    recompute_current(state)
    save_state(args.root, state)
    print("gate %s -> %s" % (args.gate, args.result))
    print("next: %s" % describe_next(state))
    return 0


def cmd_checkpoint(args):
    state = load_state(args.root)
    name = args.name
    state.setdefault("checkpoints", {}).setdefault(name, {"status": "pending", "note": "", "updated_at": None})
    state["checkpoints"][name]["status"] = args.status
    state["checkpoints"][name]["note"] = args.note or ""
    state["checkpoints"][name]["updated_at"] = now()
    save_state(args.root, state)
    print("checkpoint %s -> %s" % (name, args.status))
    return 0


def cmd_check(args):
    state = load_state(args.root)
    errors = []
    warnings = []

    for key in PRE_GATE:
        if state["stages"][key]["status"] != "done":
            errors.append("stage %s (%s) not done" % (key, STAGE_LABELS[key]))
    if state["gates"]["solution-choice"]["result"] != "passed":
        errors.append("gate solution-choice (方案选择) not passed")
    for key in POST_GATE:
        if state["stages"][key]["status"] != "done":
            errors.append("stage %s (%s) not done" % (key, STAGE_LABELS[key]))
    if args.require_final:
        if state["stages"]["PRD"]["status"] != "done":
            errors.append("stage PRD not done")
        if not os.path.isfile(os.path.join(args.root, "PRD.md")):
            errors.append("PRD.md not found in %s" % args.root)

    for key in STAGE_KEYS:
        artifact = STAGE_ARTIFACTS[key]
        if state["stages"][key]["status"] == "done" and not os.path.isfile(os.path.join(args.root, artifact)):
            warnings.append("stage %s marked done but %s is missing" % (key, artifact))

    result = {"ok": not errors, "errors": errors, "warnings": warnings,
              "current_stage": state["current_stage"], "state": state["stages"], "gates": state["gates"]}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if errors:
            print("NOT READY")
            for item in errors:
                print("  ERROR: %s" % item)
        else:
            print("READY")
        for item in warnings:
            print("  WARN: %s" % item)
    return 0 if not errors else 1


def build_parser():
    parser = argparse.ArgumentParser(
        prog="prd_state.py",
        description="Track PRD grounding stages, the solution gate and final readiness.",
        epilog="Only the solution choice is gated; the decision log (stage 09) is auto-decided by the skill.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create a PRD workspace and state.json")
    init.add_argument("--root", required=True, help="workspace directory to create")
    init.add_argument("--slug", required=True, help="short slug, e.g. order-partial-refund")
    init.add_argument("--title", required=True, help="PRD title")
    init.add_argument("--repo", default="", help="code repository path (optional)")
    init.add_argument("--force", action="store_true", help="overwrite an existing state.json")
    init.set_defaults(func=cmd_init)

    status = sub.add_parser("status", help="show stage, gate and checkpoint status")
    status.add_argument("--root", required=True, help="workspace directory")
    status.add_argument("--json", action="store_true", help="print raw state.json")
    status.set_defaults(func=cmd_status)

    nxt = sub.add_parser("next", help="print the next recommended action")
    nxt.add_argument("--root", required=True, help="workspace directory")
    nxt.set_defaults(func=cmd_next)

    mark = sub.add_parser("set", help="mark a stage status")
    mark.add_argument("--root", required=True, help="workspace directory")
    mark.add_argument("--stage", required=True, choices=STAGE_KEYS, help="stage key")
    mark.add_argument("--status", required=True, choices=STAGE_STATUSES, help="new status")
    mark.set_defaults(func=cmd_set)

    gate = sub.add_parser("gate", help="record the solution-choice gate result")
    gate.add_argument("--root", required=True, help="workspace directory")
    gate.add_argument("--gate", required=True, choices=list(GATE_STAGE), help="gate key")
    gate.add_argument("--result", required=True, choices=GATE_RESULTS, help="pending or passed")
    gate.add_argument("--note", default="", help="decision note, e.g. the chosen solution")
    gate.set_defaults(func=cmd_gate)

    checkpoint = sub.add_parser("checkpoint", help="record a soft checkpoint result")
    checkpoint.add_argument("--root", required=True, help="workspace directory")
    checkpoint.add_argument("--name", required=True, help="checkpoint name, e.g. checkpoint-1")
    checkpoint.add_argument("--status", required=True, choices=("pending", "done"), help="checkpoint status")
    checkpoint.add_argument("--note", default="", help="optional note")
    checkpoint.set_defaults(func=cmd_checkpoint)

    check = sub.add_parser("check", help="validate readiness (exit 1 when not ready)")
    check.add_argument("--root", required=True, help="workspace directory")
    check.add_argument("--require-final", action="store_true", help="also require PRD.md to exist")
    check.add_argument("--json", action="store_true", help="print JSON result")
    check.set_defaults(func=cmd_check)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
