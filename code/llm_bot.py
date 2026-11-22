# llm_bot.py
# Same pipeline as baseline_bot.py, but an LLM writes the answer
import importlib

try:
    _transformers = importlib.import_module("transformers")
except ModuleNotFoundError as exc:
    if exc.name != "transformers":
        raise
    raise RuntimeError(
        "The 'transformers' package is required. Install it with: "
        "python -m pip install transformers"
    ) from exc

AutoTokenizer = _transformers.AutoTokenizer
AutoModelForCausalLM = _transformers.AutoModelForCausalLM
from baseline_bot import load_movies, get_scores   # reuse your earlier code
from feedback import collect_section_feedback, save_feedback

# Download and load the model (first run downloads a few GB)
model_name = "Qwen/Qwen2.5-1.5B-Instruct"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def find_movie(question, movies):
    # Step 1 (Retrieve): match a movie title in the user's text
    for m in movies:
        if m["title"].lower() in question.lower():
            return m
    return None

def build_evidence(m):
    # Step 2: turn the stored data into numbered, citable text
    scores = get_scores(m)
    ratings = ", ".join(f"{k}: {v:.0f}/100" for k, v in scores.items())
    reviews = " | ".join(r["text"][:300] for r in m["tmdb"]["reviews"][:3])
    return (f"Movie: {m['title']} ({m['year']})\n"
            f"[1] Ratings via OMDb ({m['imdb_url']}): {ratings}\n"
            f"[2] Wikipedia ({m['wikipedia']['url']}): {m['wikipedia']['text'][:1000]}\n"
            f"[3] TMDB audience reviews ({m['tmdb']['url']}): {reviews}")

def llm_review(question, movies):
    movie = find_movie(question, movies)
    if movie is None:
        return "I couldn't find that movie in my data."

    # The system message tells the model how to behave
    messages = [
        {"role": "system", "content":
            "You are a movie review assistant. Use ONLY the evidence given. "
            "Write exactly these four sections, using the headings shown: "
            "'General Review', 'Critic Response', 'Audience Review', and "
            "'Comparison of Reviews'. In General Review, give a concise "
            "summary and overall rating out of 10. In Critic Response, "
            "summarize critic ratings such as Rotten Tomatoes or Metacritic "
            "when available; do not describe them as written reviews. In "
            "Audience Review, summarize the provided TMDB audience reviews. "
            "In Comparison of Reviews, compare the available critic and "
            "audience evidence. Cite sources like [1], [2], [3]. If evidence "
            "for a section is missing or sources disagree, say so."},
        {"role": "user", "content":
            f"Evidence:\n{build_evidence(movie)}\n\nQuestion: {question}"},
    ]

    # Step 3 (Generate): format the chat, run the model, decode the reply
    prompt = tokenizer.apply_chat_template(messages, tokenize=False,
                                           add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(**inputs, max_new_tokens=300, do_sample=False)
    # Keep only the newly generated tokens, not the prompt we sent in
    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)

if __name__ == "__main__":
    movies = load_movies()
    while True:
        q = input("\nMovie title (or 'quit'): ")
        if q.lower() == "quit":
            break
        answer = llm_review(q, movies)
        print(answer)
        # Step 4: collect section-level feedback for later review
        section_feedback = collect_section_feedback()
        save_feedback("feedback_llm.jsonl", q, answer, section_feedback)