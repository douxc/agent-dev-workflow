#!/bin/sh

set -eu

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

emit() {
    printf '%s\t%s\n' "$1" "$2"
}

need_value() {
    [ "$#" -ge 2 ] || die "missing value for $1"
    [ -n "$2" ] || die "empty value for $1"
}

canonical_dir() {
    [ -d "$1" ] || die "directory does not exist: $1"
    case "$1" in
        /*) directory_to_resolve=$1 ;;
        *) directory_to_resolve=./$1 ;;
    esac
    (CDPATH= cd -P "$directory_to_resolve" && pwd -P)
}

validate_id() {
    value=$1
    label=$2
    case "$value" in
        "" | .* | *[!A-Za-z0-9._-]* | *..*)
            die "unsafe $label: $value"
            ;;
    esac
}

validate_branch() {
    branch_value=$1
    case "$branch_value" in
        "" | -* | *[!A-Za-z0-9._/-]* | *..*)
            die "unsafe branch: $branch_value"
            ;;
    esac
    git check-ref-format --branch "$branch_value" >/dev/null 2>&1 ||
        die "invalid branch: $branch_value"
}

validate_sha() {
    sha_value=$1
    sha_label=$2
    case "$sha_value" in
        *[!0-9a-f]* | "")
            die "invalid $sha_label: $sha_value"
            ;;
    esac
    [ "${#sha_value}" -eq 40 ] || die "invalid $sha_label: $sha_value"
}

validate_relative_path() {
    path_value=$1
    path_label=$2
    case "$path_value" in
        "" | "." | /* | -* | .. | ../* | */.. | */../* | *'*'* | *'?'* | *'['* | *[!A-Za-z0-9._/-]*)
            die "unsafe $path_label: $path_value"
            ;;
    esac
}

load_project_root() {
    requested_root=$(canonical_dir "$1")
    discovered_root=$(git -C "$requested_root" rev-parse --show-toplevel 2>/dev/null) ||
        die "not a Git worktree: $requested_root"
    discovered_root=$(canonical_dir "$discovered_root")
    [ "$requested_root" = "$discovered_root" ] ||
        die "project root is not the worktree root: $requested_root"
    PROJECT_ROOT=$requested_root
}

resolve_remote() {
    requested_remote=$1
    if [ -n "$requested_remote" ]; then
        REMOTE=$requested_remote
    else
        current=$(git -C "$PROJECT_ROOT" branch --show-current)
        configured=
        if [ -n "$current" ]; then
            configured=$(git -C "$PROJECT_ROOT" config --get \
                "branch.$current.remote" || :)
        fi
        if [ -n "$configured" ] && [ "$configured" != "." ]; then
            REMOTE=$configured
        elif git -C "$PROJECT_ROOT" remote get-url origin >/dev/null 2>&1; then
            REMOTE=origin
        else
            remotes=$(git -C "$PROJECT_ROOT" remote)
            count=$(printf '%s\n' "$remotes" |
                awk 'NF { count += 1 } END { print count + 0 }')
            [ "$count" -eq 1 ] || die "cannot resolve a unique remote"
            REMOTE=$remotes
        fi
    fi
    [ -n "$REMOTE" ] || die "cannot resolve remote"
    case "$REMOTE" in
        *[!A-Za-z0-9._-]* | -*)
            die "unsafe remote: $REMOTE"
            ;;
    esac
    git -C "$PROJECT_ROOT" remote get-url "$REMOTE" >/dev/null 2>&1 ||
        die "unknown remote: $REMOTE"
}

resolve_default_branch() {
    symbolic=$(git -C "$PROJECT_ROOT" symbolic-ref --quiet --short \
        "refs/remotes/$REMOTE/HEAD" 2>/dev/null || :)
    if [ -n "$symbolic" ]; then
        DEFAULT_BRANCH=${symbolic#"$REMOTE/"}
        validate_branch "$DEFAULT_BRANCH"
        return
    fi
    if git -C "$PROJECT_ROOT" show-ref --verify --quiet \
        "refs/remotes/$REMOTE/main" ||
        git -C "$PROJECT_ROOT" show-ref --verify --quiet refs/heads/main; then
        DEFAULT_BRANCH=main
        return
    fi
    if git -C "$PROJECT_ROOT" show-ref --verify --quiet \
        "refs/remotes/$REMOTE/master" ||
        git -C "$PROJECT_ROOT" show-ref --verify --quiet refs/heads/master; then
        DEFAULT_BRANCH=master
        return
    fi
    die "cannot resolve default branch from remote HEAD, main, or master"
}

detect_operation() {
    operation_root=$1
    OPERATION=none
    for operation_name in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD; do
        operation_path=$(git -C "$operation_root" rev-parse --git-path \
            "$operation_name")
        if [ -e "$operation_path" ]; then
            OPERATION=$operation_name
            return
        fi
    done
    for operation_name in rebase-merge rebase-apply; do
        operation_path=$(git -C "$operation_root" rev-parse --git-path \
            "$operation_name")
        if [ -d "$operation_path" ]; then
            OPERATION=$operation_name
            return
        fi
    done
}

require_no_operation() {
    detect_operation "$1"
    [ "$OPERATION" = none ] || die "Git operation in progress: $OPERATION"
}

require_clean() {
    [ -z "$(git -C "$1" status --porcelain)" ] ||
        die "worktree must be clean: $1"
}

common_git_dir() {
    common_path=$(git -C "$1" rev-parse --git-common-dir)
    case "$common_path" in
        /*) canonical_dir "$common_path" ;;
        *) canonical_dir "$1/$common_path" ;;
    esac
}

validate_worktree_context() {
    context_worktree=$(canonical_dir "$1")
    context_branch=$2
    context_base=$3
    validate_branch "$context_branch"
    validate_sha "$context_base" "base SHA"

    context_top=$(git -C "$context_worktree" rev-parse --show-toplevel 2>/dev/null) ||
        die "not a Git worktree: $context_worktree"
    context_top=$(canonical_dir "$context_top")
    [ "$context_worktree" = "$context_top" ] ||
        die "worktree path is not exact: $context_worktree"
    root_common=$(common_git_dir "$PROJECT_ROOT")
    worktree_common=$(common_git_dir "$context_worktree")
    [ "$root_common" = "$worktree_common" ] ||
        die "worktree does not belong to project root"
    actual_branch=$(git -C "$context_worktree" branch --show-current)
    [ -n "$actual_branch" ] || die "detached HEAD is not allowed"
    [ "$actual_branch" = "$context_branch" ] ||
        die "branch mismatch: expected $context_branch, got $actual_branch"
    git -C "$context_worktree" rev-parse --verify \
        "$context_base^{commit}" >/dev/null 2>&1 ||
        die "base SHA is not a commit in this repository"
    git -C "$context_worktree" merge-base --is-ancestor \
        "$context_base" HEAD >/dev/null 2>&1 ||
        die "HEAD is not a descendant of the expected base"
    require_no_operation "$context_worktree"
    VERIFIED_WORKTREE=$context_worktree
}

validate_owner() {
    owner_task=$1
    owner_task_dir=$2
    owner_marker=$owner_task_dir/task-owner.json
    [ -f "$owner_marker" ] || die "missing task-owner.json"
    python3 -c '
import json
import pathlib
import sys
marker_path, task_id, project_root, task_directory = sys.argv[1:]
try:
    data = json.loads(pathlib.Path(marker_path).read_text(encoding="utf-8"))
except (OSError, ValueError) as error:
    raise SystemExit("invalid task-owner.json: %s" % error)
expected = {
    "task_id": task_id,
    "project_root": project_root,
    "task_directory": task_directory,
    "created_by": "plan-dev-tasks",
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit("task-owner mismatch: %s" % key)
' "$owner_marker" "$owner_task" "$PROJECT_ROOT" "$owner_task_dir" ||
        die "task-owner validation failed"
}

inspect_command() {
    project_root=
    remote=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --remote)
                need_value "$@"
                remote=$2
                shift 2
                ;;
            *) die "unknown inspect argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "inspect requires --project-root"
    load_project_root "$project_root"
    resolve_remote "$remote"
    resolve_default_branch
    current_branch=$(git -C "$PROJECT_ROOT" branch --show-current)
    [ -n "$current_branch" ] || current_branch=detached
    head=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
    if [ -z "$(git -C "$PROJECT_ROOT" status --porcelain)" ]; then
        clean=yes
    else
        clean=no
    fi
    detect_operation "$PROJECT_ROOT"

    emit project_root "$PROJECT_ROOT"
    emit remote "$REMOTE"
    emit default_branch "$DEFAULT_BRANCH"
    emit current_branch "$current_branch"
    emit head "$head"
    emit clean "$clean"
    emit operation "$OPERATION"
    git -C "$PROJECT_ROOT" worktree list --porcelain |
        while IFS= read -r worktree_line; do
            case "$worktree_line" in
                "worktree "*) emit worktree "${worktree_line#worktree }" ;;
                "HEAD "*) emit worktree_head "${worktree_line#HEAD }" ;;
                "branch "*) emit worktree_branch "${worktree_line#branch }" ;;
                detached) emit worktree_branch detached ;;
            esac
        done
}

sync_command() {
    project_root=
    remote=
    fetch_source=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --remote)
                need_value "$@"
                remote=$2
                shift 2
                ;;
            --fetch-source)
                need_value "$@"
                fetch_source=$2
                shift 2
                ;;
            *) die "unknown sync argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "sync requires --project-root"
    load_project_root "$project_root"
    require_no_operation "$PROJECT_ROOT"
    require_clean "$PROJECT_ROOT"
    current_branch=$(git -C "$PROJECT_ROOT" branch --show-current)
    [ -n "$current_branch" ] || die "detached HEAD is not allowed"
    resolve_remote "$remote"
    resolve_default_branch
    [ "$current_branch" = "$DEFAULT_BRANCH" ] ||
        die "sync must run on default branch $DEFAULT_BRANCH"
    git -C "$PROJECT_ROOT" show-ref --verify --quiet \
        "refs/heads/$DEFAULT_BRANCH" ||
        die "local default branch does not exist"
    [ -n "$fetch_source" ] || fetch_source=$REMOTE
    case "$fetch_source" in
        -*) die "unsafe fetch source: $fetch_source" ;;
    esac

    git -C "$PROJECT_ROOT" fetch "$fetch_source" \
        "+refs/heads/$DEFAULT_BRANCH:refs/remotes/$REMOTE/$DEFAULT_BRANCH"
    local_sha=$(git -C "$PROJECT_ROOT" rev-parse "refs/heads/$DEFAULT_BRANCH")
    remote_sha=$(git -C "$PROJECT_ROOT" rev-parse \
        "refs/remotes/$REMOTE/$DEFAULT_BRANCH")
    if [ "$local_sha" = "$remote_sha" ]; then
        :
    elif git -C "$PROJECT_ROOT" merge-base --is-ancestor \
        "$local_sha" "$remote_sha"; then
        git -C "$PROJECT_ROOT" merge --ff-only --no-edit \
            "refs/remotes/$REMOTE/$DEFAULT_BRANCH"
    elif git -C "$PROJECT_ROOT" merge-base --is-ancestor \
        "$remote_sha" "$local_sha"; then
        die "local default branch is ahead of remote"
    else
        die "local default branch has diverged from remote"
    fi
    base_sha=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
    emit project_root "$PROJECT_ROOT"
    emit remote "$REMOTE"
    emit default_branch "$DEFAULT_BRANCH"
    emit base_sha "$base_sha"
}

prepare_serial_command() {
    project_root=
    base=
    branch=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --base)
                need_value "$@"
                base=$2
                shift 2
                ;;
            --branch)
                need_value "$@"
                branch=$2
                shift 2
                ;;
            *) die "unknown prepare-serial argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "prepare-serial requires --project-root"
    [ -n "$base" ] || die "prepare-serial requires --base"
    [ -n "$branch" ] || die "prepare-serial requires --branch"
    load_project_root "$project_root"
    validate_sha "$base" "base SHA"
    validate_branch "$branch"
    require_no_operation "$PROJECT_ROOT"
    require_clean "$PROJECT_ROOT"
    head=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
    [ "$head" = "$base" ] || die "HEAD does not match expected base"
    git -C "$PROJECT_ROOT" show-ref --verify --quiet "refs/heads/$branch" &&
        die "branch already exists: $branch"
    git -C "$PROJECT_ROOT" switch -c "$branch" "$base"
    emit project_root "$PROJECT_ROOT"
    emit worktree "$PROJECT_ROOT"
    emit branch "$branch"
    emit base_sha "$base"
}

prepare_parallel_command() {
    project_root=
    task_id=
    packet_id=
    base=
    branch=
    shares=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --task-id)
                need_value "$@"
                task_id=$2
                shift 2
                ;;
            --packet-id)
                need_value "$@"
                packet_id=$2
                shift 2
                ;;
            --base)
                need_value "$@"
                base=$2
                shift 2
                ;;
            --branch)
                need_value "$@"
                branch=$2
                shift 2
                ;;
            --share)
                need_value "$@"
                shares="${shares}${shares:+
}$2"
                shift 2
                ;;
            *) die "unknown prepare-parallel argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "prepare-parallel requires --project-root"
    [ -n "$task_id" ] || die "prepare-parallel requires --task-id"
    [ -n "$packet_id" ] || die "prepare-parallel requires --packet-id"
    [ -n "$base" ] || die "prepare-parallel requires --base"
    [ -n "$branch" ] || die "prepare-parallel requires --branch"
    load_project_root "$project_root"
    validate_id "$task_id" "task ID"
    validate_id "$packet_id" "packet ID"
    validate_sha "$base" "base SHA"
    validate_branch "$branch"
    git -C "$PROJECT_ROOT" rev-parse --verify "$base^{commit}" >/dev/null 2>&1 ||
        die "base SHA is not a commit"
    require_no_operation "$PROJECT_ROOT"
    task_dir_path=$PROJECT_ROOT/.tmp/$task_id
    task_dir=$(canonical_dir "$task_dir_path")
    case "$task_dir" in
        "$PROJECT_ROOT"/.tmp/"$task_id") ;;
        *) die "task directory escapes project .tmp root" ;;
    esac
    validate_owner "$task_id" "$task_dir"
    worktrees_dir=$task_dir/worktrees
    worktree=$worktrees_dir/$packet_id
    [ ! -e "$worktree" ] && [ ! -L "$worktree" ] ||
        die "worktree path already exists: $worktree"
    git -C "$PROJECT_ROOT" show-ref --verify --quiet "refs/heads/$branch" &&
        die "branch already exists: $branch"

    if [ -n "$shares" ]; then
        while IFS= read -r share; do
            validate_relative_path "$share" "shared dependency path"
            source_path=$PROJECT_ROOT/$share
            [ -d "$source_path" ] && [ ! -L "$source_path" ] ||
                die "shared dependency must be an existing directory: $share"
            source_real=$(canonical_dir "$source_path")
            case "$source_real" in
                "$PROJECT_ROOT"/*) ;;
                *) die "shared dependency escapes project root: $share" ;;
            esac
            git -C "$PROJECT_ROOT" check-ignore --quiet -- "$share" ||
                die "shared dependency is not Git-ignored: $share"
            if git -C "$PROJECT_ROOT" cat-file -e "$base:$share" 2>/dev/null; then
                die "shared dependency is tracked at base: $share"
            fi
        done <<EOF
$shares
EOF
    fi
    shares_dir=$task_dir/worktree-shares
    shares_marker=$shares_dir/$packet_id
    [ ! -e "$shares_marker" ] && [ ! -L "$shares_marker" ] ||
        die "shared dependency marker already exists"

    mkdir -p "$worktrees_dir"
    git -C "$PROJECT_ROOT" worktree add -b "$branch" "$worktree" "$base"
    if [ -n "$shares" ]; then
        while IFS= read -r share; do
            source_real=$(canonical_dir "$PROJECT_ROOT/$share")
            link_path=$worktree/$share
            [ ! -e "$link_path" ] && [ ! -L "$link_path" ] ||
                die "shared dependency link target exists: $share"
            link_parent=$(dirname "$link_path")
            mkdir -p "$link_parent"
            ln -s "$source_real" "$link_path"
        done <<EOF
$shares
EOF
    fi
    mkdir -p "$shares_dir"
    printf '%s\n' "$shares" >"$shares_marker"
    emit project_root "$PROJECT_ROOT"
    emit worktree "$worktree"
    emit branch "$branch"
    emit base_sha "$base"
}

verify_command() {
    project_root=
    worktree=
    branch=
    base=
    require_clean_flag=no
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --worktree)
                need_value "$@"
                worktree=$2
                shift 2
                ;;
            --branch)
                need_value "$@"
                branch=$2
                shift 2
                ;;
            --base)
                need_value "$@"
                base=$2
                shift 2
                ;;
            --require-clean)
                require_clean_flag=yes
                shift
                ;;
            *) die "unknown verify argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "verify requires --project-root"
    [ -n "$worktree" ] || die "verify requires --worktree"
    [ -n "$branch" ] || die "verify requires --branch"
    [ -n "$base" ] || die "verify requires --base"
    load_project_root "$project_root"
    validate_worktree_context "$worktree" "$branch" "$base"
    if [ "$require_clean_flag" = yes ]; then
        require_clean "$VERIFIED_WORKTREE"
    fi
    emit project_root "$PROJECT_ROOT"
    emit worktree "$VERIFIED_WORKTREE"
    emit branch "$branch"
    emit head "$(git -C "$VERIFIED_WORKTREE" rev-parse HEAD)"
    emit base_sha "$base"
}

commit_command() {
    project_root=
    worktree=
    branch=
    base=
    message=
    paths=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --worktree)
                need_value "$@"
                worktree=$2
                shift 2
                ;;
            --branch)
                need_value "$@"
                branch=$2
                shift 2
                ;;
            --base)
                need_value "$@"
                base=$2
                shift 2
                ;;
            --message)
                need_value "$@"
                message=$2
                shift 2
                ;;
            --path)
                need_value "$@"
                paths="${paths}${paths:+
}$2"
                shift 2
                ;;
            *) die "unknown commit argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "commit requires --project-root"
    [ -n "$worktree" ] || die "commit requires --worktree"
    [ -n "$branch" ] || die "commit requires --branch"
    [ -n "$base" ] || die "commit requires --base"
    [ -n "$message" ] || die "commit requires --message"
    [ -n "$paths" ] || die "commit requires at least one --path"
    load_project_root "$project_root"
    validate_worktree_context "$worktree" "$branch" "$base"
    git -C "$VERIFIED_WORKTREE" diff --cached --quiet ||
        die "index already contains staged changes"

    while IFS= read -r path; do
        validate_relative_path "$path" "authorized commit path"
    done <<EOF
$paths
EOF
    while IFS= read -r path; do
        git -C "$VERIFIED_WORKTREE" add -- "$path"
    done <<EOF
$paths
EOF
    git -C "$VERIFIED_WORKTREE" diff --cached --quiet &&
        die "refusing empty commit"
    git -C "$VERIFIED_WORKTREE" commit -m "$message"
    emit branch "$branch"
    emit commit_sha "$(git -C "$VERIFIED_WORKTREE" rev-parse HEAD)"
}

push_command() {
    project_root=
    worktree=
    remote=
    default_branch=
    expected_remote_tip=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --worktree)
                need_value "$@"
                worktree=$2
                shift 2
                ;;
            --remote)
                need_value "$@"
                remote=$2
                shift 2
                ;;
            --default-branch)
                need_value "$@"
                default_branch=$2
                shift 2
                ;;
            --expected-remote-tip)
                need_value "$@"
                expected_remote_tip=$2
                shift 2
                ;;
            *) die "unknown push argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "push requires --project-root"
    [ -n "$worktree" ] || die "push requires --worktree"
    [ -n "$remote" ] || die "push requires --remote"
    [ -n "$default_branch" ] || die "push requires --default-branch"
    [ -n "$expected_remote_tip" ] ||
        die "push requires --expected-remote-tip"
    load_project_root "$project_root"
    resolve_remote "$remote"
    validate_branch "$default_branch"
    branch=$(git -C "$worktree" branch --show-current 2>/dev/null || :)
    [ -n "$branch" ] || die "detached HEAD is not allowed"
    validate_branch "$branch"
    [ "$branch" != "$default_branch" ] ||
        die "refusing to push default branch"
    head=$(git -C "$worktree" rev-parse HEAD)
    validate_worktree_context "$worktree" "$branch" "$head"
    require_clean "$VERIFIED_WORKTREE"
    case "$expected_remote_tip" in
        absent) ;;
        *) validate_sha "$expected_remote_tip" "expected remote tip" ;;
    esac

    remote_tip=$(git -C "$VERIFIED_WORKTREE" ls-remote --heads "$REMOTE" \
        "refs/heads/$branch" | awk 'NR == 1 { print $1 }')
    if [ -z "$remote_tip" ]; then
        [ "$expected_remote_tip" = absent ] ||
            die "remote branch is absent but a tip was expected"
    else
        validate_sha "$remote_tip" "remote tip"
        [ "$expected_remote_tip" != absent ] ||
            die "remote branch exists unexpectedly"
        [ "$remote_tip" = "$expected_remote_tip" ] ||
            die "remote branch tip does not match expected tip"
        git -C "$VERIFIED_WORKTREE" fetch "$REMOTE" \
            "refs/heads/$branch:refs/remotes/$REMOTE/$branch"
        fetched_tip=$(git -C "$VERIFIED_WORKTREE" rev-parse \
            "refs/remotes/$REMOTE/$branch")
        [ "$fetched_tip" = "$expected_remote_tip" ] ||
            die "remote branch changed during verification"
        git -C "$VERIFIED_WORKTREE" merge-base --is-ancestor \
            "$fetched_tip" HEAD >/dev/null 2>&1 ||
            die "push would not be fast-forward"
    fi
    git -C "$VERIFIED_WORKTREE" push -u "$REMOTE" \
        "HEAD:refs/heads/$branch"
    emit remote "$REMOTE"
    emit branch "$branch"
    emit pushed_sha "$(git -C "$VERIFIED_WORKTREE" rev-parse HEAD)"
}

cleanup_parallel_command() {
    project_root=
    task_id=
    packet_id=
    branch=
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --project-root)
                need_value "$@"
                project_root=$2
                shift 2
                ;;
            --task-id)
                need_value "$@"
                task_id=$2
                shift 2
                ;;
            --packet-id)
                need_value "$@"
                packet_id=$2
                shift 2
                ;;
            --branch)
                need_value "$@"
                branch=$2
                shift 2
                ;;
            *) die "unknown cleanup-parallel argument: $1" ;;
        esac
    done
    [ -n "$project_root" ] || die "cleanup-parallel requires --project-root"
    [ -n "$task_id" ] || die "cleanup-parallel requires --task-id"
    [ -n "$packet_id" ] || die "cleanup-parallel requires --packet-id"
    [ -n "$branch" ] || die "cleanup-parallel requires --branch"
    load_project_root "$project_root"
    validate_id "$task_id" "task ID"
    validate_id "$packet_id" "packet ID"
    validate_branch "$branch"
    task_dir_path=$PROJECT_ROOT/.tmp/$task_id
    task_dir=$(canonical_dir "$task_dir_path")
    case "$task_dir" in
        "$PROJECT_ROOT"/.tmp/"$task_id") ;;
        *) die "task directory escapes project .tmp root" ;;
    esac
    validate_owner "$task_id" "$task_dir"
    expected_worktree=$task_dir/worktrees/$packet_id
    worktree=$(canonical_dir "$expected_worktree")
    case "$worktree" in
        "$task_dir"/worktrees/"$packet_id") ;;
        *) die "worktree escapes owned task directory" ;;
    esac
    actual_top=$(git -C "$worktree" rev-parse --show-toplevel 2>/dev/null) ||
        die "owned path is not a Git worktree"
    actual_top=$(canonical_dir "$actual_top")
    [ "$actual_top" = "$worktree" ] || die "worktree path is not exact"
    actual_branch=$(git -C "$worktree" branch --show-current)
    [ "$actual_branch" = "$branch" ] ||
        die "branch mismatch for cleanup"
    require_no_operation "$worktree"
    shares_marker=$task_dir/worktree-shares/$packet_id
    shares=
    if [ -f "$shares_marker" ] && [ ! -L "$shares_marker" ]; then
        shares=$(sed '/^$/d' "$shares_marker")
    elif [ -e "$shares_marker" ] || [ -L "$shares_marker" ]; then
        die "invalid shared dependency marker"
    fi

    status_lines=$(git -C "$worktree" status --porcelain --untracked-files=all)
    if [ -n "$status_lines" ]; then
        while IFS= read -r status_line; do
            case "$status_line" in
                "?? "*) status_path=${status_line#?? } ;;
                *) die "worktree has tracked or staged changes" ;;
            esac
            declared=no
            if [ -n "$shares" ]; then
                while IFS= read -r share; do
                    validate_relative_path "$share" "shared dependency path"
                    if [ "$status_path" = "$share" ]; then
                        declared=yes
                    fi
                done <<EOF
$shares
EOF
            fi
            [ "$declared" = yes ] ||
                die "worktree has unmanaged untracked content: $status_path"
        done <<EOF
$status_lines
EOF
    fi
    if [ -n "$shares" ]; then
        while IFS= read -r share; do
            link_path=$worktree/$share
            [ -L "$link_path" ] ||
                die "managed shared dependency is not a symlink: $share"
            link_target=$(readlink "$link_path")
            source_real=$(canonical_dir "$PROJECT_ROOT/$share")
            [ "$link_target" = "$source_real" ] ||
                die "managed shared dependency target mismatch: $share"
            unlink "$link_path"
        done <<EOF
$shares
EOF
    fi
    require_clean "$worktree"
    git -C "$PROJECT_ROOT" worktree remove "$worktree"
    if [ -f "$shares_marker" ]; then
        unlink "$shares_marker"
    fi
    emit removed_worktree "$worktree"
    emit retained_branch "$branch"
}

usage() {
    printf '%s\n' \
        "usage: git-workflow.sh <inspect|sync|prepare-serial|prepare-parallel|verify|commit|push|cleanup-parallel> [options]" >&2
    exit 2
}

[ "$#" -gt 0 ] || usage
command_name=$1
shift
case "$command_name" in
    inspect) inspect_command "$@" ;;
    sync) sync_command "$@" ;;
    prepare-serial) prepare_serial_command "$@" ;;
    prepare-parallel) prepare_parallel_command "$@" ;;
    verify) verify_command "$@" ;;
    commit) commit_command "$@" ;;
    push) push_command "$@" ;;
    cleanup-parallel) cleanup_parallel_command "$@" ;;
    *) usage ;;
esac
