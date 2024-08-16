# example/bark/bark.sh
#
# Usage:
# ./example/bark/bark.sh \
#   http://localhost:9876/file.wav \
#   "Hello world! This is a test." \
#   /tmp/output_file.wav

URL="$1"
TEXT="$2"
OUTFILE="$3"

CODE="$(< example/bark/bark.py)"
KWARGS="{'text': '$TEXT'}"
JSON=$(jo \
  code_b64=$(echo "$CODE" | base64 -w 0) \
  kwargs_b64=$(echo "$KWARGS" | base64 -w 0) \
  use_cache="true" \
  cache_kwargs="true" \
)
CMD="curl --json $JSON $URL -o $OUTFILE"

echo "Running $CMD"
$CMD
echo "Wrote $OUTFILE"
