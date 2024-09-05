# example/meta/bootstrap.sh

function owtInOwt() {
  URL_PORT="$1"
  PAYLOAD_CODE_B64="$2"
  PAYLOAD_KWARGS_B64="$3"
  read -r -d '' CODE << EOF
def run(**kwargs):
  payload_code_b64 = kwargs['payload_code_b64']
  payload_kwargs_b64 = kwargs['payload_kwargs_b64']
  global _SERVER
  new_port = _SERVER.port + 1
  _globals = {'__name__': __name__+'_new',
              'new_port': new_port}
  _locals = {}
  print('going one level down to port %s' % new_port)

  exec('''
print('One level deeper, importing owt')
from owt import server
from multiprocessing import Process
server_thread = Process(target=server.main, kwargs={"port": new_port})
''', _globals, _locals)

  def kill():
    import time
    time.sleep(5)
    print('Killing server on %s' % Server.sing().port)
    _locals['server_thread'].terminate()
    print('Killed server on %d' % Server.sing().port)

  from multiprocessing import Process
  from flask import request
  import requests
  import urllib

  _locals['server_thread'].start()
  port = urllib.parse.urlparse("$URL_PORT").port
  new_url = "$URL_PORT".replace(str(port), str(new_port))
  bootstrapped_url = f"{new_url}?code_b64={urllib.parse.quote_plus(payload_code_b64)}&kwargs_b64={urllib.parse.quote_plus(payload_kwargs_b64)}"
  resp = requests.get(bootstrapped_url).content
  Process(target=kill).start()
  return resp
EOF

  CODE_B64=$(base64 -w 0 <<< "$CODE")
  KWARGS_B64=$(base64 -w 0 <<< "{\"payload_code_b64\":\"$PAYLOAD_CODE_B64\", \"payload_kwargs_b64\": \"$PAYLOAD_KWARGS_B64\"}")
  CMD="curl -G --data-urlencode code_b64=$CODE_B64 --data-urlencode kwargs_b64=$KWARGS_B64 $URL_PORT"
  echo $CMD
}
