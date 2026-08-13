#!/usr/bin/env bash

# AC grammar gate (run once, after planning and before TDD). Mechanically
# validates ac-list.md against scope.md so the load-bearing wall is checked by
# a machine, not just the main agent's self-review.
#
#   --project-root <dir>   repository root
#   --ac-file <path>       ac-list.md (may be relative to project root)
#   --scope-file <path>    scope.md (may be relative to project root)
#
# Checks:
#   - every AC has 断言 / 归属 / 验证 fields
#   - 验证 ∈ {unit, integration, scripted}
#   - 断言 contains no banned subjective words
#   - every AC 归属 path is in scope files:/infra:
#   - every scope files: path is covered by >=1 AC 归属 or listed in infra:
#
# Exit 0 = ac-check: PASS   Exit 1 = ac-check: FAIL   Exit 2 = usage error

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

project_root=
ac_file=
scope_file=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root)
            [ "$#" -ge 2 ] || die "missing value for --project-root"
            project_root=$2
            shift 2
            ;;
        --ac-file)
            [ "$#" -ge 2 ] || die "missing value for --ac-file"
            ac_file=$2
            shift 2
            ;;
        --scope-file)
            [ "$#" -ge 2 ] || die "missing value for --scope-file"
            scope_file=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "validate-ac requires --project-root"
[ -n "$ac_file" ] || die "validate-ac requires --ac-file"
[ -n "$scope_file" ] || die "validate-ac requires --scope-file"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)

case "$ac_file" in /*) ac_path=$ac_file ;; *) ac_path=$root/$ac_file ;; esac
case "$scope_file" in /*) scope_path=$scope_file ;; *) scope_path=$root/$scope_file ;; esac
[ -f "$ac_path" ] || die "ac file not found: $ac_path"
[ -f "$scope_path" ] || die "scope file not found: $scope_path"

# Declared set from scope.md: files: + infra:. files_only is files: alone;
# infra_only is infra: alone. Reuses check-scope.sh's section parsing.
declared=()
files_only=()
infra_only=()
while IFS= read -r path; do
    [ -n "$path" ] || continue
    declared+=("$path")
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

# Split declared into files_only / infra_only by re-reading with section context.
# Any "key:" line other than files:/infra: (e.g. 约束:) resets the section so its
# list items are not misattributed.
current_section=
while IFS= read -r line; do
    case "$line" in
        "files:") current_section=files ;;
        "infra:") current_section=infra ;;
        -*)
            [ -n "$current_section" ] || continue
            item=${line#- }
            case "$current_section" in
                files) files_only+=("$item") ;;
                infra) infra_only+=("$item") ;;
            esac
            ;;
        *:) current_section= ;;
    esac
done < <(sed 's/^[[:space:]]*-[[:space:]]*/- /' "$scope_path")

[ "${#declared[@]}" -gt 0 ] ||
    die "scope file has no files: section: $scope_path"

# Parse ac-list.md into structured records: ACITEM, ACFIELD, VERIFY, OWNER,
# BANNED. Paths are assumed space-free (project-relative simple paths).
acs=()
seen_fields=()
ac_owners=()
problems=()

while IFS= read -r line; do
    case "$line" in
        ACITEM\ *)
            ac=${line#ACITEM }
            acs+=("$ac")
            ;;
        ACFIELD\ *)
            rest=${line#ACFIELD }
            seen_fields+=("$rest")
            ;;
        VERIFY\ *)
            rest=${line#VERIFY }
            ac=${rest%% *}
            val=${rest#* }
            case "$val" in
                unit|integration|scripted) ;;
                *) problems+=("$ac invalid verify: $val") ;;
            esac
            ;;
        OWNER\ *)
            rest=${line#OWNER }
            ac=${rest%% *}
            path=${rest#* }
            ac_owners+=("$path")
            owner_found=0
            for d in "${declared[@]}"; do
                [ "$d" = "$path" ] && owner_found=1 && break
            done
            [ "$owner_found" -eq 1 ] || problems+=("$ac owner not in scope: $path")
            ;;
        BANNED\ *)
            rest=${line#BANNED }
            ac=${rest%% *}
            word=${rest#* }
            problems+=("$ac banned word in assertion: $word")
            ;;
    esac
done < <(awk '
    BEGIN {
        in_ac = 0; ac = ""; ac_count = 0
        banned[1] = "合理"; banned[2] = "适当"; banned[3] = "优雅"
        banned[4] = "快速"; banned[5] = "尽可能"; banned[6] = "一些"
    }
    /^## AC 清单[[:space:]]*$/ { in_ac = 1; next }
    in_ac && /^## / { in_ac = 0 }
    in_ac {
        if (match($0, /^[[:space:]]*- AC-[0-9]+:/)) {
            s = $0; sub(/^[[:space:]]*- /, "", s); sub(/:.*/, "", s)
            ac = s; ac_count++
            print "ACITEM " ac
            next
        }
        if (ac == "") next
        if (match($0, /^[[:space:]]*- 断言:/)) {
            v = $0; sub(/^[[:space:]]*- 断言:[[:space:]]*/, "", v)
            print "ACFIELD " ac " 断言"
            for (i in banned) if (index(v, banned[i])) print "BANNED " ac " " banned[i]
            next
        }
        if (match($0, /^[[:space:]]*- 归属:/)) {
            v = $0; sub(/^[[:space:]]*- 归属:[[:space:]]*/, "", v)
            print "ACFIELD " ac " 归属"
            n = split(v, parts, ",")
            for (i = 1; i <= n; i++) {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", parts[i])
                if (parts[i] != "") print "OWNER " ac " " parts[i]
            }
            next
        }
        if (match($0, /^[[:space:]]*- 验证:/)) {
            v = $0; sub(/^[[:space:]]*- 验证:[[:space:]]*/, "", v)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
            print "ACFIELD " ac " 验证"
            print "VERIFY " ac " " v
            next
        }
    }
    END { if (ac_count == 0) print "NOAC" }
' "$ac_path")

# NOAC sentinel: ac-list has no AC items (missing header or empty).
if [ "${#acs[@]}" -eq 0 ]; then
    problems+=("ac-list has no AC items")
fi

# Every AC must have all three fields.
for ac in "${acs[@]}"; do
    for field in 断言 归属 验证; do
        present=0
        for sf in "${seen_fields[@]}"; do
            [ "$sf" = "$ac $field" ] && present=1 && break
        done
        [ "$present" -eq 1 ] || problems+=("$ac missing field: $field")
    done
done

# Every scope files: path must be covered by an AC owner or be in infra:.
for f in "${files_only[@]}"; do
    in_infra=0
    for d in "${infra_only[@]}"; do
        [ "$d" = "$f" ] && in_infra=1 && break
    done
    [ "$in_infra" -eq 1 ] && continue
    covered=0
    for o in "${ac_owners[@]}"; do
        [ "$o" = "$f" ] && covered=1 && break
    done
    [ "$covered" -eq 1 ] || problems+=("scope file not covered by any AC: $f")
done

if [ "${#problems[@]}" -gt 0 ]; then
    for p in "${problems[@]}"; do
        printf 'ac-check: FAIL %s\n' "$p"
    done
    printf 'ac-check: FAIL (%s problems)\n' "${#problems[@]}"
    exit 1
fi

printf 'ac-check: PASS (%s ACs, %s declared)\n' \
    "${#acs[@]}" "${#declared[@]}"
exit 0
