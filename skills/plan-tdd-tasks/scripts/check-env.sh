#!/usr/bin/env bash

# Environment preparation gate (run once, after planning and before TDD).
# Verifies the three environment invariants hold so work can begin on a clean
# temp branch at the recorded base. Non-mutating: the main agent creates the
# branch; this script only confirms it is safe to start coding.
#
#   --project-root <dir>   repository root (must be a Git worktree)
#   --base <rev>           the commit recorded during analysis (branch startpoint)
#   --branch <name>        the declared task branch (must not be main/master)
#
# Exit 0 = env-check: PASS   (on declared branch, clean tree, HEAD == base)
# Exit 1 = env-check: FAIL   (an environment invariant is broken)
# Exit 2 = usage error

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

project_root=
base=HEAD
branch=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root)
            [ "$#" -ge 2 ] || die "missing value for --project-root"
            project_root=$2
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
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "check-env requires --project-root"
[ -n "$branch" ] || die "check-env requires --branch"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)

# A protected branch cannot be the declared task branch.
case "$branch" in
    main|master) die "declared branch is protected: $branch" ;;
esac

git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "not a Git worktree: $root"
git -C "$root" rev-parse --verify "$base^{commit}" >/dev/null 2>&1 ||
    die "invalid base revision: $base"

base_commit=$(git -C "$root" rev-parse "$base^{commit}")

# Invariant A: the current branch is the declared task branch.
current_branch=$(git -C "$root" rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "$branch" ]; then
    printf 'env-check: FAIL (current branch %s != declared %s)\n' \
        "$current_branch" "$branch"
    exit 1
fi

# Invariant B: the working tree is clean apart from .tmp/ (planning artifacts).
# Tracked changes vs HEAD plus untracked files, NUL-delimited for exact matching.
tree_dirty=0
while IFS= read -r -d '' path; do
    case "$path" in
        .tmp | .tmp/*) continue ;;
    esac
    tree_dirty=1
    break
done < <(
    git -C "$root" diff --name-only -z HEAD
    git -C "$root" ls-files --others --exclude-standard -z
)
if [ "$tree_dirty" -eq 1 ]; then
    printf 'env-check: FAIL (working tree not clean)\n'
    exit 1
fi

# Invariant C: HEAD sits at the recorded base (no commits started yet).
head_commit=$(git -C "$root" rev-parse HEAD)
if [ "$head_commit" != "$base_commit" ]; then
    printf 'env-check: FAIL (HEAD advanced past base)\n'
    exit 1
fi

printf 'env-check: PASS (branch %s at base)\n' "$branch"
exit 0
