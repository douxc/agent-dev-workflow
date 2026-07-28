#!/usr/bin/env bash

set -euo pipefail

readonly SKILL_NAMES="plan-dev-tasks dev-with-tdd"
readonly PLATFORM_NAMES=".claude .claudeD .claudeP .codex .hermes"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

path_exists() {
  [ -e "$1" ] || [ -L "$1" ]
}

next_backup_path() {
  local target="$1"
  local base="${target}.backup.$(date '+%Y%m%d%H%M%S').$$"
  local candidate="$base"
  local suffix=0

  while path_exists "$candidate"; do
    suffix=$((suffix + 1))
    candidate="${base}.${suffix}"
  done

  printf '%s\n' "$candidate"
}

backup_existing() {
  local target="$1"
  local backup

  if ! path_exists "$target"; then
    return
  fi

  backup="$(next_backup_path "$target")"
  mv "$target" "$backup"
  printf 'backup %s -> %s\n' "$target" "$backup"
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
readonly CANONICAL_ROOT="$HOME_DIR/.agents/skills"

for skill in $SKILL_NAMES; do
  if [ ! -d "$SOURCE_ROOT/$skill" ] || [ ! -f "$SOURCE_ROOT/$skill/SKILL.md" ]; then
    fail "source skill is missing or incomplete: $SOURCE_ROOT/$skill"
  fi
done

for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  platform_skills="$platform_root/skills"
  if [ -d "$platform_root" ] && path_exists "$platform_skills" && [ ! -d "$platform_skills" ]; then
    fail "platform skills path is not a directory: $platform_skills"
  fi
done

mkdir -p "$CANONICAL_ROOT"
staging_dir="$(mktemp -d "$CANONICAL_ROOT/.install.XXXXXX")"

cleanup_staging() {
  if [ -n "${staging_dir:-}" ] && [ -d "$staging_dir" ]; then
    case "$staging_dir" in
      "$CANONICAL_ROOT"/.install.*) rm -rf "$staging_dir" ;;
    esac
  fi
}
trap cleanup_staging EXIT HUP INT TERM

for skill in $SKILL_NAMES; do
  cp -R "$SOURCE_ROOT/$skill" "$staging_dir/$skill"
done

for skill in $SKILL_NAMES; do
  canonical_target="$CANONICAL_ROOT/$skill"
  backup_existing "$canonical_target"
  mv "$staging_dir/$skill" "$canonical_target"
  printf 'install %s\n' "$canonical_target"
done

rmdir "$staging_dir"
staging_dir=""

for platform in $PLATFORM_NAMES; do
  platform_root="$HOME_DIR/$platform"
  if [ ! -d "$platform_root" ]; then
    printf 'skip %s (platform root missing)\n' "$platform_root"
    continue
  fi

  platform_skills="$platform_root/skills"
  mkdir -p "$platform_skills"

  for skill in $SKILL_NAMES; do
    canonical_target="$CANONICAL_ROOT/$skill"
    link_target="$platform_skills/$skill"

    if [ -L "$link_target" ] && [ "$(readlink "$link_target")" = "$canonical_target" ]; then
      printf 'keep %s\n' "$link_target"
      continue
    fi

    backup_existing "$link_target"
    ln -s "$canonical_target" "$link_target"
    printf 'link %s -> %s\n' "$link_target" "$canonical_target"
  done
done

printf 'done: installed paired skills from %s\n' "$SCRIPT_DIR"
