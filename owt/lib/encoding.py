import io
import base64
import soundfile as sf  # type: ignore
import nltk  # type: ignore

def base64_buf(buf):
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def base64_wav(arr, sampling_rate):
    buf = io.BytesIO()
    sf.write(buf, arr, sampling_rate, format="WAV")
    return base64_buf(buf)

def over_sentences(prompt, inference_fn, batch_size=1):
    clean_prompt = prompt.replace("\n", " ").strip()
    all_prompts = nltk.sent_tokenize(clean_prompt)
    for batch in range(0, len(all_prompts), batch_size):
        prompts = all_prompts[batch:batch + batch_size]
        yield inference_fn(prompts)
