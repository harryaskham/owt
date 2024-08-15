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
    silence = np.zeros(int(0.25 * SAMPLE_RATE))  # quarter second of silence

    def generate():
        # pieces = []
        for sentence in sentences:
            logging.info("Generating sentence: %s", sentence)
            audio_array = generate_audio(sentence, history_prompt=SPEAKER)
            # pieces += [audio_array]  # , silence.copy()]
            wav_buffer = io.BytesIO()
            write_wav(wav_buffer, SAMPLE_RATE, audio_array)
            buf = wav_buffer
            yield buf.read()
            # data = buf.read(1024)
            # while data:
            #     yield data
            #     data = buf.read(1024)
        # audio_array = np.concatenate(pieces)
        # write_wav(wav_buffer, SAMPLE_RATE, audio_array)
        # wav_buffer.seek(0)
        # return wav_buffer

    return generate(), {"Content-Type": "audio/mpeg"}
    # return send_file(generate(), mimetype="audio/mpeg")
