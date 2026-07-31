#!/usr/bin/env bash

set -euo pipefail

readonly SKILL_NAMES="plan-dev-tasks dev-with-tdd"
readonly PLATFORM_NAMES=".claude .claudeD .claudeP .hermes"
readonly CLAUDE_PLATFORM_NAMES=".claude .claudeD .claudeP"
readonly CLAUDE_AGENT_NAMES="plan-dev-tasks dev-with-tdd"

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

# Named Hermes profiles to install into, in addition to the default ~/.hermes
# platform root. Validated at parse time so invalid names fail before any check
# or mutation; names are restricted to [A-Za-z0-9._-] with a non-dot start,
# which also guarantees word-splitting safety for the loops below.
HERMES_PROFILES=""
harden_flag=no
unharden_flag=no

while [ $# -gt 0 ]; do
  case "$1" in
    --hermes-profile)
      if [ $# -lt 2 ] || [ -z "$2" ]; then
        fail "--hermes-profile requires a non-empty profile name"
      fi
      if [[ ! "$2" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
        fail "invalid Hermes profile name: $2"
      fi
      HERMES_PROFILES="$HERMES_PROFILES $2"
      shift 2
      ;;
    --harden-claude)
      harden_flag=yes
      shift
      ;;
    --unharden-claude)
      unharden_flag=yes
      shift
      ;;
    *)
      fail "unknown argument: $1"
      ;;
  esac
done

if [ "$harden_flag" = yes ] && [ "$unharden_flag" = yes ]; then
  fail "--harden-claude and --unharden-claude are mutually exclusive"
fi
if [ "$harden_flag" = yes ]; then
  harden_mode=merge
elif [ "$unharden_flag" = yes ]; then
  harden_mode=unmerge
else
  harden_mode=
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
readonly CLAUDE_AGENT_SOURCE_ROOT="$SCRIPT_DIR/adapters/claude-code/agents"

for skill in $SKILL_NAMES; do
  if [ ! -d "$SOURCE_ROOT/$skill" ] || [ ! -f "$SOURCE_ROOT/$skill/SKILL.md" ]; then
    fail "source skill is missing or incomplete: $SOURCE_ROOT/$skill"
  fi
done

for agent in $CLAUDE_AGENT_NAMES; do
  agent_source="$CLAUDE_AGENT_SOURCE_ROOT/$agent.md"
  if [ ! -f "$agent_source" ] || [ ! -s "$agent_source" ]; then
    fail "source Claude Code agent is missing or incomplete: $agent_source"
  fi
done

# Validate every platform container up front, before any deletion or copy, so a
# blocking path in one platform never causes partial mutation of another.
for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  [ -d "$platform_root" ] || continue
  platform_skills="$platform_root/skills"
  if is_blocking_file "$platform_skills"; then
    fail "platform skills path is not a directory: $platform_skills"
  fi
done

for platform in $CLAUDE_PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  [ -d "$platform_root" ] || continue
  platform_agents="$platform_root/agents"
  if is_blocking_file "$platform_agents"; then
    fail "platform agents path is not a directory: $platform_agents"
  fi
done

# Validate every named Hermes profile container up front, before any deletion
# or copy, so a blocking path in one target never causes partial mutation of
# another.
for profile in $HERMES_PROFILES; do
  profile_root="$HOME_DIR/.hermes/profiles/$profile"
  [ -d "$profile_root" ] || continue
  profile_skills="$profile_root/skills"
  if is_blocking_file "$profile_skills"; then
    fail "profile skills path is not a directory: $profile_skills"
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

  for agent in $CLAUDE_AGENT_NAMES; do
    local dest="$platform_agents/$agent.md"
    remove_existing "$dest"
    cp "$CLAUDE_AGENT_SOURCE_ROOT/$agent.md" "$dest"
    printf 'install %s\n' "$dest"
  done
}

for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  if [ ! -d "$platform_root" ]; then
    printf 'skip %s (platform root missing)\n' "$platform_root"
    continue
  fi

  install_skills_into "$platform_root"
done

for platform in $CLAUDE_PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  if [ ! -d "$platform_root" ]; then
    continue
  fi

  install_agents_into "$platform_root"
done

for profile in $HERMES_PROFILES; do
  profile_root="$HOME_DIR/.hermes/profiles/$profile"
  if [ ! -d "$profile_root" ]; then
    printf 'skip %s (profile root missing)\n' "$profile_root"
    continue
  fi

  install_skills_into "$profile_root"
done

if [ -n "$harden_mode" ]; then
  claude_root_found=no
  for platform in $CLAUDE_PLATFORM_NAMES; do
    platform_root="$HOME_DIR/$platform"
    if [ ! -d "$platform_root" ]; then
      continue
    fi
    claude_root_found=yes
    settings_path="$platform_root/settings.json"
    hooks_dir="$platform_root/skills/plan-dev-tasks/scripts/hooks"
    if [ "$harden_mode" = merge ] && [ ! -d "$hooks_dir" ]; then
      fail "hook bundle missing after install: $hooks_dir"
    fi
    python3 "$SCRIPT_DIR/install-harden.py" "$harden_mode" \
      "$settings_path" "$hooks_dir" ||
      fail "harden step failed for $platform_root"
    printf '%s %s\n' "$harden_mode" "$platform_root"
  done
  if [ "$claude_root_found" = no ]; then
    if [ "$harden_mode" = merge ]; then
      fail "--harden-claude requires at least one existing Claude Code platform root"
    else
      fail "--unharden-claude requires at least one existing Claude Code platform root"
    fi
  fi
  if [ "$harden_mode" = merge ]; then
    installed_version=$(claude --version 2>/dev/null || :)
    parsed_version=$(printf '%s\n' "$installed_version" |
      sed -n 's/^\([0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*\).*/\1/p')
    if [ -n "$parsed_version" ]; then
      if python3 -c 'import sys
v = tuple(int(x) for x in sys.argv[1].split("."))
sys.exit(0 if v < (2, 1, 214) else 1)' "$parsed_version"; then
        printf 'warning: Claude Code %s is older than 2.1.214; hook enforcement may be incomplete\n' "$parsed_version" >&2
      fi
    fi
  fi
fi

printf 'done: installed paired skills from %s\n' "$SCRIPT_DIR"
