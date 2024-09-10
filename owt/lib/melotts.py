from owt.lib import stream, encoding
import torch
from melo.api import TTS
import numpy as np
import io

def run(
    prompt: str = "",
    speed: float = 1.0,
    speaker: str = 'EN-US',
):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    def generate():
        speed = 1.0
        model = TTS(language='EN', device=device)
        speaker_ids = model.hps.data.spk2id
        buf = io.BytesIO()
        model.tts_to_file(prompt, speaker_ids[speaker], buf, speed=speed, format='wav')
        wav_b64 = encoding.base64_buf(buf)
        yield stream.event(chunk=wav_b64, cumulative=wav_b64)
        yield stream.done()
    return stream.response(generate)
