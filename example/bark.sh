# Usage: ./bark.sh test.wav

URL=http://localhost:9876/unsafe/exec/test.wav

DIR=$(dirname "$0")

CODE_B64="$(cat $DIR/bark.py | base64 -w 0)"

KWARGS="{'text': 'first sentence. second sentence.'}"
KWARGS_B64=$(echo "$KWARGS" | base64 -w 0)

FN_NAME="run"

JSON=$(jo code_b64="$CODE_B64" kwargs_b64="$KWARGS_B64" fn_name="$FN_NAME")
echo "Sending $JSON"
curl 2>/dev/null --json "$JSON" $URL > "$1"
