#!/usr/bin/env bash
# Drive the whole karakeep round-trip experiment as one job: start the service,
# backfill through real HTTP, run the query set three ways, apply the frozen
# rules. Resumable -- rerunning it picks the push up where it stopped.
#
#   RT=/workspace/rt bash scripts/karakeep_roundtrip_run.sh
set -uo pipefail

RT="${RT:-/workspace/rt}"
FM="${FM:-/workspace/fm}"
CONFIGS="${CONFIGS:-A,full}"
BATCH="${BATCH:-32}"

export FACETMARK_DATA_DIR="$RT"
export FACETMARK_DB_NAME=bridged.db
export FACETMARK_HOST=127.0.0.1
export FACETMARK_PORT="${FACETMARK_PORT:-8787}"
export FACETMARK_EMBED_BACKEND=local
export FACETMARK_EMBED_MODEL=bge-m3
export FACETMARK_EMBED_DIM=1024
export FACETMARK_LOCAL_EMBED_PATH="${FACETMARK_LOCAL_EMBED_PATH:-/workspace/models/bge-m3}"
export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024
export FACETMARK_LOCAL_EMBED_BATCH="${FACETMARK_LOCAL_EMBED_BATCH:-16}"
export FACETMARK_API_KEY="${FACETMARK_API_KEY:-placeholder-no-chat-needed}"
export FACETMARK_REQUEST_TIMEOUT=120
URL="http://127.0.0.1:${FACETMARK_PORT}"

cd "$FM"
# shellcheck disable=SC1091
. .venv/bin/activate

echo "== starting service on $URL"
facetmark serve > "$RT/serve.log" 2>&1 &
SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null' EXIT

for _ in $(seq 1 60); do
  curl -sf "$URL/health" > /dev/null && break
  sleep 2
done
curl -sf "$URL/health" || { echo "service did not come up"; tail -20 "$RT/serve.log"; exit 1; }
echo

echo "== phase push"
python scripts/karakeep_roundtrip.py push \
  --docs "$RT/docs.jsonl" --token "$RT/pairing-token.txt" \
  --url "$URL" --batch "$BATCH" --resume || exit 1

echo "== phase query"
python scripts/karakeep_roundtrip.py query \
  --src "$RT/source.db" --db "$RT/bridged.db" \
  --queries eval/queries/w2w3-holdout.jsonl \
  --token "$RT/pairing-token.txt" --url "$URL" \
  --configs "$CONFIGS" --out "$RT/runs.json" || exit 1

echo "== phase verdict"
python scripts/karakeep_roundtrip.py verdict \
  --runs "$RT/runs.json" --out "$RT/roundtrip.json" || exit 1

echo "== done"
