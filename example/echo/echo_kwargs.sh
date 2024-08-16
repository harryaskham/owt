URL="$1"
CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
KWARGS_B64=$(echo "{'name': 'owt'}" | base64 -w 0)
curl --json $(jo code_b64=$CODE_B64 kwargs_b64=$KWARGS_B64) $URL/hello
