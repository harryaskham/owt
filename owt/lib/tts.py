import nltk  # type: ignore

def over_sentences(prompt, inference_fn, batch_size=1):
    clean_prompt = prompt.replace("\n", " ").strip()
    all_prompts = nltk.sent_tokenize(clean_prompt)
    for batch in range(0, len(all_prompts), batch_size):
        prompts = all_prompts[batch:batch + batch_size]
        yield inference_fn(prompts)
