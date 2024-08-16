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
