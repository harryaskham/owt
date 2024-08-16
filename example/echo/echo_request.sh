URL="$1"
CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
curl $URL/owt?code_b64=$CODE_B64
