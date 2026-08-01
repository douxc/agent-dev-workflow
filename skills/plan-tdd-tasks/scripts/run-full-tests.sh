#!/bin/sh

set -u

die() {
    printf 'error: %s\n' "$*" >&2
    printf 'run-full-tests: USAGE ERROR\n'
    exit 2
}

project_root=
test_cmd=
workdir=
log_file=

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root)
            [ "$#" -ge 2 ] || die "missing value for --project-root"
            project_root=$2
            shift 2
            ;;
        --test-cmd)
            [ "$#" -ge 2 ] || die "missing value for --test-cmd"
            test_cmd=$2
            shift 2
            ;;
        --workdir)
            [ "$#" -ge 2 ] || die "missing value for --workdir"
            workdir=$2
            shift 2
            ;;
        --log-file)
            [ "$#" -ge 2 ] || die "missing value for --log-file"
            log_file=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "run-full-tests requires --project-root"
[ -n "$test_cmd" ] || die "run-full-tests requires a non-empty --test-cmd"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
root=$(CDPATH= cd -P "$project_root" && pwd -P)

if [ -n "$workdir" ]; then
    [ -d "$workdir" ] || die "workdir is not a directory: $workdir"
    run_dir=$(CDPATH= cd -P "$workdir" && pwd -P)
else
    run_dir=$root
fi

if [ -n "$log_file" ]; then
    log_dir=$(dirname "$log_file")
    [ -d "$log_dir" ] || die "log file directory does not exist: $log_dir"
fi

cd "$run_dir"

# Run exactly one test command via sh -c. The command was authored by the main
# agent in the package (test-command.txt), so injection is not a threat model.
# Output is captured to the log file (when requested) and then replayed to
# stdout so log and console stay byte-identical; exit status is taken from the
# test command itself.
if [ -n "$log_file" ]; then
    if sh -c "$test_cmd" >"$log_file" 2>&1; then
        rc=0
    else
        rc=$?
    fi
    cat "$log_file"
else
    if sh -c "$test_cmd"; then
        rc=0
    else
        rc=$?
    fi
fi

if [ "$rc" -eq 0 ]; then
    printf 'run-full-tests: PASS\n'
    exit 0
fi
printf 'run-full-tests: FAIL (exit %s)\n' "$rc"
exit 1
