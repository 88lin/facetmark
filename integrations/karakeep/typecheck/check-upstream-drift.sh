#!/usr/bin/env bash
# Re-fetch the karakeep files this integration was written against and compare
# their git blob SHAs to upstream-pins.json.
#
# Exit 0: every pinned file is byte-identical to what the stubs were derived
#         from, so `npm run typecheck` is checking against the real contract.
# Exit 1: at least one file moved. The stubs are stale until someone reads the
#         diff and re-derives them. Nothing here can tell you whether the change
#         was cosmetic.
# Exit 2: could not fetch, or could not read the pins at all (no network,
#         renamed path, private repo, malformed JSON).
#
# The first version of this script exited 0 while checking zero files: the
# snippet that parsed the pins died on a Python 3.11 f-string restriction, the
# loop read an empty stream, and "0 unchanged, 0 drifted" printed as success. A
# check that silently checks nothing is worse than no check, so reading zero
# pins is now a hard exit 2.
#
# Override the source with KARAKEEP_REPO / KARAKEEP_REF to check a different
# fork or tag than the one pinned.
set -uo pipefail

cd "$(dirname "$0")"
PINS=upstream-pins.json

command -v git >/dev/null || { echo "need git (for hash-object)"; exit 2; }
command -v curl >/dev/null || { echo "need curl"; exit 2; }
command -v python3 >/dev/null || { echo "need python3"; exit 2; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if ! python3 - "$PINS" "$tmp/pins.tsv" "$tmp/meta.tsv" <<'PY'
import json
import sys

pins_path, out_path, meta_path = sys.argv[1:4]
with open(pins_path, encoding="utf-8") as fh:
    doc = json.load(fh)
files = doc["files"]
if not files:
    raise SystemExit("upstream-pins.json lists no files")
with open(out_path, "w", encoding="utf-8") as fh:
    for path, meta in files.items():
        fh.write("%s\t%s\n" % (path, meta["blob"]))
with open(meta_path, "w", encoding="utf-8") as fh:
    fh.write("%s\t%s\n" % (doc["repo"], doc["ref"]))
PY
then
  echo "could not read ${PINS}"
  exit 2
fi

IFS=$'\t' read -r pinned_repo pinned_ref < "$tmp/meta.tsv"
REPO=${KARAKEEP_REPO:-$pinned_repo}
REF=${KARAKEEP_REF:-$pinned_ref}
echo "checking ${REPO}@${REF} against ${PINS}"

fetch_failed=0
drifted=0
matched=0
seen=0

while IFS=$'\t' read -r path want; do
  [ -n "$path" ] || continue
  seen=$((seen + 1))
  out="$tmp/$(echo "$path" | tr / _)"
  code=$(curl -sSL -w '%{http_code}' -o "$out" \
    "https://raw.githubusercontent.com/${REPO}/${REF}/${path}" 2>/dev/null)
  if [ "$code" != "200" ]; then
    printf '  FETCH  %s (HTTP %s)\n' "$path" "$code"
    fetch_failed=$((fetch_failed + 1))
    continue
  fi
  got=$(git hash-object "$out")
  if [ "$got" = "$want" ]; then
    printf '  ok     %s\n' "$path"
    matched=$((matched + 1))
  else
    printf '  DRIFT  %s\n         pinned %s\n         actual %s\n' "$path" "$want" "$got"
    drifted=$((drifted + 1))
  fi
done < "$tmp/pins.tsv"

if [ "$seen" -eq 0 ]; then
  echo "read zero pins -- refusing to report success"
  exit 2
fi

echo "${seen} pinned: ${matched} unchanged, ${drifted} drifted, ${fetch_failed} unreachable"
[ "$fetch_failed" -gt 0 ] && exit 2
[ "$drifted" -gt 0 ] && exit 1
exit 0
