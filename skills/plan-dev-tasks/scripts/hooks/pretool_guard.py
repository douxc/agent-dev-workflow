#!/usr/bin/env python3
"""PreToolUse enforcement hook for the plan-dev-tasks workflow.

Reads the Claude Code PreToolUse event JSON from stdin and prints a deny
decision only when a rule fires; otherwise prints nothing (silence keeps the
normal permission flow). Never approves anything.

Rules (see references/claude-code-flow.md 强制层):
  1. state-file protection: no direct writes to .tmp/<task-id>/state.json.
  2. business-write: worker writes only inside its packet's allowed_write_paths
     while authorized/running; the main thread never writes business paths
     while a task is active (coordinator_direct_write), and never writes into
     a parallel worker's worktree.
  3. git-owner: state-changing git commands must go through the bundled runner.
  4. dispatch-gate (best effort): Agent(dev-with-tdd) only after the gate.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from lib import state as S  # noqa: E402

HOOK_DIR = os.path.dirname(os.path.realpath(__file__))
RUNNER_PATH = S.find_runner_path(HOOK_DIR)

TOOL_NAME = "PreToolUse"


def deny(reason, message):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": TOOL_NAME,
            "permissionDecision": "deny",
            "permissionDecisionReason": "%s: %s" % (reason, message),
        }
    }))
    sys.exit(0)


def _active_states(states):
    """Live states (or corrupt placeholders) driving the enforcement."""
    return states


def decide_write(root, states, target, agent_type):
    is_worker = agent_type == "dev-with-tdd"

    # 1. state-file protection: only the runner may write state.json.
    for entry in states:
        if target == entry["state_file"]:
            deny("state_file_protection",
                 "direct write to state.json is not allowed: %s" % target)

    # A corrupt state file disables verification: fail closed.
    corrupt = [e for e in states if e["data"] is None]

    # 2. worker writes: inside the packet allowlist only.
    if is_worker:
        for entry in states:
            data = entry["data"]
            if data is None:
                continue
            if data.get("lifecycle") not in S.ACTIVE_WORKER_TASK_LIFECYCLES:
                continue
            for packet in data.get("packets", []):
                worktree = packet.get("worktree")
                if not worktree:
                    continue
                wroot = os.path.realpath(worktree)
                if S._under(target, wroot):
                    rel = os.path.relpath(target, wroot)
                    for allowed in packet.get("allowed_write_paths", []):
                        if rel == allowed or rel.startswith(allowed + "/"):
                            return
                    deny("worker_write_outside_packet",
                         "worker write outside allowed paths: %s" % rel)
        if corrupt:
            deny("worker_write_outside_packet",
                 "cannot verify worker write against corrupt state")
        deny("worker_write_outside_packet",
             "worker writes are limited to packet allowed paths")
        return

    # 3. main thread: the task workspace (.tmp/<task-id>/) is always allowed,
    # except the worktrees/ subtree which belongs to parallel workers.
    for entry in states:
        worktrees_root = os.path.join(entry["task_dir"], "worktrees")
        if S._under(target, worktrees_root):
            continue
        if S._under(target, entry["task_dir"]):
            return

    # 4. main thread business paths: only after persistence is done.
    for entry in states:
        data = entry["data"]
        if data is None:
            continue
        for packet in data.get("packets", []):
            worktree = packet.get("worktree")
            if not worktree:
                continue
            wroot = os.path.realpath(worktree)
            if wroot == os.path.realpath(entry["data"]["project_root"]):
                continue
            if S._under(target, wroot):
                if data.get("lifecycle") in S.WRITE_ALLOWED_MAIN_LIFECYCLES:
                    return
                deny("coordinator_direct_write",
                     "main thread writing into worker worktree")
    if corrupt:
        deny("coordinator_direct_write",
             "cannot verify main-thread write against corrupt state")
    if all(entry["data"] is not None and
           entry["data"].get("lifecycle") in S.WRITE_ALLOWED_MAIN_LIFECYCLES
           for entry in states):
        return
    deny("coordinator_direct_write",
         "approval grants no write authority; dispatch the worker instead")


def decide_bash(root, states, command, agent_type):
    try:
        parts = S.shlex.split(command)
    except ValueError:
        return
    if S.is_runner_invocation(parts, RUNNER_PATH):
        return
    if parts and parts[0] == "git":
        subcommand, detail = S.git_subcommand(parts[1:], root)
        if not S.git_command_allowed(subcommand, detail):
            deny("git_owner_violation",
                 "state-changing git must go through the bundled runner: %s"
                 % subcommand)
        # Read-only git never writes; skip the write heuristic below.
        return
    for raw_target in S.bash_write_targets(command):
        target = S.resolve_target(root, raw_target)
        decide_write(root, states, target, agent_type)


def decide_agent(root, states, tool_input):
    subagent_type = tool_input.get("subagent_type") or ""
    prompt = tool_input.get("prompt") or ""
    if subagent_type != "dev-with-tdd" and \
            "Required skill: dev-with-tdd" not in prompt:
        return
    if not states:
        deny("dispatch_mode_mismatch",
             "worker dispatch without any task state file")
    for entry in states:
        data = entry["data"]
        if data is None:
            continue
        lifecycle = data.get("lifecycle")
        if lifecycle == "prepared" and \
                data.get("gate", {}).get("status") == "passed":
            return
        if lifecycle in ("context-gap", "rework"):
            return
    deny("dispatch_mode_mismatch",
         "worker dispatch requires prepared state with gate passed")


def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except ValueError:
        sys.exit(0)
    tool_name = event.get("tool_name") or ""
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd") or os.getcwd()
    agent_type = event.get("agent_type") or ""
    root = S.project_root(cwd)
    states = S.find_states(root)

    # The dispatch gate is NOT dormant without state: dispatching a worker
    # with no task state at all is itself a protocol violation.
    if tool_name == "Agent":
        decide_agent(root, states, tool_input)
        sys.exit(0)
    if not states:
        sys.exit(0)

    if tool_name in ("Write", "Edit", "MultiEdit"):
        target_raw = tool_input.get("file_path") or tool_input.get("path")
        if not target_raw:
            sys.exit(0)
        decide_write(root, states, S.resolve_target(root, target_raw),
                     agent_type)
    elif tool_name == "Bash":
        command = tool_input.get("command") or ""
        if command:
            decide_bash(root, states, command, agent_type)
    sys.exit(0)


if __name__ == "__main__":
    main()
