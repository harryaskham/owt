from owt.lib import stream, encoding
from typing import Literal
import torch
from parler_tts import ParlerTTSForConditionalGeneration, ParlerTTSStreamer
from transformers import AutoTokenizer, AutoFeatureExtractor, set_seed
from threading import Thread
import numpy as np
import nltk  # type: ignore

def run(
    prompt: str = "",
    description: str = "A female speaker delivers a slightly expressive and animated speech with a moderate speed and pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up.",
    model_name: str = "parler-tts/parler-tts-mini-v1",
    attention: Literal["eager", "sdpa", "flash_attention_2"] = "flash_attention_2",
    chunk_secs: int = 5,
    temperature: float = 1.0,
    min_new_tokens: int = 10,
    do_sample: bool = True,
    split_type: Literal["sentence", "none"] = "none",
    batch_size: int = 2,
):
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    match split_type:
        case "sentence":
            model = ParlerTTSForConditionalGeneration.from_pretrained(
                model_name,
                attn_implementation=attention).to(device)

            def generate(prompt, description):
                clean_prompt = prompt.replace("\n", " ").strip()
                all_prompts = nltk.sent_tokenize(clean_prompt)
                all_descriptions = [description] * len(all_prompts)
                cumulative_audio: np.ndarray = np.array([])
                for batch in range(0, len(all_prompts), batch_size):
                    prompts = all_prompts[batch:batch + batch_size]
                    descriptions = all_descriptions[batch:batch + batch_size]

                    inputs_batch = tokenizer(descriptions, return_tensors="pt", padding=True).to("cuda")
                    prompt_batch = tokenizer(prompts, return_tensors="pt", padding=True).to("cuda")
                    sampling_rate = AutoFeatureExtractor.from_pretrained(model_name).sampling_rate

                    set_seed(0)
                    generation = model.generate(
                        input_ids=inputs_batch.input_ids,
                        attention_mask=inputs_batch.attention_mask,
                        prompt_input_ids=prompt_batch.input_ids,
                        prompt_attention_mask=prompt_batch.attention_mask,
                        do_sample=do_sample,
                        temperature=temperature,
                        return_dict_in_generate=True,
                    )

                    for i in range(len(prompts)):
                        new_audio = generation.sequences[i, :generation.audios_length[i]].cpu().numpy().squeeze()
                        cumulative_audio = np.concatenate((cumulative_audio, new_audio))
                        yield stream.event(
                            chunk=encoding.base64_wav(new_audio, sampling_rate),
                            cumulative=encoding.base64_wav(cumulative_audio, sampling_rate))

                yield stream.done()

            return stream.response(generate, prompt, description)

        case "none":
            model = ParlerTTSForConditionalGeneration.from_pretrained(
                model_name,
                attn_implementation="sdpa").to(device, dtype=torch.bfloat16)
            frame_rate = model.audio_encoder.config.frame_rate

            def generate(text, description, play_steps_in_s):
                inputs_batch = tokenizer(description, return_tensors="pt").to(device)
                prompt_batch = tokenizer(text, return_tensors="pt").to(device)
                sampling_rate = model.audio_encoder.config.sampling_rate
                play_steps = int(frame_rate * play_steps_in_s)
                streamer = ParlerTTSStreamer(model, device=device, play_steps=play_steps)
                generation_kwargs = dict(
                    input_ids=inputs_batch.input_ids,
                    prompt_input_ids=prompt_batch.input_ids,
                    attention_mask=inputs_batch.attention_mask,
                    prompt_attention_mask=prompt_batch.attention_mask,
                    streamer=streamer,
                    do_sample=do_sample,
                    temperature=temperature,
                    min_new_tokens=min_new_tokens,
                )
                Thread(target=model.generate, kwargs=generation_kwargs).start()
                cumulative_audio: np.ndarray = np.array([])
                for new_audio in streamer:
                    if new_audio.shape[0] == 0:
                        break
                    print(f"Sample of length: {round(new_audio.shape[0] / sampling_rate, 4)} seconds")
                    cumulative_audio = np.concatenate((cumulative_audio, new_audio))
                    yield stream.event(
                        chunk=encoding.base64_wav(new_audio, sampling_rate),
                        cumulative=encoding.base64_wav(cumulative_audio, sampling_rate))
                yield stream.done()

            return stream.response(generate, prompt, description, play_steps_in_s=chunk_secs)
