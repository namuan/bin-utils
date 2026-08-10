#!/bin/bash
# Move files to macOS Trash (safe rm wrapper).
#
# Goal: behave like POSIX rm for every case a script or build system can observe
# (exit codes, -f semantics, refusing to remove a directory without -r), while
# routing real user data to ~/.Trash instead of destroying it.
#
# NOTE: bash 3.2 compatible on purpose (/bin/bash on macOS is 3.2) — no mapfile,
# no ${var,,}, no `set -u` (3.2 errors on "${arr[@]}" when the array is empty).

status=0
force=false
recursive=false
verbose=false
interactive=false
dir_ok=false
end_of_flags=false
flags=()
paths=()

for arg in "$@"; do
    if [ "$end_of_flags" = false ] && [ "$arg" = "--" ]; then
        # REASON: POSIX `--` ends option parsing. Without this, `rm -rf -- -weirdname`
        # treated the filename as a flag and silently never deleted it.
        end_of_flags=true
        continue
    fi
    if [ "$end_of_flags" = false ] && [[ "$arg" == -?* ]]; then
        [[ "$arg" == *f* ]] && force=true
        [[ "$arg" == *r* || "$arg" == *R* ]] && recursive=true
        [[ "$arg" == *v* ]] && verbose=true
        [[ "$arg" == *i* ]] && interactive=true
        [[ "$arg" == *d* ]] && dir_ok=true
        flags+=("$arg")
        continue
    fi
    paths+=("$arg")
done

