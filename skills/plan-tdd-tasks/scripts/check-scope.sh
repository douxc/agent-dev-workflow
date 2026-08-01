#!/bin/sh

set -eu

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

project_root=
scope_file=
base=HEAD

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root)
            [ "$#" -ge 2 ] || die "missing value for --project-root"
            project_root=$2
            shift 2
            ;;
        --scope-file)
            [ "$#" -ge 2 ] || die "missing value for --scope-file"
            scope_file=$2
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

[ -n "$project_root" ] || die "check-scope requires --project-root"
[ -n "$scope_file" ] || die "check-scope requires --scope-file"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)

case "$scope_file" in
    /*) scope_path=$scope_file ;;
    *) scope_path=$root/$scope_file ;;
esac
[ -f "$scope_path" ] || die "scope file not found: $scope_path"

git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "not a Git worktree: $root"
git -C "$root" rev-parse --verify "$base^{commit}" >/dev/null 2>&1 ||
    die "invalid base revision: $base"

# Declared set: `- ` items under the `files:` and `infra:` sections. Any other
# marker line (task:, base:, 约束:, ...) ends the current section.
declared=$(awk '
/^files:$/ { section = "files"; next }
/^infra:$/ { section = "infra"; next }
/^[^[:space:]]+:/ { section = ""; next }
/^[[:space:]]*-[[:space:]]/ {
    if (section == "files" || section == "infra") {
        sub(/^[[:space:]]*-[[:space:]]*/, "")
        print
    }
}
' "$scope_path")
[ -n "$declared" ] || die "scope file has no files: section: $scope_path"

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

# Changed set: working-tree diff vs base (includes staged) plus untracked,
# minus anything under .tmp/ unconditionally (defense in depth).
{
    git -C "$root" diff --name-only "$base"
    git -C "$root" ls-files --others --exclude-standard
} | sort -u | while IFS= read -r path; do
    case "$path" in
        .tmp | .tmp/*) ;;
        *) printf '%s\n' "$path" ;;
    esac
done >"$tmpdir/changed"

printf '%s\n' "$declared" | sort -u >"$tmpdir/declared"

# Staged changes are already in the changed set; surface them as a warning.
git -C "$root" diff --cached --name-only "$base" | sort -u |
    while IFS= read -r path; do
        case "$path" in
            .tmp | .tmp/*) ;;
            *) printf 'staged: %s\n' "$path" ;;
        esac
    done

comm -23 "$tmpdir/changed" "$tmpdir/declared" >"$tmpdir/out-of-scope"
if [ -s "$tmpdir/out-of-scope" ]; then
    while IFS= read -r path; do
        printf 'out-of-scope %s\n' "$path"
    done <"$tmpdir/out-of-scope"
    count=$(wc -l <"$tmpdir/out-of-scope" | tr -d ' ')
    printf 'scope-check: FAIL (%s out-of-scope files)\n' "$count"
    exit 1
fi

# Declared but unchanged — informational only.
comm -13 "$tmpdir/changed" "$tmpdir/declared" | while IFS= read -r path; do
    printf 'unchanged %s\n' "$path"
done

changed_count=$(wc -l <"$tmpdir/changed" | tr -d ' ')
declared_count=$(wc -l <"$tmpdir/declared" | tr -d ' ')
printf 'scope-check: PASS (%s changed, %s declared)\n' \
    "$changed_count" "$declared_count"
exit 0
