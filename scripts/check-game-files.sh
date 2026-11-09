#!/bin/sh
# Check the supported executable before loading it into the game process.
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: $0 GAME_DIR [UCP3_ZIP]" >&2
    exit 2
fi

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | cut -d ' ' -f 1
    else
        echo "Install sha256sum or shasum to verify game files." >&2
        exit 1
    fi
}

check_file() {
    file=$1 expected=$2 label=$3
    if [ ! -f "$file" ] || [ ! -r "$file" ]; then
        echo "$label is missing or unreadable: $file" >&2
        exit 1
    fi
    actual=$(hash_file "$file")
    if [ "$actual" != "$expected" ]; then
        echo "$label SHA-256 mismatch: got $actual, expected $expected" >&2
        exit 1
    fi
}

check_file "$1/Stronghold Crusader.exe" \
    3bb0a8c1e72331b3a30a5aa93ed94beca0081b476b04c1960e26d5b45387ac5a \
    "Game executable"
if [ "$#" -eq 2 ]; then
    check_file "$2" a979816e4475e054b46b2f2793ef6a2109cfd03bf650e58e2b2f764804a8c105 \
        "UCP3 archive"
fi
printf '%s\n' "Game files verified."
