def run(
    prompt: str = "",
    description: str = "A female speaker delivers a slightly expressive and animated speech with a moderate speed and pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up.",
    model_name: str = "parler-tts/parler-tts-mini-v1",
):

    import json
    import io
    import base64
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer
    import soundfile as sf

    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    model = ParlerTTSForConditionalGeneration.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    sampling_rate = model.audio_encoder.config.sampling_rate

    input_ids = tokenizer(description, return_tensors="pt").input_ids.to(device)
    prompt_input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)

    generation = model.generate(input_ids=input_ids, prompt_input_ids=prompt_input_ids)
    audio_arr = generation.cpu().numpy().squeeze()

    def base64_wav(arr):
        buf = io.BytesIO()
        sf.write(buf, arr, sampling_rate, format="WAV")
        wav = buf.getvalue()
        return base64.b64encode(wav).decode("utf-8")

    def stream():
        yield "data: %s\n\n" % (
            json.dumps(
                {
                    "chunk": base64_wav(audio_arr),
                    "cumulative": base64_wav(audio_arr),
                }
            )
        )
        yield "data: [DONE]\n\n"

    return stream(), {"Content-Type": "text/event-stream"}
