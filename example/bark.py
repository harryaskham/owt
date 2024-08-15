def run(text: str):
    import os
    import logging
    import io
    from pydub import AudioSegment
    import nltk  # we'll use this to split into sentences
    import numpy as np
    from scipy.io.wavfile import write as write_wav
    from flask import send_file

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_USE_SMALL_MODELS"] = "0"
    os.environ["SUNO_OFFLOAD_CPU"] = "0"

    from bark.generation import (
        generate_text_semantic,
        preload_models,
    )
    from bark import generate_audio, SAMPLE_RATE

    preload_models()

    script = text.replace("\n", " ").strip()

    sentences = nltk.sent_tokenize(script)

    SPEAKER = "v2/en_speaker_6"

    def generate():
        for sentence in sentences:
            logging.info("Generating sentence: %s", sentence)
            audio_array = generate_audio(sentence, history_prompt=SPEAKER)
            wav_buffer = io.BytesIO()
            write_wav(wav_buffer, SAMPLE_RATE, audio_array)
            yield wav_buffer.read()

    return generate(), {"Content-Type": "audio/mpeg"}