if [ ${#paths[@]} -eq 0 ]; then
    # REASON: `rm -f` with no operands must exit 0 (POSIX). Build scripts do
    # `rm -f $(FILES)` where FILES can expand to nothing.
    [ "$force" = true ] && exit 0
    echo "usage: rm [-f | -i] [-dIPRrvW] file ..." >&2
    exit 1
fi

# Find the mount point containing $1 by walking up until the device number changes.
# REASON: parsing `df` output breaks on volume names with spaces (e.g. /Volumes/Power Protect).
mount_point_of() {
    local p="$1" dev parent
    dev="$(stat -f %d -- "$p" 2>/dev/null)" || return 1
    while [ "$p" != "/" ]; do
        parent="$(dirname -- "$p")"
        [ "$(stat -f %d -- "$parent" 2>/dev/null)" != "$dev" ] && break
        p="$parent"
    done
    printf '%s' "$p"
}

# Move $1 to the Trash using the same API Finder uses (NSFileManager -trashItemAtURL:).
# REASON: a raw rename(2) into ~/.Trash fails with EDEADLK ("Resource deadlock avoided")
# for items under a FileProvider/iCloud domain such as ~/Documents (and its .nosync
# subtrees), and also under concurrent modification of the same tree. trashItemAtURL is
# domain-aware and routes to the correct trash instead of doing a cross-domain rename.
# REASON: osascript is wrapped in `timeout 60 taskpolicy -b` per this machine's convention —
# it can hang indefinitely on iCloud paths and must not run at foreground priority.
trash_via_api() {
    # REASON: report success via stdout, not an exception. Dereferencing the NSError Ref
    # on the failure path segfaults JavaScriptCore, and passing null for the error
    # out-parameter avoids allocating it at all.
    local result
    result="$(timeout 60 taskpolicy -b osascript -l JavaScript -e '
function run(argv) {
    ObjC.import("Foundation");
    var url = $.NSURL.fileURLWithPath($.NSString.alloc.initWithUTF8String(argv[0]));
    return $.NSFileManager.defaultManager.trashItemAtURLResultingItemURLError(url, null, null) ? "OK" : "FAIL";
}' "$1" 2>/dev/null)"
    [ "$result" = "OK" ]
}

# Paths whose contents are regenerable build artifacts: use real rm.
# REASON: build systems generate tens of thousands of ephemeral files. Moving them to
# Trash is slow (a multi-GB `mv` that Finder then has to index), fills the same volume
# so it frees no disk, and is what made `rm -rf node_modules` appear to hang.
# The directory ITSELF must match too, not just its children — matching only `*/node_modules/*`
# meant the single most common command (`rm -rf node_modules`) fell through to the Trash path.
is_ephemeral() {
    local item_path="$1" base="$2"
    case "$base" in
        node_modules|.next|__pycache__|.venv|.gradle|.terraform|.turbo|.pytest_cache|.mypy_cache|.ruff_cache)
            return 0 ;;
        target)
            # REASON: only treat `target` as disposable when it is a Cargo build dir —
            # "target" is otherwise a plausible name for real user data.
            [ -f "$(dirname -- "$item_path")/Cargo.toml" ] && return 0 ;;
    esac
    case "$item_path" in
        */node_modules/*|*/target/*|*/.next/*|*/__pycache__/*|*/.venv/*|*/.gradle/*|*/.terraform/*) return 0 ;;
        /tmp/*|/private/tmp/*|/var/*|/private/var/*) return 0 ;;
    esac
    return 1
}

for item in "${paths[@]}"; do
    base="$(basename -- "$item")"

    # Real rm refuses these outright; so must we, before any path math.
    case "$base" in
        .|..)
            echo "rm: \"$base\" and \"..\" may not be removed" >&2
            status=1
            continue ;;
        /)
            # REASON: basename "/" is "/", which otherwise built the path "//" and slipped
            # past the root guard below — `rm -rf /` reached the mv (it failed, but only by luck).
            echo "rm: \"/\" may not be removed" >&2
            status=1
            continue ;;
    esac

    # Resolve to an absolute physical path so iCloud doesn't intercept .nosync symlinks.
    parent_real="$(cd "$(dirname -- "$item")" 2>/dev/null && pwd -P)"
    if [ -n "$parent_real" ]; then
        item_path="${parent_real%/}/$base"
    else
        # Parent doesn't exist or isn't traversable, so the item cannot exist either.
        item_path="$item"
    fi

    if [ "$item_path" = "/" ]; then
        echo "rm: \"/\" may not be removed" >&2
        status=1
        continue
    fi

    # REASON: `[ -e ]` is FALSE for a broken symlink, so the old wrapper silently skipped
    # dangling links — `rm -rf link` exited 0 with the link still there, and the next
    # `ln -s` in the script then failed. `-L` catches them.
    if [ ! -e "$item" ] && [ ! -L "$item" ]; then
        if [ "$force" = false ]; then
            echo "rm: $item: No such file or directory" >&2
            status=1
        fi
        # REASON: keep going instead of `exit 1` — POSIX rm processes every operand and
        # reports failure at the end. Exiting here skipped the remaining arguments.
        continue
    fi

    # Directory guard. A symlink to a directory is not a directory for rm's purposes.
    if [ -d "$item" ] && [ ! -L "$item" ]; then
        if [ "$recursive" = false ]; then
            if [ "$dir_ok" = true ] && rmdir -- "$item_path" 2>/dev/null; then
                [ "$verbose" = true ] && echo "$item"
                continue
            fi
            # REASON: the old wrapper happily trashed an entire tree on a bare `rm dir`.
            # Real rm errors out; matching it prevents accidental whole-directory removal.
            echo "rm: $item: is a directory" >&2
            status=1
            continue
        fi
    fi

    if [ "$interactive" = true ] && [ "$force" = false ]; then
        printf 'remove %s? ' "$item" >&2
        read -r reply < /dev/tty || reply=""
        case "$reply" in [yY]*) ;; *) continue ;; esac
    fi

    if is_ephemeral "$item_path" "$base"; then
        /bin/rm "${flags[@]}" -- "$item" || status=1
        continue
    fi

    # Pick the Trash on the item's own volume.
    # REASON: mv'ing off an external volume into ~/.Trash silently turns into a full
    # cross-device copy (slow, can fail mid-way, and frees nothing on the source volume).
    # Finder uses <volume>/.Trashes/<uid>; do the same.
    item_dev="$(stat -f %d -- "$item_path" 2>/dev/null)"
    home_dev="$(stat -f %d -- "$HOME" 2>/dev/null)"
    if [ -n "$item_dev" ] && [ "$item_dev" = "$home_dev" ]; then
        trash_dir="$HOME/.Trash"
    else
        vol="$(mount_point_of "$item_path")"
        if [ -n "$vol" ] && [ "$vol" != "/" ]; then
            trash_dir="$vol/.Trashes/$(id -u)"
        else
            trash_dir="$HOME/.Trash"
        fi
    fi

    if ! mkdir -p "$trash_dir" 2>/dev/null; then
        echo "rm: $item: cannot access trash at $trash_dir (use /bin/rm to delete permanently)" >&2
        status=1
        continue
    fi

    # Resolve name collisions inside the trash.
    dest="$trash_dir/$base"
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        suffix="$(date +%Y%m%d%H%M%S)"
        dest="$trash_dir/${base}_${suffix}"
        n=1
        while [ -e "$dest" ] || [ -L "$dest" ]; do
            dest="$trash_dir/${base}_${suffix}_${n}"
            n=$((n + 1))
        done
    fi

    # REASON: the old wrapper ignored mv's exit status, so a permission-denied move
    # reported success while the file was still on disk.
    # Escalation ladder. rename(2) is the fast path, but it fails on FileProvider/iCloud
    # domain boundaries and under concurrent access, so never treat its failure as fatal.
    moved=false
    if mv_err="$(mv -f -- "$item_path" "$dest" 2>&1)"; then
        moved=true
    else
        # REASON: another process (a parallel agent, a harness cleanup) may have removed the
        # tree while we were working. It's gone — that's the requested outcome, not an error.
        if [ ! -e "$item_path" ] && [ ! -L "$item_path" ]; then
            moved=true
        fi

        # REASON: if the parent directory isn't writable the removal can never succeed, so
        # skip the retries and the ditto copy — otherwise a permission error costs 1.2s of
        # sleeps plus a full copy of the tree that then has to be thrown away.
        parent_dir="$(dirname -- "$item_path")"
        recoverable=true
        [ -w "$parent_dir" ] || recoverable=false

        # REASON: EDEADLK/EBUSY from a concurrent writer on the same tree is transient;
        # two short retries clear it without the user re-running the command.
        if [ "$moved" = false ] && [ "$recoverable" = true ]; then
            for delay in 0.2 1; do
                sleep "$delay"
                if mv -f -- "$item_path" "$dest" 2>/dev/null; then moved=true; break; fi
                if [ ! -e "$item_path" ] && [ ! -L "$item_path" ]; then moved=true; break; fi
            done
        fi

        # Domain-aware Trash API — handles the iCloud/.nosync EDEADLK case rename can't.
        if [ "$moved" = false ] && trash_via_api "$item_path"; then
            moved=true
        fi

        # REASON: last resort before giving up — copy into the Trash then delete the source,
        # so the data stays recoverable even when nothing can rename it. `ditto` (not cp)
        # because it preserves ACLs, xattrs and resource forks.
        if [ "$moved" = false ] && [ "$recoverable" = true ] && ditto "$item_path" "$dest" 2>/dev/null; then
            if /bin/rm -rf -- "$item_path" 2>/dev/null; then
                moved=true
            else
                /bin/rm -rf -- "$dest" 2>/dev/null
            fi
        fi
    fi

    if [ "$moved" = true ]; then
        [ "$verbose" = true ] && echo "$item"
    else
        # Surface the original error, and don't pretend the removal happened.
        [ -n "$mv_err" ] && echo "$mv_err" >&2
        echo "rm: $item: could not move to trash (use /bin/rm to delete permanently)" >&2
        status=1
    fi
done

exit $status
