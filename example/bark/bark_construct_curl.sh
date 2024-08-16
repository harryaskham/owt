URL="$1"
CODE=$(python <<EOF
with open('example/bark/bark.html', 'r') as html_f:
  html = html_f.read()
  with open('example/bark/bark.py', 'r') as code_f:
    code = code_f.read()
    with open('example/bark/bark.js', 'r') as js_f:
      template = (html.replace('{% include "bark.py" %}', code)
                  .replace('<script src="/bark/bark.js"></script>',
                           '<script>\n'+js_f.read()+'\n</script>'))
      print('''
def run(_):
  from flask import render_template
  try:
      render_template(\'\'\''''+template+'''\'\'\')
  except Exception as e:
      return str(e)''')
EOF
)
CODE_B64=$(base64 -w 0 <<< "$CODE")
echo "curl -G --data-urlencode \"code_b64=$CODE_B64\" $URL"
