# example/summat/simple.sh

URL="$1"
read -r -d '' CODE << EOF
from owt import summat as s

run = (
    s.pipe()
    .to(s.LoadFile(root_dir='./example/summat'))
    .to(s.NameOutput(name='buf'))
    .to(s.BufferSink())
    .f(lambda ab: (str(ab[0]).upper(), ab[1]))
    .done()
)
EOF

curl --json $(jo \
  code_b64=$(echo "$CODE" | base64 -w 0) \
  kwargs_b64=$(echo "{'path': 'simple.sh'}" | base64 -w 0) \
) $URL
