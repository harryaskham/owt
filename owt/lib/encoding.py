import io
import base64
import soundfile as sf  # type: ignore

def base64_wav(arr, sampling_rate):
    buf = io.BytesIO()
    sf.write(buf, arr, sampling_rate, format="WAV")
    wav = buf.getvalue()
    return base64.b64encode(wav).decode("utf-8")
