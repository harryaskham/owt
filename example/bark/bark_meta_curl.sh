URL="$1"
read -r -d '' CODE << 'EOF'
def run(_, base_url):
  import os
  html = os.popen(f'bash -c "$(./example/bark/bark_construct_curl.sh {base_url})"').read()
  return html
EOF

KWARGS="{\"base_url\": \"$URL\"}"
CODE_B64=$(base64 -w 0 <<< "$CODE")
KWARGS_B64=$(base64 -w 0 <<< "$KWARGS")
echo "curl -G --data-urlencode code_b64=$CODE_B64 --data-urlencode kwargs_b64=$KWARGS_B64 $URL"
