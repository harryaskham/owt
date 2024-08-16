# example/bark/bark.py


def run(request, text: str, speaker: str = "v2/en_speaker_6"):
    import os
    import logging
    import json
    import io
    import nltk
    import numpy as np
    import base64
    from scipy.io.wavfile import write as write_wav

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_USE_SMALL_MODELS"] = "1"
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
        sentences = nltk.sent_tokenize(text.replace("\n", " ").strip())
        full_wav_array = None
        for i, sentence in enumerate(sentences):
            logging.info(
                "Generating sentence %d/%d: %s", i + 1, len(sentences), sentence
            )
            semantic_tokens = generate_text_semantic(
                sentence,
                history_prompt=speaker,
                temp=0.6,
                min_eos_p=0.05,
            )
            wav_array = semantic_to_waveform(semantic_tokens, history_prompt=speaker)
            # wav_array = generate_audio(sentence, history_prompt=speaker)
            full_wav_array = (
                wav_array
                if full_wav_array is None
                else np.concatenate((full_wav_array, wav_array))
            )

            yield "data: %s\n\n" % (
                json.dumps(
                    {
                        "sentence": base64_wav(wav_array),
                        "cumulative": base64_wav(full_wav_array),
                    }
                )
            )
        yield "data: DONE\n\n"

    return generate(), {"Content-Type": "text/event-stream"}
