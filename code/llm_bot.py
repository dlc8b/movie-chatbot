# Same pipeline as baseline_bot.py, but an LLM writes the answer
import importlib
import os
from pathlib import Path

try:
    _transformers = importlib.import_module("transformers")
except ModuleNotFoundError as exc:
    if exc.name != "transformers":
        raise
    raise RuntimeError(
        "The 'transformers' package is required. Install it with: "
        "python -m pip install transformers"
    ) from exc

_torch = importlib.import_module("torch")
AutoTokenizer = _transformers.AutoTokenizer
AutoModelForCausalLM = _transformers.AutoModelForCausalLM

from baseline_bot import load_movies, get_scores
from feedback import (
    FEEDBACK_SECTIONS,
    assemble_response,
    collect_section_preferences,
    save_comparison,
)


MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"
COMPARISONS_FILE = Path(__file__).with_name("comparisons.jsonl")
DEFAULT_ADAPTER_DIR = Path(__file__).with_name("movie_dpo_adapter")

adapter_override = os.environ.get("MOVIE_DPO_ADAPTER")
adapter_dir = Path(adapter_override) if adapter_override else DEFAULT_ADAPTER_DIR
if adapter_override and not adapter_dir.exists():
    raise FileNotFoundError(f"DPO adapter directory does not exist: {adapter_dir}")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
if _torch.cuda.is_available():
    model.to("cuda")

active_model_name = MODEL_NAME
if adapter_dir.exists():
    try:
        _peft = importlib.import_module("peft")
    except ModuleNotFoundError as exc:
        if exc.name != "peft":
            raise
        raise RuntimeError(
            "A trained DPO adapter was found, but PEFT is not installed. "
            "Install the DPO dependencies from requirements-dpo.txt."
        ) from exc
    model = _peft.PeftModel.from_pretrained(model, str(adapter_dir))
    active_model_name = f"{MODEL_NAME} with adapter {adapter_dir}"

model.eval()


def find_movie(question, movies):
    for movie in movies:
        if movie["title"].lower() in question.lower():
            return movie
    return None


def build_evidence(movie):
    scores = get_scores(movie)
    ratings = ", ".join(f"{source}: {score:.0f}/100"
                        for source, score in scores.items())
    reviews = " | ".join(
        review["text"][:300] for review in movie["tmdb"]["reviews"][:3]
    )
    return (
        f"Movie: {movie['title']} ({movie['year']})\n"
        f"[1] Ratings via OMDb ({movie['imdb_url']}): {ratings}\n"
        f"[2] Wikipedia ({movie['wikipedia']['url']}): "
        f"{movie['wikipedia']['text'][:1000]}\n"
        f"[3] TMDB audience reviews ({movie['tmdb']['url']}): {reviews}"
    )


def build_section_prompt(question, evidence, label, instruction):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a movie review assistant. Use only the evidence "
                "provided. Do not invent facts or opinions. Cite evidence "
                "with its bracketed source number. Return only the requested "
                "section's content, without a heading."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Evidence:\n{evidence}\n\n"
                f"Question: {question}\n\n"
                f"Write the {label} section: {instruction}"
            ),
        },
    ]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def generate_completion(prompt, sample):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    generation_options = {
        "max_new_tokens": 180,
        "do_sample": sample,
    }
    if sample:
        generation_options.update({"temperature": 0.8, "top_p": 0.95})

    with _torch.inference_mode():
        output = model.generate(**inputs, **generation_options)
    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def build_prompts(question, evidence):
    prompts = {}
    for key, label, instruction in FEEDBACK_SECTIONS:
        prompts[key] = build_section_prompt(
            question, evidence, label, instruction
        )
    return prompts


def generate_candidates(question, movie):
    evidence = build_evidence(movie)
    prompts = build_prompts(question, evidence)
    candidate_a = {}
    candidate_b = {}
    for section in FEEDBACK_SECTIONS:
        key = section[0]
        candidate_a[key] = generate_completion(prompts[key], sample=False)
        candidate_b[key] = generate_completion(prompts[key], sample=True)
    return evidence, prompts, candidate_a, candidate_b


def llm_review(question, movies):
    movie = find_movie(question, movies)
    if movie is None:
        return "I couldn't find that movie in my data."

    evidence = build_evidence(movie)
    prompts = build_prompts(question, evidence)
    candidate_a = {
        key: generate_completion(prompt, sample=False)
        for key, prompt in prompts.items()
    }
    preferences = {key: "a" for key in prompts}
    return assemble_response(candidate_a, candidate_a, preferences)


if __name__ == "__main__":
    movies = load_movies()
    while True:
        question = input("\nMovie title (or 'quit'): ")
        if question.lower() == "quit":
            break

        movie = find_movie(question, movies)
        if movie is None:
            print("I couldn't find that movie in my data.")
            continue

        evidence, prompts, candidate_a, candidate_b = generate_candidates(
            question, movie
        )
        preferences = collect_section_preferences(candidate_a, candidate_b)
        answer = assemble_response(candidate_a, candidate_b, preferences)
        print("\nSelected response:\n")
        print(answer)
        save_comparison(
            COMPARISONS_FILE,
            question,
            f"{movie['title']} ({movie['year']})",
            evidence,
            prompts,
            candidate_a,
            candidate_b,
            preferences,
            active_model_name,
        )
