#!/usr/bin/env python3
"""Merge or unmerge the plan-dev-tasks hook bundle into a Claude Code
settings.json.

usage: install-harden.py merge|unmerge <settings_path> <hooks_dir>

merge:
  - missing settings.json -> created from the bundle fragment;
  - existing file must be strict JSON (JSONC comments are rejected, fail
    closed, file untouched);
  - idempotent: entries are keyed on (event, matcher, command); re-runs
    never duplicate;
  - all other keys (permissions, enableAllProjectMcpServers, ...) preserved.

unmerge:
  - removes only hook entries whose command resolves under <hooks_dir>;
  - drops emptied groups and events;
  - never deletes the settings file.

Exit code 0 on success, 1 on failure with the error on stderr.
"""

import json
import os
import sys

HOOK_COMMAND_PREFIX = "python3 "


def fail(message):
    print("error: %s" % message, file=sys.stderr)
    sys.exit(1)


def fragment(hooks_dir):
    """The hook entries this bundle owns, one group per (event, matcher)."""
    pretool = os.path.join(hooks_dir, "pretool_guard.py")
    stop = os.path.join(hooks_dir, "stop_guard.py")
    groups = [
        ("PreToolUse", "Write", pretool),
        ("PreToolUse", "Edit", pretool),
        ("PreToolUse", "MultiEdit", pretool),
        ("PreToolUse", "Bash", pretool),
        ("PreToolUse", "Agent", pretool),
        ("Stop", None, stop),
    ]
    return [
        {
            "event": event,
            "matcher": matcher,
            "entry": {
                "type": "command",
                "command": "%s%s" % (HOOK_COMMAND_PREFIX, script),
            },
        }
        for event, matcher, script in groups
    ]


def is_bundle_command(command, hooks_dir):
    return command.startswith(HOOK_COMMAND_PREFIX + hooks_dir + os.sep)


def load_settings(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        fail("settings.json is not valid strict JSON (JSONC comments are "
             "not supported); file untouched: %s: %s" % (path, error))
    if not isinstance(data, dict):
        fail("settings.json root must be an object: %s" % path)
    return data


def save_settings(path, data):
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as error:
        fail("cannot write settings.json: %s: %s" % (path, error))


def group_matches(group, matcher):
    if matcher is None:
        return "matcher" not in group
    return group.get("matcher") == matcher


def merge(settings_path, hooks_dir):
    hooks_dir = os.path.realpath(hooks_dir)
    if not os.path.isdir(hooks_dir):
        fail("hook bundle directory does not exist: %s" % hooks_dir)
    data = load_settings(settings_path)
    hooks = data.get("hooks")
    if hooks is None:
        hooks = {}
        data["hooks"] = hooks
    if not isinstance(hooks, dict):
        fail("settings.json 'hooks' must be an object: %s" % settings_path)

    for item in fragment(hooks_dir):
        event, matcher, entry = item["event"], item["matcher"], item["entry"]
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            fail("settings.json 'hooks.%s' must be a list: %s"
                 % (event, settings_path))
        target_group = None
        for group in groups:
            if isinstance(group, dict) and group_matches(group, matcher):
                target_group = group
                break
        if target_group is None:
            new_group = {"hooks": [entry]}
            if matcher is not None:
                new_group["matcher"] = matcher
            groups.append(new_group)
            continue
        hook_list = target_group.setdefault("hooks", [])
        if not isinstance(hook_list, list):
            fail("settings.json hook group 'hooks' must be a list: %s"
                 % settings_path)
        if not any(isinstance(h, dict) and h.get("command") == entry["command"]
                   for h in hook_list):
            hook_list.append(entry)
    save_settings(settings_path, data)


def unmerge(settings_path, hooks_dir):
    hooks_dir = os.path.realpath(hooks_dir)
    data = load_settings(settings_path)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict) or not hooks:
        print("unmerge: nothing to remove (no hooks section)")
        return
    changed = False
    for event in list(hooks):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            if not isinstance(group, dict):
                kept_groups.append(group)
                continue
            hook_list = group.get("hooks")
            if not isinstance(hook_list, list):
                kept_groups.append(group)
                continue
            kept_hooks = [
                h for h in hook_list
                if not (isinstance(h, dict)
                        and is_bundle_command(h.get("command", ""), hooks_dir))
            ]
            if len(kept_hooks) != len(hook_list):
                changed = True
            if kept_hooks:
                group["hooks"] = kept_hooks
                kept_groups.append(group)
            elif hook_list:
                changed = True
        if kept_groups != groups:
            changed = True
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]
    if not hooks:
        del data["hooks"]
    if changed:
        save_settings(settings_path, data)
        print("unmerge: removed bundle hook entries from %s" % settings_path)
    else:
        print("unmerge: no bundle hook entries found in %s" % settings_path)


def main():
    if len(sys.argv) != 4:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    action, settings_path, hooks_dir = sys.argv[1:]
    if action == "merge":
        merge(settings_path, hooks_dir)
    elif action == "unmerge":
        unmerge(settings_path, hooks_dir)
    else:
        fail("unknown action: %s (expected merge or unmerge)" % action)


if __name__ == "__main__":
    main()
