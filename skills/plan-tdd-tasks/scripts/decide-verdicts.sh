#!/usr/bin/env bash

# Mechanical disagreement classification (skill §8 — run after both blind
# verdicts are in). Parses A.md and B.md via parse-verdict.sh and classifies
# the 2x2 matrix, so the main agent does not eyeball pass/fail or the
# disagreement table. A MALFORMED verdict names the offending file: the main
# agent re-dispatches only that reviewer (§7 step 3). FAIL-block evidence
# echo remains parse-verdict.sh's job; this script only classifies.
#
#   --verdict-a <path>   path to A.md
#   --verdict-b <path>   path to B.md
#
# Exit 0 = decide-verdicts: DOUBLE-PASS      (both pass -> §9)
# Exit 1 = decide-verdicts: DOUBLE-FAIL      (both fail -> fix, re-dispatch)
# Exit 1 = decide-verdicts: SPLIT            (one pass, one fail -> rebuttal)
# Exit 2 = decide-verdicts: MALFORMED (<f>)  (parse failure -> re-dispatch
#                                              that one)

set -eo pipefail

die() {
    printf 'error: %s\n' "$*" >&2
    exit 2
}

verdict_a=
verdict_b=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --verdict-a)
            [ "$#" -ge 2 ] || die "missing value for --verdict-a"
            verdict_a=$2
            shift 2
            ;;
        --verdict-b)
            [ "$#" -ge 2 ] || die "missing value for --verdict-b"
            verdict_b=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$verdict_a" ] || die "decide-verdicts requires --verdict-a"
[ -n "$verdict_b" ] || die "decide-verdicts requires --verdict-b"

case "$verdict_a" in
    /*) a_path=$verdict_a ;;
    *) a_path=$(pwd)/$verdict_a ;;
esac
case "$verdict_b" in
    /*) b_path=$verdict_b ;;
    *) b_path=$(pwd)/$verdict_b ;;
esac

self_dir=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
parse="$self_dir/parse-verdict.sh"

set +e
"$parse" --verdict-file "$a_path" >/dev/null 2>&1
a_status=$?
"$parse" --verdict-file "$b_path" >/dev/null 2>&1
b_status=$?
set -e

if [ "$a_status" -eq 2 ]; then
    printf 'decide-verdicts: MALFORMED (%s)\n' "$verdict_a"
    exit 2
fi
if [ "$b_status" -eq 2 ]; then
    printf 'decide-verdicts: MALFORMED (%s)\n' "$verdict_b"
    exit 2
fi

if [ "$a_status" -eq 0 ] && [ "$b_status" -eq 0 ]; then
    printf 'decide-verdicts: DOUBLE-PASS\n'
    exit 0
fi
if [ "$a_status" -eq 1 ] && [ "$b_status" -eq 1 ]; then
    printf 'decide-verdicts: DOUBLE-FAIL\n'
    exit 1
fi
printf 'decide-verdicts: SPLIT\n'
exit 1
