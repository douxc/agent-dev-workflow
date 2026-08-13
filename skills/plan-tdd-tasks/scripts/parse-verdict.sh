#!/usr/bin/env bash

# Mechanical verdict parser (run after each blind review). Extracts the verdict
# from a review file so the main agent does not eyeball pass/fail or the
# disagreement matrix. A malformed or missing file yields MALFORMED (exit 2),
# which the main agent treats as "re-dispatch that one reviewer".
#
#   --verdict-file <path>   path to A.md / B.md (absolute or relative to cwd)
#
# Exit 0 = verdict-parse: PASS    (file ends with "verdict: PASS")
# Exit 1 = verdict-parse: FAIL    (file ends with "verdict: FAIL"; FAIL blocks
#                                  are echoed first)
# Exit 2 = verdict-parse: MALFORMED (no valid verdict line, empty, or missing)

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

verdict_file=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --verdict-file)
            [ "$#" -ge 2 ] || die "missing value for --verdict-file"
            verdict_file=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$verdict_file" ] || die "parse-verdict requires --verdict-file"

case "$verdict_file" in
    /*) vpath=$verdict_file ;;
    *) vpath=$(pwd)/$verdict_file ;;
esac

if [ ! -f "$vpath" ]; then
    printf 'verdict-parse: MALFORMED\n'
    exit 2
fi

# Last non-empty line, with trailing whitespace trimmed for an exact match.
verdict_line=$(awk 'NF { sub(/[[:space:]]+$/, ""); last = $0 } END { print last }' \
    "$vpath")

case "$verdict_line" in
    "verdict: PASS")
        printf 'verdict-parse: PASS\n'
        exit 0
        ;;
    "verdict: FAIL")
        # Echo each FAIL block (its header line plus the 证据/理由 lines that
        # immediately follow) so the main agent has the failure evidence.
        awk '
            /^\[.*\] FAIL[[:space:]]*$/ { in_fail = 1; print; next }
            in_fail && /^[[:space:]]*(证据|理由):/ { print; next }
            in_fail { in_fail = 0 }
        ' "$vpath"
        printf 'verdict-parse: FAIL\n'
        exit 1
        ;;
    *)
        printf 'verdict-parse: MALFORMED\n'
        exit 2
        ;;
esac
