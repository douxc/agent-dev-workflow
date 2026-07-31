#!/usr/bin/env python3
"""Stop hook for the plan-dev-tasks workflow.

Fires once per turn end. Warns (via additionalContext, which continues the
conversation) when a task's lifecycle is in a state the Coordinator may not
end normally in, or when an approved task was never dispatched. Each
lifecycle value is warned about at most once, recorded in a sidecar marker
under the task directory, so the warning cannot loop every turn. Fail-soft:
the user can always exit regardless.

Silence (no output) keeps the normal flow.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from lib import state as S  # noqa: E402


def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except ValueError:
        sys.exit(0)
    cwd = event.get("cwd") or os.getcwd()
    root = S.project_root(cwd)
    warnings = []

    for entry in S.find_states(root):
        data = entry["data"]
        if data is None:
            continue
        lifecycle = data.get("lifecycle")
        if lifecycle in S.ILLEGAL_END_LIFECYCLES:
            marker = os.path.join(entry["task_dir"], ".stop-warned")
            warned = set()
            try:
                warned = set(open(marker, encoding="utf-8").read().splitlines())
            except OSError:
                pass
            if lifecycle in warned:
                continue
            try:
                with open(marker, "a", encoding="utf-8") as handle:
                    handle.write(lifecycle + "\n")
            except OSError:
                pass
            warnings.append(
                "[plan-dev-tasks] 任务 %s 处于 %s 状态，Coordinator 不得正常结束："
                "请继续审查/聚合结果或显式转为 accepted/rework/context-gap/"
                "blocked 后再停止。\n" % (data.get("task_id"), lifecycle)
            )
        elif lifecycle in S.ABANDONED_LIFECYCLES:
            marker = os.path.join(entry["task_dir"], ".stop-warned")
            warned = set()
            try:
                warned = set(open(marker, encoding="utf-8").read().splitlines())
            except OSError:
                pass
            if lifecycle in warned:
                continue
            try:
                with open(marker, "a", encoding="utf-8") as handle:
                    handle.write(lifecycle + "\n")
            except OSError:
                pass
            warnings.append(
                "[plan-dev-tasks] 任务 %s 处于 %s 状态但从未派发 worker："
                "如已放弃请取消任务并清理；否则继续派发。\n"
                % (data.get("task_id"), lifecycle)
            )

    if warnings:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": "".join(warnings),
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
