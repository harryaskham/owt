# tags: <laugh>, <chuckle>, <sigh>, <cough>, <sniffle>, <groan>, <yawn>, <gasp>.
from typing import Literal
from owt.lib import stream, encoding, tts
import os
import logging
import numpy as np
import gguf_orpheus
import time

def run(
    text: str = "",
    speaker: Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"] = "tara",
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_tokens: int = 1200,
    repetition_penalty: float = 1.1,
    sentence_template: str = "%s",
    split_type: Literal["sentence", "none"] = "sentence",
    batch_size: int = 1,
):
    full_wav_array: np.ndarray | None = None

    def generate(sentences):
        nonlocal full_wav_array
        raw_sentence = " ".join(sentences)
        sentence = sentence_template % raw_sentence
        logging.info(
            "Generating sentence: %s", sentence
        )
        chunk_stream = gguf_orpheus.tokens_decoder(
            gguf_orpheus.generate_speech_from_api(
                prompt=text,
                voice=speaker,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                repetition_penalty=repetition_penalty))
        for wav_array in chunk_stream:
            full_wav_array = (
                wav_array
                if full_wav_array is None
                else np.concatenate((full_wav_array, wav_array)))
            return stream.event(
                chunk=encoding.base64_wav(wav_array, gguf_orpheus.SAMPLE_RATE),
                cumulative=encoding.base64_wav(full_wav_array, gguf_orpheus.SAMPLE_RATE))

    def output():
        match split_type:
            case "sentence":
                yield from tts.over_sentences(text, generate, batch_size=batch_size)
            case "none":
                yield generate([text])
        yield stream.done()

    return stream.response(output)
