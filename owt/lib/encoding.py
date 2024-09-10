import io
import base64
import soundfile as sf  # type: ignore

def base64_buf(buf):
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def base64_wav(arr, sampling_rate):
    buf = io.BytesIO()
    sf.write(buf, arr, sampling_rate, format="WAV")
    return base64_buf(buf)
