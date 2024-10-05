import torch
import io
from owt.lib import stream, encoding, tts
from TTS.api import TTS

def run(
    prompt: str = "",
    speaker_wav: str = '/tmp/attenborough.wav',
    language: str = 'en',
    split_type: str = 'sentence',
    batch_size: int = 1,
    internal_split_sentences: bool = False,
):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

    def generate(prompts):
        prompt = " ".join(prompts)
        class BufWrap:
            """Shaped such that XTTS can write to it."""
            def __init__(self):
                self.buffer = io.BytesIO()
        buf = BufWrap()
        model.tts_to_file(
            text=prompt,
            split_sentences=internal_split_sentences,
            language=language,
            speaker_wav=speaker_wav,
            pipe_out=buf,
            file_path="/tmp/xtts_output.wav")
        return stream.event(chunk=encoding.base64_buf(buf.buffer), cumulative="")

    def output():
        match split_type:
            case "sentence":
                yield from tts.over_sentences(prompt, generate, batch_size=batch_size)
            case "none":
                yield generate([prompt])
        yield stream.done()

    return stream.response(output)
