
# Table of Contents

1.  [Owt](#orgf6383ac)
    1.  [What&rsquo;s This?](#org597988e)
        1.  [Security](#orge2f5b99)
        2.  [Why?](#orgfaf7e72)
        3.  [How?](#org9d465ca)
        4.  [Examples](#org741dcfa)


<a id="orgf6383ac"></a>

# Owt

Serve up owt yer fancy on t&rsquo;fly.


<a id="org597988e"></a>

## What&rsquo;s This?

A Flask app exposing an endpoint whose request handling behaviour is configured by the request itself.


<a id="orge2f5b99"></a>

### Security

**This works by evaluating arbitrary user-supplied strings as code. This is grossly insecure by its very nature; don&rsquo;t expose it to the internet!**

There&rsquo;s support for basic auth via `--auth="username:sha256(password)"` but still, exercise caution. It would not be difficult to accidentally make an `owt` API call that irreversibly destroyed your own machine.


<a id="orgfaf7e72"></a>

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


<a id="org9d465ca"></a>

### How?

The cost of supporting some new system is pushed to the client, who must send adaptor code (a request handler, essentially) along with the request. This creates a virtual endpoint on the fly, giving complete control over the serving logic to the API user.

Writing the adaptor code is a one-time cost for each new virtual endpoint, made cheaper by having access to `owt.summat`, a collection of composable building blocks.


<a id="org741dcfa"></a>

### Examples

The following examples (in `example/`) could all be run one-by-one without any need to restart or rebuild `owt`. The first one is shown a few different ways to give a flavour of usage. Subsequent examples just show `curl` in tandem with an adaptor `.py` file, but it&rsquo;s easy to see how one could extend from here to call to `owt` from any other language.

1.  Common

        export EXEC_URL="http://localhost:9876/unsafe/exec"

2.  Echo Server

    By default, the function named `run(request, **kwargs)` in the user-supplied code will be used to handle the request.
    Code and (optionally) arguments are supplied as `code_b64` and `kwargs_b64`. `kwargs_b64` is `eval`&rsquo;d to get the resulting dictionary, so can itself contain richer logic to build up arguments.
    
    1.  As a self-contained shell script
    
            source $(dirname "$0")/../common.sh
            
            read -r -d '' CODE << EOF
            def run(_, name: str):
              return f'Hello, {name}!'
            EOF
            
            curl --json $(jo \
              code_b64=$(b64 "$CODE") \
              kwargs_b64=$(b64 "{'name': 'owt'}") \
            ) $EXEC_URL/hello
    
    2.  As a Python file + script
    
            def run(request, name=None):
                # Loads from either the free-text path or the request body
                if not name:
                    name = request.path.split("/")[-1]
                return f"Hello, {name}!"
        
        Passing data via `kwargs`:
        
            CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
            KWARGS_B64=$(echo "{'name': 'owt'}" | base64 -w 0)
            curl --json $(jo code_b64=$CODE_B64 kwargs_b64=$KWARGS_B64) $EXEC_URL/hello
        
        Passing data in the request itself (here, the path info):
        
            CODE_B64=$(cat example/echo/echo.py | base64 -w 0)
            curl --json $(jo code_b64=$CODE_B64) $EXEC_URL/owt

3.  Text to Speech API

    A more complex example demonstrating wrapping Suno&rsquo;s OSS TTS model [<https://github.com/suno-ai/bark>](Bark).
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
                    for sentence in sentences:
                        logging.info("Generating sentence: %s", sentence)
                        wav_array = generate_audio(sentence, history_prompt=speaker)
                        buf = io.BytesIO()
                        write_wav(buf, SAMPLE_RATE, wav_array)
                        yield buf.read()
            
                return generate(), {"Content-Type": "audio/mpeg"}
    
    2.  Save audio via cURL
    
            # Usage:
            # ./bark.sh \
            #   "Hello world! This is a test." \
            #   filename_to_request.wav \
            #   /tmp/output_file.wav
            
            EXEC_URL="http://localhost:9876/unsafe/exec"
            
            CODE="$(< example/bark/bark.py)"
            KWARGS="{'text': '$1'}"
            FN_NAME="run"
            
            WAV_FILENAME="$2"
            OWT_URL="$EXEC_URL/$WAV_FILENAME"
            OUTFILE=$3
            
            JSON=$(jo \
              code_b64=$(echo "$CODE" | base64 -w 0) \
              kwargs_b64=$(echo "$KWARGS" | base64 -w 0) \
              use_cache="true" \
              cache_kwargs="true" \
            )
            
            CMD="curl --json $JSON $OWT_URL -o $OUTFILE"
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
        
        The `owt` arguments can be passed as GET query parameters as well as POST JSON data, so for this handler:
        
            def run(_):
                from flask import render_template
            
                with open("example/bark/bark.html") as f:
                    return render_template(f.read())
        
        We can construct a URL via:
        
            CODE_B64=$(cat example/bark/bark_serve_html.py | base64 -w 0)
            echo "http://localhost:9876/unsafe/exec/bark_app?code_b64=$CODE_B64"
        
            ./example/bark/bark_construct_url.sh

