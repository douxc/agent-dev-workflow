"""Shared state discovery and decision helpers for the plan-dev-tasks hooks.

The hooks are restrictive-only: they only ever DENY tool calls; silence keeps
the user's normal permission flow. All decisions are derived from the state
file(s) the runner owns at ``${PROJECT_ROOT}/.tmp/<task-id>/state.json``
(see references/state-file.md). No state file -> hooks are dormant.
"""

import json
import os
import shlex
import subprocess


LIFECYCLES = [
    "approved", "prepared", "dispatched", "authorized", "running",
    "handoff-received", "reviewing", "accepted", "rework",
    "context-gap", "blocked", "committed", "finalized",
]

# States in which a worker is allowed to write inside its packet allowlist.
# Packet lifecycles move independently in L3 packages, so the task lifecycle
# is the reliable execution-window signal; packet.lifecycle is informational.
ACTIVE_WORKER_TASK_LIFECYCLES = {"authorized", "running", "rework"}

# Main-thread business writes are only allowed once persistence is done
# (review finished, commits made, pre-cleanup).
WRITE_ALLOWED_MAIN_LIFECYCLES = {"accepted", "committed", "finalized"}

# Stop-hook warnings: ending normally is illegal in these states.
ILLEGAL_END_LIFECYCLES = {"dispatched", "running", "handoff-received",
                          "reviewing"}
# Approved-but-never-dispatched tasks are flagged as abandoned.
ABANDONED_LIFECYCLES = {"approved", "prepared"}

# Git subcommands that never change state, matched on the subcommand token.
GIT_READ_ONLY = {
    "status", "diff", "log", "show", "rev-parse", "rev-list", "merge-base",
    "cat-file", "ls-remote", "check-ignore", "ls-files", "blame", "grep",
    "shortlog", "count-objects", "describe", "name-rev", "version", "help",
}
# Subcommands that are read-only only with specific arguments.
GIT_READ_ONLY_BRANCH_ARGS = {"--show-current", "--list", "-a", "--all",
                             "-r", "--remotes", "-v", "--verbose", "-vv"}
GIT_READ_ONLY_REMOTE_VERBS = {"get-url", "show"}
GIT_READ_ONLY_CONFIG_ARGS = {"--get", "--list", "--get-regexp"}
GIT_WORKTREE_READ_ONLY_ARGS = {"list"}

# Bash write-verb heuristic: the first non-flag token after these verbs is a
# write target. This is a first line only; the deterministic backstops remain
# the gate's `verify --require-clean` and the runner's explicit-path `commit`.
BASH_WRITE_VERBS = {"touch", "mkdir", "rm", "mv", "cp", "tee", "install", "ln"}


def project_root(cwd):
    """Resolve the main worktree root of the repo containing `cwd`.

    Uses `git worktree list --porcelain` so a parallel worker's cwd (inside a
    linked worktree under .tmp/) still resolves to the main root where the
    .tmp/ directory lives. Falls back to the canonical cwd for non-Git
    workspaces.
    """
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        if out.returncode == 0:
            for line in out.stdout.splitlines():
                if line.startswith("worktree "):
                    return os.path.realpath(line[len("worktree "):])
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.realpath(cwd)


def load_state_file(path):
    try:
        data = json.loads(open(path, encoding="utf-8").read())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return None
    return data


def find_states(root):
    """Return one entry per existing state.json under ``root/.tmp/*/``.

    Each entry is a dict with keys ``data`` (parsed state or None when
    corrupt), ``task_dir`` (canonical task directory), and ``state_file``.
    A corrupt file is treated as deny-worthy by the decision rules.
    """
    states = []
    tmp_dir = os.path.join(root, ".tmp")
    try:
        entries = os.listdir(tmp_dir)
    except OSError:
        return states
    for name in sorted(entries):
        task_dir = os.path.realpath(os.path.join(tmp_dir, name))
        if not os.path.isdir(task_dir):
            continue
        state_file = os.path.join(task_dir, "state.json")
        if not os.path.isfile(state_file):
            continue
        states.append({
            "data": load_state_file(state_file),
            "task_dir": task_dir,
            "state_file": os.path.realpath(state_file),
        })
    return states


def resolve_target(root, raw_target):
    if os.path.isabs(raw_target):
        return os.path.realpath(raw_target)
    return os.path.realpath(os.path.join(root, raw_target))


def _under(target, base):
    return target == base or target.startswith(base + os.sep)


def find_runner_path(hook_dir):
    """Canonical path of the bundled git-workflow.sh next to the hooks dir."""
    return os.path.realpath(os.path.join(hook_dir, os.pardir, "git-workflow.sh"))


def is_runner_invocation(parts, runner_path):
    """True when the Bash command invokes the bundled runner directly."""
    if not parts:
        return False
    first = parts[0]
    if first in ("sh", "bash") and len(parts) > 1:
        first = parts[1]
    if not os.path.isabs(first) and not os.path.exists(first):
        return False
    try:
        if os.path.islink(first):
            return False
        return os.path.realpath(first) == runner_path
    except OSError:
        return False


def bash_write_targets(command):
    """Heuristic extraction of file-write targets from a Bash command."""
    try:
        parts = shlex.split(command)
    except ValueError:
        return []
    targets = []
    for index, part in enumerate(parts):
        if part == ">" and index + 1 < len(parts):
            targets.append(parts[index + 1])
        elif part.startswith(">") and not part.startswith(">>") and len(part) > 1:
            targets.append(part[1:])
        elif part in BASH_WRITE_VERBS:
            positional = [
                p for p in parts[index + 1:]
                if not p.startswith("-") and p != ">" and not p.startswith(">")
            ]
            if not positional:
                continue
            if part in ("cp", "mv"):
                # For copy/move the destination is the last positional.
                targets.append(positional[-1])
            else:
                targets.append(positional[0])
        elif part == "sed" and index + 2 < len(parts) and parts[index + 1] == "-i":
            targets.append(parts[index + 2])
    return targets


def git_subcommand(parts, root):
    """Return (subcommand, detail) for a Bash git invocation, or None.

    `-C <path>` pointing at a different repository marks the command as out
    of scope: returns ("__out_of_scope__", None). `detail` is the first
    positional argument after the subcommand where relevant.
    """
    index = 0
    while index < len(parts):
        token = parts[index]
        if token in ("-C", "--git-dir", "--work-tree"):
            if token == "-C" and index + 1 < len(parts):
                target = os.path.realpath(parts[index + 1])
                if target != root:
                    return ("__out_of_scope__", None)
                index += 2
                continue
            index += 2
            continue
        if token == "-c" and index + 2 < len(parts):
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        detail = parts[index + 1] if index + 1 < len(parts) else None
        return (token, detail)
    return (None, None)


def git_command_allowed(subcommand, detail):
    """True when the parsed git subcommand is read-only."""
    if subcommand in ("__out_of_scope__", None):
        return True
    if subcommand in GIT_READ_ONLY:
        return True
    if subcommand == "branch":
        return detail in GIT_READ_ONLY_BRANCH_ARGS or detail is None
    if subcommand == "remote":
        return detail is None or detail in GIT_READ_ONLY_REMOTE_VERBS
    if subcommand == "config":
        return detail in GIT_READ_ONLY_CONFIG_ARGS
    if subcommand == "worktree":
        return detail in GIT_WORKTREE_READ_ONLY_ARGS
    return False
