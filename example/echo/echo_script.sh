# example/echo/echo_script.sh

URL="$1"
read -r -d '' CODE << EOF
def run(_, name: str):
  return f'Hello, {name}!'
EOF
curl --json $(jo \
  code_b64=$(echo "$CODE" | base64 -w 0) \
  kwargs_b64=$(echo "{'name': 'owt'}" | base64 -w 0) \
) $URL/hello
