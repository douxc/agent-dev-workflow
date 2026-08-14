#!/usr/bin/env bash

set -euo pipefail

readonly SKILL_NAMES="plan-tdd-tasks blind-review-tasks"
readonly AGENT_NAMES="plan-tdd-tasks blind-review-tasks"
readonly PLATFORM_NAMES=".claude .claudeP"
readonly HERMES_PROFILES_DIR=".hermes/profiles"
readonly LEGACY_SKILLS="plan-dev-tasks dev-with-tdd"
readonly LEGACY_AGENTS="plan-dev-tasks dev-with-tdd"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

# --- argument parsing ---
# `-p <profile>` selects Hermes profile mode: install into the named Hermes
# profile (~/.hermes/profiles/<profile>/), mutually exclusive with the Claude
# platform install that runs when no -p is given.
profile=
profile_set=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    -p)
      [ "$#" -ge 2 ] || fail "-p requires a profile name"
      profile=$2
      profile_set=1
      shift 2
      ;;
    *) fail "unknown argument: $1" ;;
  esac
done

if [ "$profile_set" -eq 1 ]; then
  case "$profile" in
    ""|*/*|"."|"..") fail "invalid profile name: $profile" ;;
  esac
fi

path_exists() {
  [ -e "$1" ] || [ -L "$1" ]
}

# A container is a regular file (not a dir, not a symlink). Such a path blocks
# installation and must fail closed instead of being silently clobbered.
is_blocking_file() {
  local target="$1"
  path_exists "$target" && [ ! -d "$target" ] && [ ! -L "$target" ]
}

remove_existing() {
  local target="$1"

  if ! path_exists "$target"; then
    return
  fi

  rm -rf "$target"
  printf 'remove %s\n' "$target"
}

if [ -z "${HOME:-}" ]; then
  fail "HOME must be a non-empty absolute directory"
fi

case "$HOME" in
  /*) ;;
  *) fail "HOME must be an absolute directory" ;;
esac

if [ "$HOME" = "/" ] || [ ! -d "$HOME" ]; then
  fail "HOME must be an existing directory other than /"
fi

readonly HOME_DIR="$(CDPATH= cd "$HOME" && pwd -P)"
if [ "$HOME_DIR" = "/" ]; then
  fail "HOME must not resolve to /"
fi

readonly SCRIPT_DIR="$(CDPATH= cd "$(dirname "$0")" && pwd -P)"
readonly SOURCE_ROOT="$SCRIPT_DIR/skills"
readonly AGENT_SOURCE_ROOT="$SCRIPT_DIR/adapters/claude-code/agents"

for skill in $SKILL_NAMES; do
  if [ ! -d "$SOURCE_ROOT/$skill" ] || [ ! -f "$SOURCE_ROOT/$skill/SKILL.md" ]; then
    fail "source skill is missing or incomplete: $SOURCE_ROOT/$skill"
  fi
done

for agent in $AGENT_NAMES; do
  agent_source="$AGENT_SOURCE_ROOT/$agent.md"
  if [ ! -f "$agent_source" ] || [ ! -s "$agent_source" ]; then
    fail "source Claude Code agent is missing or incomplete: $agent_source"
  fi
done

# Build the install targets: either the Hermes profile (skills only — Hermes
# has no .md agent mechanism, subagents are defined at runtime) or the Claude
# platform roots.
targets=()
if [ "$profile_set" -eq 1 ]; then
  ship_agents=0
  targets=("$HOME_DIR/$HERMES_PROFILES_DIR/$profile")
else
  ship_agents=1
  for platform in $PLATFORM_NAMES; do
    targets+=("$HOME_DIR/$platform")
  done
fi

# Validate every target container up front, before any deletion or copy, so
# a blocking path in one platform never causes partial mutation of another.
for target in "${targets[@]}"; do
  [ -d "$target" ] || continue
  target_skills="$target/skills"
  if is_blocking_file "$target_skills"; then
    fail "platform skills path is not a directory: $target_skills"
  fi
  if [ "$ship_agents" -eq 1 ]; then
    target_agents="$target/agents"
    if is_blocking_file "$target_agents"; then
      fail "platform agents path is not a directory: $target_agents"
    fi
  fi
done

# User-level settings merge (plain mode only) must not clobber a blocking
# path: a directory at ~/.claude/settings.json would make the merge fail.
if [ "$profile_set" -eq 0 ] && [ -d "$HOME_DIR/.claude/settings.json" ]; then
  fail "user settings path is not a file: $HOME_DIR/.claude/settings.json"
fi

# Retire the retired .claudeD platform root: it is no longer an install
# target, so an existing root is removed entirely rather than left stale.
# -p mode owns only Hermes profiles and must not touch Claude platform roots.
if [ "$profile_set" -eq 0 ] && path_exists "$HOME_DIR/.claudeD"; then
  remove_existing "$HOME_DIR/.claudeD"
fi

install_skills_into() {
  local platform_root="$1"
  local platform_skills="$platform_root/skills"

  if [ -L "$platform_skills" ]; then
    remove_existing "$platform_skills"
  fi
  mkdir -p "$platform_skills"

  for skill in $SKILL_NAMES; do
    local dest="$platform_skills/$skill"
    remove_existing "$dest"
    cp -R "$SOURCE_ROOT/$skill" "$dest"
    printf 'install %s\n' "$dest"
  done
}

install_agents_into() {
  local platform_root="$1"
  local platform_agents="$platform_root/agents"

  if [ -L "$platform_agents" ]; then
    remove_existing "$platform_agents"
  fi
  mkdir -p "$platform_agents"

  for agent in $AGENT_NAMES; do
    local dest="$platform_agents/$agent.md"
    remove_existing "$dest"
    cp "$AGENT_SOURCE_ROOT/$agent.md" "$dest"
    printf 'install %s\n' "$dest"
  done
}

# Retire the legacy skills/agents from the previous architecture.
remove_legacy_into() {
  local platform_root="$1"
  local platform_skills="$platform_root/skills"
  local platform_agents="$platform_root/agents"

  for legacy in $LEGACY_SKILLS; do
    remove_existing "$platform_skills/$legacy"
  done
  for legacy in $LEGACY_AGENTS; do
    remove_existing "$platform_agents/$legacy.md"
  done
}

# Merge the home read rules into the user-level Claude Code settings
# (~/.claude/settings.json) so skill reference reads never prompt in any
# project. Plain mode only: -p mode owns only Hermes profiles. Skips when
# ~/.claude is missing (same convention as missing platform roots); warns
# when python3 is unavailable; corrupt JSON fails closed unmodified.
merge_user_settings() {
  local settings_dir="$HOME_DIR/.claude"
  local user_settings="$settings_dir/settings.json"

  if [ ! -d "$settings_dir" ]; then
    printf 'skip user settings merge (%s missing)\n' "$settings_dir"
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    printf 'warning: python3 not found; user-level settings merge skipped\n'
    return 0
  fi

  python3 - "$user_settings" <<'PY' || fail "failed to merge user settings: $user_settings"
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
except FileNotFoundError:
    data = {}
except json.JSONDecodeError as exc:
    sys.stderr.write(f"corrupt settings.json: {exc}\n")
    sys.exit(1)

rules = ("Read(~/.claude/**)", "Read(~/.claudeP/**)")
allow = data.setdefault("permissions", {}).setdefault("allow", [])
for rule in rules:
    if rule not in allow:
        allow.append(rule)
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
PY

  printf 'merge user settings %s\n' "$user_settings"
}

for target in "${targets[@]}"; do
  if [ ! -d "$target" ]; then
    printf 'skip %s (platform root missing)\n' "$target"
    continue
  fi

  remove_legacy_into "$target"
  install_skills_into "$target"
  if [ "$ship_agents" -eq 1 ]; then
    install_agents_into "$target"
  fi
done

if [ "$profile_set" -eq 0 ]; then
  merge_user_settings
fi

printf 'done: installed paired skills from %s\n' "$SCRIPT_DIR"
