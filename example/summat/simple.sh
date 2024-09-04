# example/summat/simple.sh

URL="$1"
read -r -d '' CODE << EOF
run = (pipe()
       .kwarg('path')
       .open(root_dir='./example/summat')
       .bytes()
       .f(lambda ab: ab.decode('utf-8').upper())
       .done())
EOF

curl --json $(jo \
  code_b64=$(echo "$CODE" | base64 -w 0) \
  kwargs_b64=$(echo "{'path': 'simple.sh'}" | base64 -w 0) \
) $URL
