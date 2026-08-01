#!/usr/bin/env bash

set -euo pipefail

readonly SKILL_NAMES="plan-tdd-tasks blind-review-tasks"
readonly AGENT_NAMES="plan-tdd-tasks blind-review-tasks"
readonly PLATFORM_NAMES=".claude .claudeD .claudeP"
readonly LEGACY_SKILLS="plan-dev-tasks dev-with-tdd"
readonly LEGACY_AGENTS="plan-dev-tasks dev-with-tdd"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

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

if [ $# -gt 0 ]; then
  fail "unknown argument: $1"
fi

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

# Validate every platform container up front, before any deletion or copy, so
# a blocking path in one platform never causes partial mutation of another.
for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  [ -d "$platform_root" ] || continue
  platform_skills="$platform_root/skills"
  if is_blocking_file "$platform_skills"; then
    fail "platform skills path is not a directory: $platform_skills"
  fi
  platform_agents="$platform_root/agents"
  if is_blocking_file "$platform_agents"; then
    fail "platform agents path is not a directory: $platform_agents"
  fi
done

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

for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  if [ ! -d "$platform_root" ]; then
    printf 'skip %s (platform root missing)\n' "$platform_root"
    continue
  fi

  remove_legacy_into "$platform_root"
  install_skills_into "$platform_root"
  install_agents_into "$platform_root"
done

printf 'done: installed paired skills from %s\n' "$SCRIPT_DIR"
