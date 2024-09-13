import torch
import io
from melo.api import TTS  # type: ignore
from owt.lib import stream, encoding, tts

def run(
    prompt: str = "",
    speed: float = 1.0,
    speaker: str = 'EN-US',
    split_type: str = 'sentence',
    batch_size: int = 1,
):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = TTS(language='EN', device=device)
    speaker_ids = model.hps.data.spk2id

    def generate(prompts):
        prompt = " ".join(prompts)
        buf = io.BytesIO()
        model.tts_to_file(prompt, speaker_ids[speaker], buf, speed=speed, format='wav')
        return stream.event(chunk=encoding.base64_buf(buf), cumulative="")

    def output():
        match split_type:
            case "sentence":
                yield from tts.over_sentences(prompt, generate, batch_size=batch_size)
            case "none":
                yield generate([prompt])
        yield stream.done()

    return stream.response(output)
