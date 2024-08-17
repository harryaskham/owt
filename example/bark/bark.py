# example/bark/bark.py


def run(request, text: str, speaker: str = "v2/en_speaker_6"):
    import os
    import logging
    import json
    import io
    import nltk
    import numpy as np
    import functools
    import base64
    from scipy.io.wavfile import write as write_wav
    import multiprocessing

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_USE_SMALL_MODELS"] = "0"
    os.environ["SUNO_OFFLOAD_CPU"] = "0"

    from bark.generation import generate_text_semantic, preload_models
    from bark.api import semantic_to_waveform
    from bark import generate_audio, SAMPLE_RATE

    preload_models()

    def base64_wav(arr):
        buf = io.BytesIO()
        write_wav(buf, SAMPLE_RATE, arr)
        wav = buf.getvalue()
        return base64.b64encode(wav).decode("utf-8")

    def generate():

        def generate_map(i, sentence, speaker, outputs):
            logging.info("Generating sentence %d: %s", i + 1, sentence)
            semantic_tokens = generate_text_semantic(
                sentence,
                history_prompt=speaker,
                temp=0.6,
                min_eos_p=0.05,
            )
            outputs[i] = semantic_to_waveform(semantic_tokens, history_prompt=speaker)
            return i, outputs[i]

        sentences = nltk.sent_tokenize(text.replace("\n", " ").strip())
        full_wav_array = None
        pool = multiprocessing.Pool()
        outputs = [None] * len(sentences)
        args = [(i, sentence, speaker, outputs) for i, sentence in enumerate(sentences)]
        next_i = 0
        for i, sentence in pool.starmap(generate_map, args):
            outputs[i] = sentence
            while outputs[next_i]:
                wav_array = outputs[next_i]
                full_wav_array = np.concatenate(
                    [output for output in outputs if output]
                )
                yield "data: %s\n\n" % (
                    json.dumps(
                        {
                            "sentence": base64_wav(wav_array),
                            "cumulative": base64_wav(full_wav_array),
                        }
                    )
                )
                next_i += 1
        yield "data: DONE\n\n"

    return generate(), {"Content-Type": "text/event-stream"}
