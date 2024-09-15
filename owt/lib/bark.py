# lib/bark.py
from typing import Literal
from owt.lib import stream, encoding, tts
import os
import logging
import numpy as np

def run(
    text: str = "",
    speaker: str = "v2/en_speaker_6",
    sentence_template: str = "%s",
    split_type: Literal["sentence", "none"] = "sentence",
    model_size: Literal["small", "large"] = "small",
    batch_size: int = 1,
    temperature: float = 0.6
):
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    os.environ["SUNO_OFFLOAD_CPU"] = "0"
    match model_size:
        case "small":
            os.environ["SUNO_USE_SMALL_MODELS"] = "1"
        case "large":
            os.environ["SUNO_USE_SMALL_MODELS"] = "0"

    from bark.generation import generate_text_semantic, preload_models, SAMPLE_RATE  # type: ignore
    from bark.api import semantic_to_waveform  # type: ignore

    preload_models()

    def output():
        match split_type:
            case "sentence":
                yield from tts.over_sentences(text, batch, batch_size=batch_size)
            case "none":
                yield batch([text])
        yield stream.done()

    full_wav_array: np.ndarray | None = None

    def batch(sentences):
        nonlocal full_wav_array
        raw_sentence = " ".join(sentences)
        sentence = sentence_template % raw_sentence
        logging.info(
            "Generating sentence: %s", sentence
        )
        semantic_tokens: np.ndarray = generate_text_semantic(
            sentence,
            history_prompt=speaker,
            temp=temperature,
            min_eos_p=0.05,
        )
        wav_array: np.ndarray = semantic_to_waveform(
            semantic_tokens, history_prompt=speaker
        )
        full_wav_array = (
            wav_array
            if full_wav_array is None
            else np.concatenate((full_wav_array, wav_array))
        )

        return stream.event(
            chunk=encoding.base64_wav(wav_array, SAMPLE_RATE),
            cumulative=encoding.base64_wav(full_wav_array, SAMPLE_RATE))

    return stream.response(output)
