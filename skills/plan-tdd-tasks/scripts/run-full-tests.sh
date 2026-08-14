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
log_max_bytes=10485760

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
        --log-max-bytes)
            [ "$#" -ge 2 ] || die "missing value for --log-max-bytes"
            log_max_bytes=$2
            shift 2
            ;;
        *) die "unknown argument: $1" ;;
    esac
done

[ -n "$project_root" ] || die "run-full-tests requires --project-root"
[ -n "$test_cmd" ] || die "run-full-tests requires a non-empty --test-cmd"
[ -d "$project_root" ] || die "project root is not a directory: $project_root"
case "$log_max_bytes" in
    '' | *[!0-9]*) die "invalid --log-max-bytes: $log_max_bytes" ;;
esac
root=$(CDPATH= cd -P "$project_root" && pwd -P)

if [ -n "$workdir" ]; then
    [ -d "$workdir" ] || die "workdir is not a directory: $workdir"
    run_dir=$(CDPATH= cd -P "$workdir" && pwd -P)
else
    run_dir=$root
fi

if [ -n "$log_file" ]; then
    case "$log_file" in
        /*) log_path=$log_file ;;
        *) log_path=$root/$log_file ;;
    esac
    log_dir=$(dirname "$log_path")
    [ -d "$log_dir" ] || die "log file directory does not exist: $log_dir"
    log_dir=$(CDPATH= cd -P "$log_dir" && pwd -P)
    log_file=$log_dir/$(basename "$log_path")
fi

cd "$run_dir"

# Run exactly one test command via sh -c. The command was authored by the main
# agent in the package (test-command.txt), so injection is not a threat model.
#
# Log-file mode: output is captured to the log capped at --log-max-bytes (0 =
# unlimited). tail -c keeps only the most recent bytes (a BSD/GNU extension,
# available on both target platforms, macOS and Linux), so the log can never
# grow without bound and the console replay stays bounded too. The PASS/FAIL
# status line is then appended as the log's LAST line (the §9 commit gate
# reads it there) and the whole log is replayed to stdout, so log and console
# stay byte-identical.
#
# NEVER redirect or append this script's stdout into the same file passed as
# --log-file: the replay would append the log to itself (cat f >> f) and grow
# forever until the disk fills.
if [ -n "$log_file" ]; then
    # POSIX sh has no PIPESTATUS, so the test command's exit code is relayed
    # through a small status file written by the inner shell. The path is
    # quoted into the inner command; test_cmd and the log path are both
    # authored by the main agent, same trust model as the command itself.
    status_file=$log_dir/.full-tests-rc-$$
    trap 'rm -f "$status_file"' 0 1 2 3 15
    if [ "$log_max_bytes" -gt 0 ]; then
        sh -c "$test_cmd; rc=\$?; printf '%s\\n' \"\$rc\" > \"$status_file\"" \
            2>&1 | tail -c "$log_max_bytes" >"$log_file"
    else
        sh -c "$test_cmd; rc=\$?; printf '%s\\n' \"\$rc\" > \"$status_file\"" \
            2>&1 >"$log_file"
    fi
    rc=$(cat "$status_file" 2>/dev/null || printf '1')
    case "$rc" in
        '' | *[!0-9]*) rc=1 ;;
    esac
    if [ "$rc" -eq 0 ]; then
        marker='run-full-tests: PASS'
    else
        marker='run-full-tests: FAIL (exit '"$rc"')'
    fi
    # A separator newline keeps the marker on its own line even when the test
    # output does not end with one; the §9 gate reads the last non-empty line.
    printf '\n%s\n' "$marker" >>"$log_file"
    # Replay is buffered (read fully, then print once) rather than a
    # streaming cat: if stdout were redirected into the same log file, a
    # streaming read would keep re-reading its own appended output and grow
    # forever (cat f >> f). Buffering makes that impossible. Caveat: command
    # substitution cannot hold NUL bytes, so output containing NULs would
    # differ between log and console; test runners do not emit NULs. The log
    # always ends with a single newline, and command substitution strips
    # trailing newlines, so printf '%s\n' restores it byte-for-byte.
    log_text=$(cat "$log_file")
    printf '%s\n' "$log_text"
    [ "$rc" -eq 0 ] && exit 0
    exit 1
fi

if sh -c "$test_cmd"; then
    rc=0
else
    rc=$?
fi
if [ "$rc" -eq 0 ]; then
    printf 'run-full-tests: PASS\n'
    exit 0
fi
printf 'run-full-tests: FAIL (exit %s)\n' "$rc"
exit 1
