#!/usr/bin/env bash

set -eo pipefail

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
declared=()
while IFS= read -r path; do
    [ -n "$path" ] || continue
    duplicate=0
    for item in "${declared[@]}"; do
        if [ "$item" = "$path" ]; then
            duplicate=1
            break
        fi
    done
    [ "$duplicate" -eq 1 ] || declared+=("$path")
done < <(awk '
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
[ "${#declared[@]}" -gt 0 ] ||
    die "scope file has no files: section: $scope_path"

# Git paths are NUL-delimited so quoting, Unicode, whitespace, and embedded
# newlines cannot change path identity. Bash is required for NUL-safe `read`.
changed=()
while IFS= read -r -d '' path; do
    case "$path" in
        .tmp | .tmp/*) continue ;;
    esac
    duplicate=0
    for item in "${changed[@]}"; do
        if [ "$item" = "$path" ]; then
            duplicate=1
            break
        fi
    done
    [ "$duplicate" -eq 1 ] || changed+=("$path")
done < <(
    git -C "$root" diff --name-only -z "$base"
    git -C "$root" ls-files --others --exclude-standard -z
)

# Staged changes are already in the changed set; surface them as a warning.
while IFS= read -r -d '' path; do
    case "$path" in
        .tmp | .tmp/*) continue ;;
    esac
    printf 'staged: %s\n' "$path"
done < <(git -C "$root" diff --cached --name-only -z "$base")

out_of_scope=()
for path in "${changed[@]}"; do
    found=0
    for item in "${declared[@]}"; do
        if [ "$item" = "$path" ]; then
            found=1
            break
        fi
    done
    [ "$found" -eq 1 ] || out_of_scope+=("$path")
done

if [ "${#out_of_scope[@]}" -gt 0 ]; then
    for path in "${out_of_scope[@]}"; do
        printf 'out-of-scope %s\n' "$path"
    done
    printf 'scope-check: FAIL (%s out-of-scope files)\n' \
        "${#out_of_scope[@]}"
    exit 1
fi

# Declared but unchanged — informational only.
for path in "${declared[@]}"; do
    found=0
    for item in "${changed[@]}"; do
        if [ "$item" = "$path" ]; then
            found=1
            break
        fi
    done
    [ "$found" -eq 1 ] || printf 'unchanged %s\n' "$path"
done

printf 'scope-check: PASS (%s changed, %s declared)\n' \
    "${#changed[@]}" "${#declared[@]}"
exit 0
