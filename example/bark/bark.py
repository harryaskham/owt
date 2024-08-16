# example/bark/bark.py


def run(request, text: str, speaker: str = "v2/en_speaker_6"):
    import os
    import logging
    import io
    import nltk
    import numpy as np
    from scipy.io.wavfile import write as write_wav

    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_USE_SMALL_MODELS"] = "0"
    os.environ["SUNO_OFFLOAD_CPU"] = "0"

    from bark.generation import generate_text_semantic, preload_models
    from bark import generate_audio, SAMPLE_RATE

    preload_models()

    def generate():
        sentences = nltk.sent_tokenize(text.replace("\n", " ").strip())
        full_wav_array = None
        for i, sentence in enumerate(sentences):
            logging.info(
                "Generating sentence %d/%d: %s", i + 1, len(sentences), sentence
            )
            wav_array = generate_audio(sentence, history_prompt=speaker)
            full_wav_array = (
                wav_array
                if full_wav_array is None
                else np.concatenate((full_wav_array, wav_array))
            )
            if i == len(sentences) - 1:
                buf = io.BytesIO()
                write_wav(buf, SAMPLE_RATE, full_wav_array)
                yield buf.read()

    return generate(), {"Content-Type": "audio/mpeg"}
