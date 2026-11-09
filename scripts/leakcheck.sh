#!/bin/sh
set -eu

# Check both the index and non-ignored working files in a repository.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    files=$(git ls-files --cached --others --exclude-standard)
else
    files=$(find . -type f -not -path './.git/*')
fi

status=0
hits=$(printf '%s\n' "$files" | grep -iE '(^|/)(log[.]key|games(/|$))|[.](exe|dll|sav)$' || :)
if [ -n "$hits" ]; then
    printf 'Forbidden paths:\n%s\n' "$hits"
    status=1
fi

# Avoid matching this script, which contains the patterns being checked.
denylist="scripts/leakcheck-denylist.txt"
pattern='sk-[[:alnum:]]{16,}|([0-9]{1,3}[.]){3}[0-9]{1,3}|/Users/|/root/'
# The optional local denylist adds repository-specific patterns.
if [ -s "$denylist" ]; then
    pattern="$pattern|$(cat "$denylist")"
fi
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git grep -InI --untracked -e . -- . ':!scripts/leakcheck.sh' ':!scripts/leakcheck-denylist.txt' > "$tmp/working" || code=$?
    if [ "${code:-0}" -gt 1 ]; then exit "$code"; fi
    code=0
    git grep -InI --cached -e . -- . ':!scripts/leakcheck.sh' ':!scripts/leakcheck-denylist.txt' > "$tmp/index" || code=$?
    if [ "$code" -gt 1 ]; then exit "$code"; fi
else
    # find supplies filenames to grep without interpreting them as options.
    find . -type f ! -path './scripts/leakcheck.sh' ! -path './scripts/leakcheck-denylist.txt' \
        -exec grep -InI -e . /dev/null {} + > "$tmp/working" || code=$?
    if [ "${code:-0}" -gt 1 ]; then exit "$code"; fi
    : > "$tmp/index"
fi
hits=$(cat "$tmp/working" "$tmp/index" | perl -pe 's/(?<![0-9.])(?:127\.0\.0\.1|0\.0\.0\.0)(?![0-9.])/<allowed-address>/g; s{(?<![[:alnum:]_./])(/proc/(?:[0-9]+|\{pid\}))/root/}{$1/<allowed-root>/}g' | grep -iE "$pattern" || :)
if [ -n "$hits" ]; then
    printf 'Forbidden content:\n%s\n' "$hits"
    status=1
fi
exit "$status"
