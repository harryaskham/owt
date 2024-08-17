# example/summat/simple.sh

URL="$1"
read -r -d '' CODE << EOF
from typing import TypedDict
import owt
from owt import summat

class Args(summat.Args):
  path: str

run = (
    summat
    .pipeline(Args)
    .into(summat.LoadFile(root_dir='./example/summat'))
    .into(summat.NameOutput(name='buf'))
    .into(summat.BufferSink())
    .build()
)
EOF
curl --json $(jo \
  code_b64=$(echo "$CODE" | base64 -w 0) \
  kwargs_b64=$(echo "{'path': 'simple.sh'}" | base64 -w 0) \
) $URL
