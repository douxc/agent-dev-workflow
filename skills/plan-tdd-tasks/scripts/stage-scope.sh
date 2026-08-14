#!/usr/bin/env bash

# Commit closeout gate (skill §9, step 2 — run after the full-suite gate
# PASSes). Executes the whole closeout mechanically in one script: defensive
# branch recheck (main/master refused), HEAD == base, check-scope re-run,
# test gate, precise `git add` of the changed set (provably within the scope
# declaration), staged == changed verification, exactly one commit, and a
# clean-tree recheck (`.tmp/` excluded).
#
# The test gate reads test-command.txt from the package: literal `SKIP` means
# the user already consented to skip test execution (§3.5); otherwise
# `<package>/../full-tests.log` must end with `run-full-tests: PASS`.
#
#   --project-root <dir>   git worktree root
#   --package <dir>        package directory (scope.md + test-command.txt)
#   --base <rev>           base revision
#   --branch <branch>      expected feature branch (main/master refused)
#   --message <msg>        commit message (composed by the main agent)
#
# Exit 0 = stage-scope: PASS (commit <sha>)
# Exit 1 = stage-scope: FAIL (...)
# Exit 2 = usage/validation error (stderr)

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

fail() {
    printf 'stage-scope: FAIL (%s)\n' "$*"
    exit 1
}

project_root=
package=
base=
branch=
message=

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
        --branch)
            [ "$#" -ge 2 ] || die "missing value for --branch"
            branch=$2
            shift 2
            ;;
        --message)
            [ "$#" -ge 2 ] || die "missing value for --message"
            message=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "stage-scope requires --project-root"
[ -n "$package" ] || die "stage-scope requires --package"
[ -n "$base" ] || die "stage-scope requires --base"
[ -n "$branch" ] || die "stage-scope requires --branch"
[ -n "$message" ] || die "stage-scope requires --message"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)
case "$package" in
    /*) package_dir=$package ;;
    *) package_dir=$root/$package ;;
esac
[ -f "$package_dir/scope.md" ] || die "scope file not found: $package_dir/scope.md"
[ -f "$package_dir/test-command.txt" ] || die "test-command file not found: $package_dir/test-command.txt"

git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "not a Git worktree: $root"

self_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)

# 1. Defensive branch recheck: on the expected feature branch, never main.
current_branch=$(git -C "$root" branch --show-current)
[ "$current_branch" = "$branch" ] ||
    fail "branch $current_branch != expected $branch"
case "$branch" in
    main | master) fail "refusing to commit on protected branch $branch" ;;
esac

# 2. HEAD == base recheck.
head_rev=$(git -C "$root" rev-parse HEAD)
base_rev=$(git -C "$root" rev-parse --verify "$base^{commit}") ||
    die "invalid base revision: $base"
[ "$head_rev" = "$base_rev" ] || fail "HEAD != base ($base)"

# 3. Scope recheck (skill §6 check-scope.sh gate).
if ! "$self_dir/check-scope.sh" --project-root "$root" \
    --scope-file "$package_dir/scope.md" --base "$base"; then
    fail "scope recheck failed"
fi

# 4. Test gate: literal SKIP = user consent; otherwise full-tests.log must
# end with "run-full-tests: PASS".
test_cmd=$(tr -d '\n\r' <"$package_dir/test-command.txt")
if [ "$test_cmd" = "SKIP" ]; then
    printf 'test gate: SKIP (user consent)\n'
else
    log_file="$package_dir/../full-tests.log"
    [ -f "$log_file" ] || fail "full-tests.log missing: $log_file"
    last_line=$(awk 'NF { sub(/[[:space:]]+$/, ""); last = $0 } END { print last }' \
        "$log_file")
    [ "$last_line" = "run-full-tests: PASS" ] ||
        fail "test gate failed: log does not end with run-full-tests: PASS"
fi

# 5. Precise add: stage exactly the changed set (check-scope PASSed above, so
# the changed set is provably within the scope declaration).
changed=()
while IFS= read -r -d '' record; do
    [ -n "$record" ] || continue
    changed+=("${record#*|}")
done < <("$self_dir/check-scope.sh" --project-root "$root" --base "$base" \
    --list-changed)
if [ "${#changed[@]}" -eq 0 ]; then
    fail "nothing to stage"
fi
if ! git -C "$root" add -- "${changed[@]}"; then
    fail "git add failed"
fi

# 6. Staged == changed verification: no undeclared staging, no missed change.
# Both sides are sorted with `sort -z` (git emits each source sorted; the
# changed set interleaves M and N sources) so path identity stays NUL-safe.
staged=()
while IFS= read -r -d '' path; do
    case "$path" in
        .tmp | .tmp/*) continue ;;
    esac
    staged+=("$path")
done < <(git -C "$root" diff --cached --name-only -z)

staged_sorted=()
while IFS= read -r -d '' path; do
    staged_sorted+=("$path")
done < <(printf '%s\0' "${staged[@]}" | sort -z)
changed_sorted=()
while IFS= read -r -d '' path; do
    changed_sorted+=("$path")
done < <(printf '%s\0' "${changed[@]}" | sort -z)

mismatch=0
if [ "${#staged_sorted[@]}" -ne "${#changed_sorted[@]}" ]; then
    mismatch=1
else
    for i in "${!staged_sorted[@]}"; do
        [ "${staged_sorted[$i]}" = "${changed_sorted[$i]}" ] || mismatch=1
    done
fi
if [ "$mismatch" -eq 1 ]; then
    fail "staged set != changed set"
fi

# 7. Exactly one commit (message is composed by the main agent).
if ! commit_out=$(git -C "$root" commit -m "$message" 2>&1); then
    fail "git commit failed: $commit_out"
fi
commit_sha=$(git -C "$root" rev-parse HEAD)

# 8. Clean-tree recheck (`.tmp/` unconditionally excluded).
leftover=$(git -C "$root" status --porcelain |
    awk '!/^.. \.tmp(\/|$)/ { print }')
[ -z "$leftover" ] ||
    fail "working tree not clean: $(printf '%s' "$leftover" | tr '\n' ' ')"

printf 'stage-scope: PASS (commit %s)\n' "$commit_sha"
exit 0
