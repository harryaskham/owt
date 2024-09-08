def run(
    prompt: str = "",
    description: str = "A female speaker delivers a slightly expressive and animated speech with a moderate speed and pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up.",
    model_name: str = "parler-tts/parler-tts-mini-v1",
):

    import json
    import io
    import base64
    import torch
    from parler_tts import ParlerTTSForConditionalGeneration, ParlerTTSStreamer
    from transformers import AutoTokenizer
    from threading import Thread
    import soundfile as sf
    import numpy as np

    device = "cuda:0" if torch.cuda.is_available() else "cpu"

    model = ParlerTTSForConditionalGeneration.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    sampling_rate = model.audio_encoder.config.sampling_rate
    frame_rate = model.audio_encoder.config.frame_rate

    def base64_wav(arr):
        buf = io.BytesIO()
        sf.write(buf, arr, sampling_rate, format="WAV")
        wav = buf.getvalue()
        return base64.b64encode(wav).decode("utf-8")

    def generate(text, description, play_steps_in_s=0.5):
        play_steps = int(frame_rate * play_steps_in_s)
        streamer = ParlerTTSStreamer(model, device=device, play_steps=play_steps)

        inputs = tokenizer(description, return_tensors="pt").to(device)
        prompt = tokenizer(text, return_tensors="pt").to(device)

        generation_kwargs = dict(
            input_ids=inputs.input_ids,
            prompt_input_ids=prompt.input_ids,
            attention_mask=inputs.attention_mask,
            prompt_attention_mask=prompt.attention_mask,
            streamer=streamer,
            do_sample=True,
            temperature=1.0,
            min_new_tokens=10,
        )

        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        cumulative_audio = None
        for new_audio in streamer:
            if new_audio.shape[0] == 0:
                break
            print(f"Sample of length: {round(new_audio.shape[0] / sampling_rate, 4)} seconds")

            if cumulative_audio is None:
                cumulative_audio = new_audio
            else:
                cumulative_audio = np.concatenate((cumulative_audio, new_audio))

            yield "data: %s\n\n" % (
                json.dumps(
                    {
                        "chunk": base64_wav(new_audio),
                        "cumulative": base64_wav(cumulative_audio),
                    }
                )
            )

    return generate(prompt, description, play_steps_in_s=5), {"Content-Type": "text/event-stream"}
