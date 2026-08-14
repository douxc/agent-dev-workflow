#!/usr/bin/env bash

# Package builder (skill §6, step 2 — run after the check-scope.sh gate
# PASSes). Generates the blind-review package from the changed set, which is
# read from `check-scope.sh --list-changed` so the two scripts share one
# source of truth for what changed:
#
#   diff.txt — `git diff <base>` output; every untracked new file is appended
#              as a `== new: <path> ==` block with its full content
#   code/    — complete copies of all changed files at their repo-relative
#              paths (project-map.md excluded — §11, not a blind-review
#              input; deleted files have no copy, the deletion is visible in
#              diff.txt)
#
#   --project-root <dir>   git worktree root
#   --package <dir>        package directory (diff.txt and code/ are written
#                          inside it)
#   --base <rev>           base revision (same as the scope-check base)
#
# Exit 0 = build-package: PASS (n files, m new)
# Exit 1 = build-package: FAIL (...)   (changed-set read failed)
# Exit 2 = usage/validation error (stderr)

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

project_root=
package=
base=HEAD

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root)
            [ "$#" -ge 2 ] || die "missing value for --project-root"
            project_root=$2
            shift 2
            ;;
        --package)
            [ "$#" -ge 2 ] || die "missing value for --package"
            package=$2
            shift 2
            ;;
        --base)
            [ "$#" -ge 2 ] || die "missing value for --base"
            base=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "build-package requires --project-root"
[ -n "$package" ] || die "build-package requires --package"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)
case "$package" in
    /*) package_dir=$package ;;
    *) package_dir=$root/$package ;;
esac
[ -d "$package_dir" ] || die "package dir not found: $package_dir"

git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "not a Git worktree: $root"

self_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
list_file=$(mktemp) || die "mktemp failed"
trap 'rm -f "$list_file"' EXIT

# The changed-set read failing is a gate failure, not a usage error.
if ! "$self_dir/check-scope.sh" --project-root "$root" --base "$base" \
    --list-changed >"$list_file"; then
    printf 'build-package: FAIL (changed-set read failed)\n'
    exit 1
fi

diff_file="$package_dir/diff.txt"
code_dir="$package_dir/code"

# diff.txt = full diff vs base; untracked new files appended as blocks.
git -C "$root" diff "$base" >"$diff_file"

file_count=0
new_count=0
while IFS= read -r -d '' record; do
    [ -n "$record" ] || continue
    kind=${record%%|*}
    path=${record#*|}
    case "$path" in
        project-map.md) continue ;;
    esac
    file_count=$((file_count + 1))
    if [ "$kind" = "N" ]; then
        new_count=$((new_count + 1))
        {
            printf '== new: %s ==\n' "$path"
            cat "$root/$path"
        } >>"$diff_file"
    fi
    # Complete copies at repo-relative paths; deleted files have no copy
    # (the deletion is visible in diff.txt).
    if [ -f "$root/$path" ]; then
        dest="$code_dir/$path"
        mkdir -p "$(dirname "$dest")"
        cp "$root/$path" "$dest"
    fi
done <"$list_file"

printf 'build-package: PASS (%s files, %s new)\n' "$file_count" "$new_count"
exit 0
