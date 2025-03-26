# tags: <laugh>, <chuckle>, <sigh>, <cough>, <sniffle>, <groan>, <yawn>, <gasp>.
from typing import Literal
from owt.lib import stream, encoding, tts
import os
import logging
import numpy as np
from orpheus_tts import OrpheusModel
import time

def run(
    text: str = "",
    model = OrpheusModel(model_name ="canopylabs/orpheus-tts-0.1-finetune-prod")
    speaker: Literal["tara", "leah", "jess", "leo", "dan", "mia", "zac", "zoe"] = "tara".
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
        start_time = time.monotonic()
        syn_tokens = model.generate_speech(prompt=text, voice="tara", repetition_penalty=repetition_penalty)
        channels = 1
        sampwidth = 2
        framerate = 24000
        total_frames = 0
        chunk_counter = 0
        for wav_array in syn_tokens: # output streaming
          chunk_counter += 1
          frame_count = len(wav_array) // sampwidth * channels
          total_frames += frame_count
          full_wav_array = (
              wav_array
              if full_wav_array is None
              else np.concatenate((full_wav_array, wav_array))
          )
        duration = total_frames / framerate
        end_time = time.monotonic()
        print(f"It took {end_time - start_time} seconds to generate {duration:.2f} seconds of audio")
        return stream.event(
            chunk=encoding.base64_wav(wav_array, sample_rate),
            cumulative=encoding.base64_wav(full_wav_array, sample_rate))

    def output():
        match split_type:
            case "sentence":
                yield from tts.over_sentences(text, generate, batch_size=batch_size)
            case "none":
                yield generate([text])
        yield stream.done()

    return stream.response(output)
