#!/bin/sh
set -u
cd "$(dirname "$0")/.." || exit 1
refs=$(grep -hE '^[[:space:]]*(-[[:space:]]*)?uses:' .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null | sed -E "s/^[[:space:]]*(-[[:space:]]*)?uses:[[:space:]]*['\"]?([^[:space:]'\"#]+).*/uses:\2/" | grep -vE '^uses:(\./|docker://)')
if [ -z "$refs" ]; then
  echo 'No remote actions found' >&2
  exit 1
fi
status=0
while IFS= read -r line; do
  ref=${line#*:}
  if ! printf '%s\n' "$ref" | grep -Eq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*@[0-9a-f]{40}$'; then
    printf 'Invalid action pin: %s\n' "$line" >&2
    status=1
    continue
  fi
  repo=${ref%%@*}
  repo=$(printf '%s' "$repo" | cut -d/ -f1,2)
  sha=${ref##*@}
  if gh api "repos/$repo/commits/$sha" >/dev/null; then
    printf 'OK %s\n' "$ref"
  else
    rc=$?
    printf 'FAILED %s (gh exit %s)\n' "$ref" "$rc" >&2
    status=1
  fi
done <<EOF
$refs
EOF
exit "$status"
