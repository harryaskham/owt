# example/bark/bark.sh
#
# Usage:
# ./example/bark/bark.sh http://localhost:9876/file.wav "Hello world! This is a test." /tmp/output_dir

URL="$1"
TEXT="$2"
OUTDIR="$3"

CODE_B64="$(cat example/bark/bark.py | base64 -w 0)"
KWARGS_B64=$(echo "{\"text\": \"$TEXT\"}" | base64 -w 0)
JSON=$(jo \
  code_b64=$CODE_B64 \
  kwargs_b64=$KWARGS_B64 \
  use_cache="true" \
  cache_kwargs="true" \
)
CMD="curl --json $JSON $URL"

echo "Running $CMD"
I=0
for event in "$($CMD)"; do
  if [[ "$event" == "data: {"* ]]; then
    WAV="$(echo -n "$event" | sed 's/data: //g' | jq '.sentence' | base64 -d)"
    echo "$WAV" > "$OUTDIR/sentence$I.wav"
    I=$((I+1))
  fi
done
