# lib/bark.py
from typing import Literal


def run(
    text: str | None = None,
    speaker: str = "v2/en_speaker_6",
    sentence_template: str = "%s",
    split_type: Literal["sentence", "none"] = "sentence",
    model_size: Literal["small", "large"] = "small",
):
    import os
    import logging
    import json
    import io
    import nltk
    import numpy as np
    import base64
    from scipy.io.wavfile import write as write_wav

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_OFFLOAD_CPU"] = "0"
    match model_size:
        case "small":
            os.environ["SUNO_USE_SMALL_MODELS"] = "1"
        case "large":
            os.environ["SUNO_USE_SMALL_MODELS"] = "0"

    from bark.generation import generate_text_semantic, preload_models, SAMPLE_RATE
    from bark.api import semantic_to_waveform

    preload_models()

    def base64_wav(arr):
        buf = io.BytesIO()
        write_wav(buf, SAMPLE_RATE, arr)
        wav = buf.getvalue()
        return base64.b64encode(wav).decode("utf-8")

    def generate():
        clean_text = text.replace("\n", " ").strip()
        match split_type:
            case "sentence":
                sentences = nltk.sent_tokenize(clean_text)
            case "none":
                sentences = [clean_text]
        full_wav_array = None
        for i, raw_sentence in enumerate(sentences):
            sentence = sentence_template % raw_sentence
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
        yield "data: [DONE]\n\n"

    return generate(), {"Content-Type": "text/event-stream"}
