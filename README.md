
# Table of Contents

1.  [Owt](#org04494e2)
    1.  [What&rsquo;s This?](#org29e9c16)
        1.  [Security](#org0bd0d77)
        2.  [Why?](#org54d544a)
        3.  [How?](#org4ac6bcb)
        4.  [Examples](#orgecb27a5)


<a id="org04494e2"></a>

# Owt

Serve up owt yer fancy on t&rsquo;fly.


<a id="org29e9c16"></a>

## What&rsquo;s This?

A Flask app exposing an endpoint whose request handling behaviour is configured by the request itself.


<a id="org0bd0d77"></a>

### Security

**This works by evaluating arbitrary user-supplied strings as code. This is grossly insecure by its very nature; don&rsquo;t expose it to the internet!**

There&rsquo;s support for basic auth via `--auth="username:sha256(password)"` but still, exercise caution. It would not be difficult to accidentally make an `owt` API call that irreversibly destroyed your own machine.


<a id="org54d544a"></a>

### Why?

The primary motivation is rapid prototyping against new machine learning models from languages other than Python. So often the newest hotness drops with a checkpoint and a Python client, and using this outside of the specific ecosystem in which it is designed to run means one of:

1.  FFI-wrapping the library to get native-looking calls in your language (or use an embedded Python if your language has it)
    -   Painful and bespoke-to-each-new-library work to figure out how to make all necessary requirements, virtualenv setup, CUDA flags, etc available.
    -   Or, now your software only works inside a virtualenv.
2.  Spawn `python some_project.py --flag=...`" as a child process
    -   Handle communication over stdin/out/err can be a pain.
    -   Wrapping
3.  Docker-ify it
    -   Long; CUDA can be annoying; still need to expose the logic by one of the other methods.
4.  Building a lightweight API backend exposing the Python logic and writing client code in your language of choice
    -   **Annoying boilerplate, the time between &ldquo;I can run `python generate.py --animal=cat > pic.png` on my machine&rdquo; and "I have some ~generate:** Animal -> IO Image~" can be >1h.
    -   Either one new service for every new library you want to test out, or now you need to maintain a growing monolith of unrelated endpoints

`owt` aims to make #4 less painful, at the cost of security and sanity, by providing a single service capable of serving arbitrary new logic without requiring changes to `owt` itself.


<a id="org4ac6bcb"></a>

### How?

The cost of supporting some new system is pushed to the client, who must send adaptor code (a request handler, essentially) along with the request. This creates a virtual endpoint on the fly, giving complete control over the serving logic to the API user.

Writing the adaptor code is a one-time cost for each new virtual endpoint, made cheaper by having access to `owt.summat`, a collection of composable building blocks.


<a id="orgecb27a5"></a>

### Examples

The following examples (in `example/`) could all be run one-by-one without any need to restart or rebuild `owt`. The first one is shown a few different ways to give a flavour of usage. Subsequent examples just show `curl` in tandem with an adaptor `.py` file, but it&rsquo;s easy to see how one could extend from here to call to `owt` from any other language.

1.  Echo Server

    By default, the function named `run(request, **kwargs)` in the user-supplied code will be used to handle the request.
    Code and (optionally) arguments are supplied as `code_b64` and `kwargs_b64`. `kwargs_b64` is `eval`&rsquo;d to get the resulting dictionary, so can itself contain richer logic to build up arguments.
    
    1.  As a self-contained shell script
    
            URL="$1"
            
            read -r -d '' CODE << EOF
            def run(_, name: str):
              return f'Hello, {name}!'
            EOF
            
            curl --json $(jo \
              code_b64=$(echo "$CODE" | base64 -w 0) \
              kwargs_b64=$(echo "{'name': 'owt'}" | base64 -w 0) \
            ) $URL/hello
        
            ./example/echo/echo_script.sh http://localhost:9876
        
        Hello, owt!
    
    2.  As a Python file + script
    
            def run(request, name=None):
                # Loads from either the free-text path or the request body
                if not name:
                    name = request.path.split("/")[-1]
                return f"Hello, {name}!"
        
        Passing data via POST JSON `kwargs`:
        
            URL="$1"
            CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
            KWARGS_B64=$(echo "{'name': 'owt'}" | base64 -w 0)
            curl --json $(jo code_b64=$CODE_B64 kwargs_b64=$KWARGS_B64) $URL/hello
        
            ./example/echo/echo_kwargs.sh http://localhost:9876
        
        Hello, owt!
        
        Passing data via GET in the path:
        
            URL="$1"
            CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
            curl $URL/owt?code_b64=$CODE_B64
        
            ./example/echo/echo_request.sh http://localhost:9876
        
        <!doctype html>
        <html lang=en>
        <title>404 Not Found</title>
        <h1>Not Found</h1>
        <p>The requested URL was not found on the server. If you entered the URL manually please check your spelling and try again.</p>

2.  Text to Speech API

    A more complex example demonstrating wrapping Suno&rsquo;s OSS TTS model (<https://github.com/suno-ai/bark>)[Bark].
    The client provides an adaptor that responds with a stream of bytes, allowing the generated audio to be streamed in chunks, sentence-by-sentence.
    Responses are cached for the lifetime of the `owt` server for each combination of `(text, speaker)`.
    The `preload_models()` call makes the first call take a while as VRAM is populated, but the weights remain in memory so subsequent calls are cheaper.
    To avoid this breaking other `owt` uses, one can spin up multiple instances of `owt`, each handling a different kind of task and with different resource profiles.
    
    1.  Python Adaptor
    
            def run(request, text: str, speaker: str = "v2/en_speaker_6"):
                import os
                import logging
                import io
                import nltk
                from scipy.io.wavfile import write as write_wav
            
                os.environ["CUDA_VISIBLE_DEVICES"] = "0"
                os.environ["SUNO_USE_SMALL_MODELS"] = "0"
                os.environ["SUNO_OFFLOAD_CPU"] = "0"
            
                from bark.generation import generate_text_semantic, preload_models
                from bark import generate_audio, SAMPLE_RATE
            
                preload_models()
            
                def generate():
                    sentences = nltk.sent_tokenize(text.replace("\n", " ").strip())
                    for i, sentence in enumerate(sentences):
                        logging.info(
                            "Generating sentence %d/%d: %s", i + 1, len(sentences), sentence
                        )
                        wav_array = generate_audio(sentence, history_prompt=speaker)
                        buf = io.BytesIO()
                        write_wav(buf, SAMPLE_RATE, wav_array)
                        yield buf.read()
            
                return generate(), {"Content-Type": "audio/mpeg"}
    
    2.  Save audio via cURL
    
            # Usage:
            # ./example/bark/bark.sh \
            #   http://localhost:9876/file.wav \
            #   "Hello world! This is a test." \
            #   /tmp/output_file.wav
            
            URL="$1"
            TEXT="$2"
            OUTFILE="$3"
            
            CODE="$(< example/bark/bark.py)"
            KWARGS="{'text': '$TEXT'}"
            JSON=$(jo \
              code_b64=$(echo "$CODE" | base64 -w 0) \
              kwargs_b64=$(echo "$KWARGS" | base64 -w 0) \
              use_cache="true" \
              cache_kwargs="true" \
            )
            CMD="curl --json $JSON $URL -o $OUTFILE"
            
            echo "Running $CMD"
            $CMD
            echo "Wrote $OUTFILE"
    
    3.  Stream audio via JS
    
        See `example/bark/bark.html` for usage.
        
            function makeRequest(code, text) {
              return {
                'code_b64': btoa(code),
                'kwargs_b64': btoa('{"text": "' + text + '"}')
              };
            }
            
            async function getAudio(url, code, text, onChunk, onDone) {
              let response = await fetch(url, {
                  method: 'POST',
                  headers: {
                      'Content-Type': 'application/json',
                  },
                  body: JSON.stringify(makeRequest(code, text))
              });
              if (!response.ok) {
                throw new Error(await response.text());
              }
              const reader = response.body.getReader();
              reader.read().then(({ done, chunk }) => {
                if (chunk) {
                  onChunk(chunk);
                }
                if (done) {
                  onDone();
                }
              });
            }
    
    4.  Ad-hoc Web Server
    
        In fact we can go one step further and create an adhoc endpoint that serves us the rendered `bark.html` Jinja2 template.
        
        The `owt` arguments can be passed as GET query parameters as well as POST JSON data, so we can actually write a handler that embeds the entire HTML into the query with this Python-in-Python-in-Bash curiosity.
        
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
        
            ./example/bark/bark_construct_curl.sh http://localhost:9876
        
        curl -G --data-urlencode "code_b64=CmRlZiBydW4oXyk6CiAgZnJvbSBmbGFzayBpbXBvcnQgcmVuZGVyX3RlbXBsYXRlCiAgdHJ5OgogICAgICByZW5kZXJfdGVtcGxhdGUoJycnPCFkb2N0eXBlIGh0bWw+CjxodG1sPgogIDxoZWFkPgogICAgPHRpdGxlPmJhcmsgdGVzdDwvdGl0bGU+CiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuLnNpbXBsZWNzcy5vcmcvc2ltcGxlLm1pbi5jc3MiPgogICAgPHNjcmlwdD4KZnVuY3Rpb24gbWFrZVJlcXVlc3QoY29kZSwgdGV4dCkgewogIHJldHVybiB7CiAgICAnY29kZV9iNjQnOiBidG9hKGNvZGUpLAogICAgJ2t3YXJnc19iNjQnOiBidG9hKCd7InRleHQiOiAiJyArIHRleHQgKyAnIn0nKQogIH07Cn0KCmFzeW5jIGZ1bmN0aW9uIGdldEF1ZGlvKHVybCwgY29kZSwgdGV4dCwgb25DaHVuaywgb25Eb25lKSB7CiAgbGV0IHJlc3BvbnNlID0gYXdhaXQgZmV0Y2godXJsLCB7CiAgICAgIG1ldGhvZDogJ1BPU1QnLAogICAgICBoZWFkZXJzOiB7CiAgICAgICAgICAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nLAogICAgICB9LAogICAgICBib2R5OiBKU09OLnN0cmluZ2lmeShtYWtlUmVxdWVzdChjb2RlLCB0ZXh0KSkKICB9KTsKICBpZiAoIXJlc3BvbnNlLm9rKSB7CiAgICB0aHJvdyBuZXcgRXJyb3IoYXdhaXQgcmVzcG9uc2UudGV4dCgpKTsKICB9CiAgY29uc3QgcmVhZGVyID0gcmVzcG9uc2UuYm9keS5nZXRSZWFkZXIoKTsKICByZWFkZXIucmVhZCgpLnRoZW4oKHsgZG9uZSwgY2h1bmsgfSkgPT4gewogICAgaWYgKGNodW5rKSB7CiAgICAgIG9uQ2h1bmsoY2h1bmspOwogICAgfQogICAgaWYgKGRvbmUpIHsKICAgICAgb25Eb25lKCk7CiAgICB9CiAgfSk7Cn0KCjwvc2NyaXB0PgogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY29kZS5qcXVlcnkuY29tL2pxdWVyeS0zLjcuMS5qcyIgaW50ZWdyaXR5PSJzaGEyNTYtZUtoYXlpOExFUXdwNE5LeE4rQ2ZDaCszcU9WVXRKbjNRTlowVGNpV0xQND0iIGNyb3Nzb3JpZ2luPSJhbm9ueW1vdXMiPjwvc2NyaXB0PgogICAgPHNjcmlwdD4KICAgICAgZnVuY3Rpb24gY29kZSgpIHsKICAgICAgICByZXR1cm4gJCgiI2NvZGUiKS50ZXh0KCk7CiAgICAgIH0KCiAgICAgIGZ1bmN0aW9uIHVybCgpIHsKICAgICAgICByZXR1cm4gJCgiI3VybCIpLnZhbCgpOyAgIAogICAgICB9CgogICAgICBmdW5jdGlvbiBiYXJrVGV4dCgpIHsKICAgICAgICByZXR1cm4gJCgnI2JhcmstaW5wdXQnKS52YWwoKTsKICAgICAgfQoKCiAgICAgIGZ1bmN0aW9uIGF1ZGlvVXJsKGNvZGUsIHRleHQpIHsKICAgICAgICBjb25zdCByZXF1ZXN0ID0gbWFrZVJlcXVlc3QoY29kZSwgdGV4dCk7CiAgICAgICAgcmV0dXJuIHVybCgpICsgJz8nICsgJC5wYXJhbShyZXF1ZXN0KTsKICAgICAgfQoKCiAgICAgIGZ1bmN0aW9uIGF1ZGlvQ2h1bmtIYW5kbGVyKGNodW5rKSB7CiAgICAgICAgY29uc29sZS5sb2coJ2F1ZGlvIGNodW5rJywgY2h1bmspOwogICAgICAgIHNldEF1ZGlvRGF0YVVSTChbY2h1bmtdKTsKICAgICAgfQoKICAgICAgZnVuY3Rpb24gYXVkaW9Eb25lSGFuZGxlcigpIHsKICAgICAgICBjb25zb2xlLmxvZygnYXVkaW8gZG9uZScpOwogICAgICB9CgogICAgICBmdW5jdGlvbiBoYW5kbGVTcGVhaygpIHsKICAgICAgICByZXR1cm4gZ2V0QXVkaW8odXJsKCksIGNvZGUoKSwgdGV4dCgpLCBhdWRpb0NodW5rSGFuZGxlciwgYXVkaW9Eb25lSGFuZGxlcik7CiAgICAgIH0KCiAgICAgIGNvbnN0IGF1ZGlvID0gbmV3IEF1ZGlvKCk7CgogICAgICBmdW5jdGlvbiBzZXRBdWRpb0RhdGFVUkwodmFsdWVzKSB7CiAgICAgICAgY29uc29sZS5sb2coJ3NldHRpbmcgYXVkaW8gZGF0YSB1cmwnLCB2YWx1ZXMpOwogICAgICAgIGNvbnN0IGJsb2IgPSBuZXcgQmxvYih2YWx1ZXMsIHsgdHlwZTogJ2F1ZGlvL3dhdicgfSk7CiAgICAgICAgY29uc29sZS5sb2coJ3NldHRpbmcgYXVkaW8gZGF0YSB1cmwnLCB2YWx1ZXMsIGJsb2IpOwogICAgICAgIGF1ZGlvLnNyYyA9IFVSTC5jcmVhdGVPYmplY3RVUkwoYmxvYik7CiAgICAgICAgYXVkaW8ucGxheSgpOwogICAgICB9CgogICAgICAkKGZ1bmN0aW9uKCkgewogICAgICAgIGNvbnN0IGF1ZGlvRGl2ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2Jhcmstb3V0cHV0Jyk7CiAgICAgICAgYXVkaW8uY29udHJvbHMgPSB0cnVlOwogICAgICAgIGF1ZGlvRGl2LmFwcGVuZENoaWxkKGF1ZGlvKTsKICAgICAgICBhdWRpby5hZGRFdmVudExpc3RlbmVyKCdsb2FkZWRkYXRhJywgKCkgPT4gewogICAgICAgICAgYXVkaW8ucGxheSgpOwogICAgICAgIH0pOwogICAgICB9KTsKICAgIDwvc2NyaXB0PgogIDwvaGVhZD4KICA8Ym9keT4KICAgIDxsYWJlbCBmb3I9InVybCI+RXhlYyBVUkw8L2xhYmVsPgogICAgPGlucHV0IHR5cGU9InRleHQiIGlkPSJ1cmwiIHZhbHVlPSJodHRwOi8vbG9jYWxob3N0Ojk4NzYvdGVzdC53YXYiPjwvaW5wdXQ+CiAgICA8bGFiZWwgZm9yPSJiYXJrLWlucHV0Ij5UZXh0IHRvIHNwZWFrPC9sYWJlbD4KICAgIDx0ZXh0YXJlYSBpZD0iYmFyay1pbnB1dCI+VGVzdCBzZW50ZW5jZS4gQW5kIGEgc2Vjb25kIHRlc3QuPC90ZXh0YXJlYT4KICAgIDxidXR0b24gb25jbGljaz0iaGFuZGxlU3BlYWsiPlNwZWFrPC9idXR0b24+CiAgICA8ZGl2IGlkPSJiYXJrLW91dHB1dCI+PC9kaXY+CiAgICA8cHJlPgogICAgICA8Y29kZSBpZD0iY29kZSIgY29udGVudGVkaXRhYmxlPSJ0cnVlIj4KZGVmIHJ1bihyZXF1ZXN0LCB0ZXh0OiBzdHIsIHNwZWFrZXI6IHN0ciA9ICJ2Mi9lbl9zcGVha2VyXzYiKToKICAgIGltcG9ydCBvcwogICAgaW1wb3J0IGxvZ2dpbmcKICAgIGltcG9ydCBpbwogICAgaW1wb3J0IG5sdGsKICAgIGZyb20gc2NpcHkuaW8ud2F2ZmlsZSBpbXBvcnQgd3JpdGUgYXMgd3JpdGVfd2F2CgogICAgb3MuZW52aXJvblsiQ1VEQV9WSVNJQkxFX0RFVklDRVMiXSA9ICIwIgogICAgb3MuZW52aXJvblsiU1VOT19VU0VfU01BTExfTU9ERUxTIl0gPSAiMCIKICAgIG9zLmVudmlyb25bIlNVTk9fT0ZGTE9BRF9DUFUiXSA9ICIwIgoKICAgIGZyb20gYmFyay5nZW5lcmF0aW9uIGltcG9ydCBnZW5lcmF0ZV90ZXh0X3NlbWFudGljLCBwcmVsb2FkX21vZGVscwogICAgZnJvbSBiYXJrIGltcG9ydCBnZW5lcmF0ZV9hdWRpbywgU0FNUExFX1JBVEUKCiAgICBwcmVsb2FkX21vZGVscygpCgogICAgZGVmIGdlbmVyYXRlKCk6CiAgICAgICAgc2VudGVuY2VzID0gbmx0ay5zZW50X3Rva2VuaXplKHRleHQucmVwbGFjZSgiXG4iLCAiICIpLnN0cmlwKCkpCiAgICAgICAgZm9yIGksIHNlbnRlbmNlIGluIGVudW1lcmF0ZShzZW50ZW5jZXMpOgogICAgICAgICAgICBsb2dnaW5nLmluZm8oCiAgICAgICAgICAgICAgICAiR2VuZXJhdGluZyBzZW50ZW5jZSAlZC8lZDogJXMiLCBpICsgMSwgbGVuKHNlbnRlbmNlcyksIHNlbnRlbmNlCiAgICAgICAgICAgICkKICAgICAgICAgICAgd2F2X2FycmF5ID0gZ2VuZXJhdGVfYXVkaW8oc2VudGVuY2UsIGhpc3RvcnlfcHJvbXB0PXNwZWFrZXIpCiAgICAgICAgICAgIGJ1ZiA9IGlvLkJ5dGVzSU8oKQogICAgICAgICAgICB3cml0ZV93YXYoYnVmLCBTQU1QTEVfUkFURSwgd2F2X2FycmF5KQogICAgICAgICAgICB5aWVsZCBidWYucmVhZCgpCgogICAgcmV0dXJuIGdlbmVyYXRlKCksIHsiQ29udGVudC1UeXBlIjogImF1ZGlvL21wZWcifQoKICAgICAgPC9jb2RlPgogICAgPC9wcmU+CiAgPC9ib2R5Pgo8L2h0bWw+CicnJykKICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgIHJldHVybiBzdHIoZSkK" http://localhost:9876
        
        And actually running it to get the URL:
        
            bash -c "$(./example/bark/bark_construct_curl.sh http://localhost:9876) -s -o /dev/null -w '%{url}'"
        
        http://localhost:9876/?code_b64=CmRlZiBydW4oXyk6CiAgZnJvbSBmbGFzayBpbXBvcnQgcmVuZGVyX3RlbXBsYXRlCiAgdHJ5OgogICAgICByZW5kZXJfdGVtcGxhdGUoJycnPCFkb2N0eXBlIGh0bWw%2bCjxodG1sPgogIDxoZWFkPgogICAgPHRpdGxlPmJhcmsgdGVzdDwvdGl0bGU%2bCiAgICA8bGluayByZWw9InN0eWxlc2hlZXQiIGhyZWY9Imh0dHBzOi8vY2RuLnNpbXBsZWNzcy5vcmcvc2ltcGxlLm1pbi5jc3MiPgogICAgPHNjcmlwdD4KZnVuY3Rpb24gbWFrZVJlcXVlc3QoY29kZSwgdGV4dCkgewogIHJldHVybiB7CiAgICAnY29kZV9iNjQnOiBidG9hKGNvZGUpLAogICAgJ2t3YXJnc19iNjQnOiBidG9hKCd7InRleHQiOiAiJyArIHRleHQgKyAnIn0nKQogIH07Cn0KCmFzeW5jIGZ1bmN0aW9uIGdldEF1ZGlvKHVybCwgY29kZSwgdGV4dCwgb25DaHVuaywgb25Eb25lKSB7CiAgbGV0IHJlc3BvbnNlID0gYXdhaXQgZmV0Y2godXJsLCB7CiAgICAgIG1ldGhvZDogJ1BPU1QnLAogICAgICBoZWFkZXJzOiB7CiAgICAgICAgICAnQ29udGVudC1UeXBlJzogJ2FwcGxpY2F0aW9uL2pzb24nLAogICAgICB9LAogICAgICBib2R5OiBKU09OLnN0cmluZ2lmeShtYWtlUmVxdWVzdChjb2RlLCB0ZXh0KSkKICB9KTsKICBpZiAoIXJlc3BvbnNlLm9rKSB7CiAgICB0aHJvdyBuZXcgRXJyb3IoYXdhaXQgcmVzcG9uc2UudGV4dCgpKTsKICB9CiAgY29uc3QgcmVhZGVyID0gcmVzcG9uc2UuYm9keS5nZXRSZWFkZXIoKTsKICByZWFkZXIucmVhZCgpLnRoZW4oKHsgZG9uZSwgY2h1bmsgfSkgPT4gewogICAgaWYgKGNodW5rKSB7CiAgICAgIG9uQ2h1bmsoY2h1bmspOwogICAgfQogICAgaWYgKGRvbmUpIHsKICAgICAgb25Eb25lKCk7CiAgICB9CiAgfSk7Cn0KCjwvc2NyaXB0PgogICAgPHNjcmlwdCBzcmM9Imh0dHBzOi8vY29kZS5qcXVlcnkuY29tL2pxdWVyeS0zLjcuMS5qcyIgaW50ZWdyaXR5PSJzaGEyNTYtZUtoYXlpOExFUXdwNE5LeE4rQ2ZDaCszcU9WVXRKbjNRTlowVGNpV0xQND0iIGNyb3Nzb3JpZ2luPSJhbm9ueW1vdXMiPjwvc2NyaXB0PgogICAgPHNjcmlwdD4KICAgICAgZnVuY3Rpb24gY29kZSgpIHsKICAgICAgICByZXR1cm4gJCgiI2NvZGUiKS50ZXh0KCk7CiAgICAgIH0KCiAgICAgIGZ1bmN0aW9uIHVybCgpIHsKICAgICAgICByZXR1cm4gJCgiI3VybCIpLnZhbCgpOyAgIAogICAgICB9CgogICAgICBmdW5jdGlvbiBiYXJrVGV4dCgpIHsKICAgICAgICByZXR1cm4gJCgnI2JhcmstaW5wdXQnKS52YWwoKTsKICAgICAgfQoKCiAgICAgIGZ1bmN0aW9uIGF1ZGlvVXJsKGNvZGUsIHRleHQpIHsKICAgICAgICBjb25zdCByZXF1ZXN0ID0gbWFrZVJlcXVlc3QoY29kZSwgdGV4dCk7CiAgICAgICAgcmV0dXJuIHVybCgpICsgJz8nICsgJC5wYXJhbShyZXF1ZXN0KTsKICAgICAgfQoKCiAgICAgIGZ1bmN0aW9uIGF1ZGlvQ2h1bmtIYW5kbGVyKGNodW5rKSB7CiAgICAgICAgY29uc29sZS5sb2coJ2F1ZGlvIGNodW5rJywgY2h1bmspOwogICAgICAgIHNldEF1ZGlvRGF0YVVSTChbY2h1bmtdKTsKICAgICAgfQoKICAgICAgZnVuY3Rpb24gYXVkaW9Eb25lSGFuZGxlcigpIHsKICAgICAgICBjb25zb2xlLmxvZygnYXVkaW8gZG9uZScpOwogICAgICB9CgogICAgICBmdW5jdGlvbiBoYW5kbGVTcGVhaygpIHsKICAgICAgICByZXR1cm4gZ2V0QXVkaW8odXJsKCksIGNvZGUoKSwgdGV4dCgpLCBhdWRpb0NodW5rSGFuZGxlciwgYXVkaW9Eb25lSGFuZGxlcik7CiAgICAgIH0KCiAgICAgIGNvbnN0IGF1ZGlvID0gbmV3IEF1ZGlvKCk7CgogICAgICBmdW5jdGlvbiBzZXRBdWRpb0RhdGFVUkwodmFsdWVzKSB7CiAgICAgICAgY29uc29sZS5sb2coJ3NldHRpbmcgYXVkaW8gZGF0YSB1cmwnLCB2YWx1ZXMpOwogICAgICAgIGNvbnN0IGJsb2IgPSBuZXcgQmxvYih2YWx1ZXMsIHsgdHlwZTogJ2F1ZGlvL3dhdicgfSk7CiAgICAgICAgY29uc29sZS5sb2coJ3NldHRpbmcgYXVkaW8gZGF0YSB1cmwnLCB2YWx1ZXMsIGJsb2IpOwogICAgICAgIGF1ZGlvLnNyYyA9IFVSTC5jcmVhdGVPYmplY3RVUkwoYmxvYik7CiAgICAgICAgYXVkaW8ucGxheSgpOwogICAgICB9CgogICAgICAkKGZ1bmN0aW9uKCkgewogICAgICAgIGNvbnN0IGF1ZGlvRGl2ID0gZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoJ2Jhcmstb3V0cHV0Jyk7CiAgICAgICAgYXVkaW8uY29udHJvbHMgPSB0cnVlOwogICAgICAgIGF1ZGlvRGl2LmFwcGVuZENoaWxkKGF1ZGlvKTsKICAgICAgICBhdWRpby5hZGRFdmVudExpc3RlbmVyKCdsb2FkZWRkYXRhJywgKCkgPT4gewogICAgICAgICAgYXVkaW8ucGxheSgpOwogICAgICAgIH0pOwogICAgICB9KTsKICAgIDwvc2NyaXB0PgogIDwvaGVhZD4KICA8Ym9keT4KICAgIDxsYWJlbCBmb3I9InVybCI%2bRXhlYyBVUkw8L2xhYmVsPgogICAgPGlucHV0IHR5cGU9InRleHQiIGlkPSJ1cmwiIHZhbHVlPSJodHRwOi8vbG9jYWxob3N0Ojk4NzYvdGVzdC53YXYiPjwvaW5wdXQ%2bCiAgICA8bGFiZWwgZm9yPSJiYXJrLWlucHV0Ij5UZXh0IHRvIHNwZWFrPC9sYWJlbD4KICAgIDx0ZXh0YXJlYSBpZD0iYmFyay1pbnB1dCI%2bVGVzdCBzZW50ZW5jZS4gQW5kIGEgc2Vjb25kIHRlc3QuPC90ZXh0YXJlYT4KICAgIDxidXR0b24gb25jbGljaz0iaGFuZGxlU3BlYWsiPlNwZWFrPC9idXR0b24%2bCiAgICA8ZGl2IGlkPSJiYXJrLW91dHB1dCI%2bPC9kaXY%2bCiAgICA8cHJlPgogICAgICA8Y29kZSBpZD0iY29kZSIgY29udGVudGVkaXRhYmxlPSJ0cnVlIj4KZGVmIHJ1bihyZXF1ZXN0LCB0ZXh0OiBzdHIsIHNwZWFrZXI6IHN0ciA9ICJ2Mi9lbl9zcGVha2VyXzYiKToKICAgIGltcG9ydCBvcwogICAgaW1wb3J0IGxvZ2dpbmcKICAgIGltcG9ydCBpbwogICAgaW1wb3J0IG5sdGsKICAgIGZyb20gc2NpcHkuaW8ud2F2ZmlsZSBpbXBvcnQgd3JpdGUgYXMgd3JpdGVfd2F2CgogICAgb3MuZW52aXJvblsiQ1VEQV9WSVNJQkxFX0RFVklDRVMiXSA9ICIwIgogICAgb3MuZW52aXJvblsiU1VOT19VU0VfU01BTExfTU9ERUxTIl0gPSAiMCIKICAgIG9zLmVudmlyb25bIlNVTk9fT0ZGTE9BRF9DUFUiXSA9ICIwIgoKICAgIGZyb20gYmFyay5nZW5lcmF0aW9uIGltcG9ydCBnZW5lcmF0ZV90ZXh0X3NlbWFudGljLCBwcmVsb2FkX21vZGVscwogICAgZnJvbSBiYXJrIGltcG9ydCBnZW5lcmF0ZV9hdWRpbywgU0FNUExFX1JBVEUKCiAgICBwcmVsb2FkX21vZGVscygpCgogICAgZGVmIGdlbmVyYXRlKCk6CiAgICAgICAgc2VudGVuY2VzID0gbmx0ay5zZW50X3Rva2VuaXplKHRleHQucmVwbGFjZSgiXG4iLCAiICIpLnN0cmlwKCkpCiAgICAgICAgZm9yIGksIHNlbnRlbmNlIGluIGVudW1lcmF0ZShzZW50ZW5jZXMpOgogICAgICAgICAgICBsb2dnaW5nLmluZm8oCiAgICAgICAgICAgICAgICAiR2VuZXJhdGluZyBzZW50ZW5jZSAlZC8lZDogJXMiLCBpICsgMSwgbGVuKHNlbnRlbmNlcyksIHNlbnRlbmNlCiAgICAgICAgICAgICkKICAgICAgICAgICAgd2F2X2FycmF5ID0gZ2VuZXJhdGVfYXVkaW8oc2VudGVuY2UsIGhpc3RvcnlfcHJvbXB0PXNwZWFrZXIpCiAgICAgICAgICAgIGJ1ZiA9IGlvLkJ5dGVzSU8oKQogICAgICAgICAgICB3cml0ZV93YXYoYnVmLCBTQU1QTEVfUkFURSwgd2F2X2FycmF5KQogICAgICAgICAgICB5aWVsZCBidWYucmVhZCgpCgogICAgcmV0dXJuIGdlbmVyYXRlKCksIHsiQ29udGVudC1UeXBlIjogImF1ZGlvL21wZWcifQoKICAgICAgPC9jb2RlPgogICAgPC9wcmU%2bCiAgPC9ib2R5Pgo8L2h0bWw%2bCicnJykKICBleGNlcHQgRXhjZXB0aW9uIGFzIGU6CiAgICAgIHJldHVybiBzdHIoZSkK
        
        Whew. We can open that `owt` URL in a browser and play with the web app, which itself makes calls to `owt` injecting the TTS logic.
    
    5.  Going Meta
    
        That gets painful though - for iterative development, you want to save your code and hit refresh. This won&rsquo;t do anything here, since all code is snapshotted into the URL itself. However&#x2026;
        
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
        
            ./example/bark/bark_meta_curl.sh http://localhost:9876
        
        curl -G --data-urlencode code_b64=ZGVmIHJ1bihfLCBiYXNlX3VybCk6CiAgaW1wb3J0IG9zCiAgaHRtbCA9IG9zLnBvcGVuKGYnYmFzaCAtYyAiJCguL2V4YW1wbGUvYmFyay9iYXJrX2NvbnN0cnVjdF9jdXJsLnNoIHtiYXNlX3VybH0pIicpLnJlYWQoKQogIHJldHVybiBodG1sCg== --data-urlencode kwargs_b64=eyJiYXNlX3VybCI6ICJodHRwOi8vbG9jYWxob3N0Ojk4NzYifQo= http://localhost:9876
        
        Sweet - this will resolve to the meta-evaluator that always renders a fresh copy of the app each time.
        
            bash -c "$(./example/bark/bark_meta_curl.sh http://localhost:9876) -s -o /dev/null -w '%{url}'"
        
        http://localhost:9876/?code_b64=ZGVmIHJ1bihfLCBiYXNlX3VybCk6CiAgaW1wb3J0IG9zCiAgaHRtbCA9IG9zLnBvcGVuKGYnYmFzaCAtYyAiJCguL2V4YW1wbGUvYmFyay9iYXJrX2NvbnN0cnVjdF9jdXJsLnNoIHtiYXNlX3VybH0pIicpLnJlYWQoKQogIHJldHVybiBodG1sCg%3d%3d&kwargs_b64=eyJiYXNlX3VybCI6ICJodHRwOi8vbG9jYWxob3N0Ojk4NzYifQo%3d
    
    6.  Going Meta-Circular
    
        Oh no&#x2026;
        
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
              print(f'Going one level down to port {_globals['new_port']}...')
            
              exec('''
            print('One level deeper, importing owt')
            from owt import *
            from multiprocessing import Process
            args.port = new_port
            server_thread = Process(target=main)
            ''', _globals, _locals)
            
              def kill():
                import time
                time.sleep(10)
                print(f'Killing server on {args.port}')
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
        
            source "example/meta/bootstrap.sh"
            
            # Load up the nice simple echo example from earlier
            CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
            KWARGS_B64=$(echo "{'name': 'owt-inside-owt'}" | base64 -w 0)
            
            # Send a request that installs a full copy of owt and calls it with the payload code+kwargs
            CMD=$(owtInOwt http://localhost 9876 "$CODE_B64" "$KWARGS_B64")
            echo "Bootstrapping $CMD"
            echo "Result:"
            bash -c "$CMD"
        
        Bootstrapping curl -G --data-urlencode code_b64=ZGVmIHJ1bihyZXF1ZXN0LCBwYXlsb2FkX2NvZGVfYjY0LCBwYXlsb2FkX2t3YXJnc19iNjQpOgogIF9nbG9iYWxzID0geydfX25hbWVfXyc6IF9fbmFtZV9fKydfbmV3JywKICAgICAgICAgICAgICAnbmV3X3BvcnQnOiBhcmdzLnBvcnQgKyAxfQogIF9sb2NhbHMgPSB7fQogIHByaW50KGYnR29pbmcgb25lIGxldmVsIGRvd24gdG8gcG9ydCB7X2dsb2JhbHNbJ25ld19wb3J0J119Li4uJykKCiAgZXhlYygnJycKcHJpbnQoJ09uZSBsZXZlbCBkZWVwZXIsIGltcG9ydGluZyBvd3QnKQpmcm9tIG93dCBpbXBvcnQgKgpmcm9tIG11bHRpcHJvY2Vzc2luZyBpbXBvcnQgUHJvY2VzcwphcmdzLnBvcnQgPSBuZXdfcG9ydApzZXJ2ZXJfdGhyZWFkID0gUHJvY2Vzcyh0YXJnZXQ9bWFpbikKJycnLCBfZ2xvYmFscywgX2xvY2FscykKCiAgZGVmIGtpbGwoKToKICAgIGltcG9ydCB0aW1lCiAgICB0aW1lLnNsZWVwKDEwKQogICAgcHJpbnQoZidLaWxsaW5nIHNlcnZlciBvbiB7YXJncy5wb3J0fScpCiAgICBfbG9jYWxzWydzZXJ2ZXJfdGhyZWFkJ10udGVybWluYXRlKCkKICAgIHByaW50KCdLaWxsZWQgc2VydmVyIG9uICVkJyAlIGFyZ3MucG9ydCkKCiAgZnJvbSBtdWx0aXByb2Nlc3NpbmcgaW1wb3J0IFByb2Nlc3MKICBpbXBvcnQgcmVxdWVzdHMKICBpbXBvcnQgdXJsbGliCgogIF9sb2NhbHNbJ3NlcnZlcl90aHJlYWQnXS5zdGFydCgpCiAgYm9vdHN0cmFwcGVkX3VybCA9IGYiaHR0cDovL2xvY2FsaG9zdDp7X2dsb2JhbHNbJ25ld19wb3J0J119L3tyZXF1ZXN0LnBhdGh9P2NvZGVfYjY0PXt1cmxsaWIucGFyc2UucXVvdGVfcGx1cyhwYXlsb2FkX2NvZGVfYjY0KX0ma3dhcmdzX2I2ND17dXJsbGliLnBhcnNlLnF1b3RlX3BsdXMocGF5bG9hZF9rd2FyZ3NfYjY0KX0iCiAgcHJpbnQoYm9vdHN0cmFwcGVkX3VybCkKICByZXNwID0gcmVxdWVzdHMuZ2V0KGJvb3RzdHJhcHBlZF91cmwpLmNvbnRlbnQKICBQcm9jZXNzKHRhcmdldD1raWxsKS5zdGFydCgpCiAgcmV0dXJuIHJlc3AK --data-urlencode kwargs_b64=eyJwYXlsb2FkX2NvZGVfYjY0IjoiWkdWbUlISjFiaWh5WlhGMVpYTjBMQ0J1WVcxbFBVNXZibVVwT2dvZ0lDQWdJeUJNYjJGa2N5Qm1jbTl0SUdWcGRHaGxjaUIwYUdVZ1puSmxaUzEwWlhoMElIQmhkR2dnYjNJZ2RHaGxJSEpsY1hWbGMzUWdZbTlrZVFvZ0lDQWdhV1lnYm05MElHNWhiV1U2Q2lBZ0lDQWdJQ0FnYm1GdFpTQTlJSEpsY1hWbGMzUXVjR0YwYUM1emNHeHBkQ2dpTHlJcFd5MHhYUW9nSUNBZ2NtVjBkWEp1SUdZaVNHVnNiRzhzSUh0dVlXMWxmU0VpQ2c9PSIsICJwYXlsb2FkX2t3YXJnc19iNjQiOiAiZXlkdVlXMWxKem9nSjI5M2RDMXBibk5wWkdVdGIzZDBKMzBLIn0K http://localhost:9876
        Result:
        Hello, owt-inside-owt!
        
        Oh no&#x2026; but that would mean&#x2026;
        
            def run(request, payload_code_b64, payload_kwargs_b64):
                import os
            
                return os.popen(
                    f'source ./example/meta/bootstrap.sh; $(owtInOwt http://localhost {args.port} "{payload_code_b64}" "{payload_kwargs_b64}")'
                ).read()
        
            METACODE_B64=$(cat example/meta/bootstrap.py | base64 -w 0)
            function wrapOwt() {
              CODE_B64="$1"
              KWARGS_B64="$2"
              METAKWARGS_B64=$(base64 -w 0 <<< "{\"payload_code_b64\":\"$CODE_B64\", \"payload_kwargs_b64\": \"$KWARGS_B64\"}")
              echo "$METAKWARGS_B64"
            }
            
            N_LAYERS="10"
            for layer in $(seq 1 $N_LAYERS); do
              CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
              NAME="owt"
              for i in $(seq 1 $layer); do
                  NAME="$NAME-inside-owt"
              done
              KWARGS_B64=$(echo "{\"name\": \"$NAME\"}" | base64 -w 0)
              METAKWARGS_B64=$(wrapOwt "$CODE_B64" "$KWARGS_B64")
              for i in seq 2 $layer; do
                  METAKWARGS_B64=$(wrapOwt "$METACODE_B64" "$METAKWARGS_B64")
              done
              echo "layer: $NAME"
              CMD="curl -G --data-urlencode code_b64=$METACODE_B64 --data-urlencode kwargs_b64=$METAKWARGS_B64 http://localhost:9876"
              echo "Result: " $(bash -c "$CMD")
            done
        
        layer: owt-inside-owt
        Result:  Hello, owt-inside-owt!
        layer: owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        layer: owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt
        Result:  Hello, owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt-inside-owt!
        
        Hoo boy. How is Python a real language.

