# example/meta/bootstrap.sh

function owtInOwt() {
  URL="$1"
  PORT="$2"
  PAYLOAD_CODE_B64="$3"
  PAYLOAD_KWARGS_B64="$4"
  read -r -d '' CODE << EOF
def run(request, payload_code_b64, payload_kwargs_b64):
  _globals = {'__name__': __name__+'_new',
              'new_port': args.port + 1}
  _locals = {}
  print('going one level down to port %s' % _globals['new_port'])

  exec('''
print('One level deeper, importing owt')
from owt import *
from multiprocessing import Process
args.port = new_port
server_thread = Process(target=main)
''', _globals, _locals)

  def kill():
    import time
    # time.sleep(1)
    print('Killing server on %s' % args.port)
    _locals['server_thread'].terminate()
    print('Killed server on %d' % args.port)

  from multiprocessing import Process
  import requests
  import urllib

  _locals['server_thread'].start()
  bootstrapped_url = f"$URL:{_globals['new_port']}/{request.path}?code_b64={urllib.parse.quote_plus(payload_code_b64)}&kwargs_b64={urllib.parse.quote_plus(payload_kwargs_b64)}"
  print(bootstrapped_url)
  resp = requests.get(bootstrapped_url).content
  Process(target=kill).start()
  return resp
EOF

  CODE_B64=$(base64 -w 0 <<< "$CODE")
  KWARGS_B64=$(base64 -w 0 <<< "{\"payload_code_b64\":\"$PAYLOAD_CODE_B64\", \"payload_kwargs_b64\": \"$PAYLOAD_KWARGS_B64\"}")
  CMD="curl -G --data-urlencode code_b64=$CODE_B64 --data-urlencode kwargs_b64=$KWARGS_B64 $URL:$PORT"
  echo $CMD
}
