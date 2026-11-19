# llm_bot.py
# Same pipeline as baseline_bot.py, but an LLM writes the answer
from transformers import AutoTokenizer, AutoModelForCausalLM
from baseline_bot import load_movies, get_scores   # reuse your earlier code

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
            "Write a summary, analysis, comparison of critic vs audience views, "
            "and an overall rating out of 10. Cite sources like [1], [2]. "
            "If sources disagree or evidence is missing, say so."},
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
    import json
    movies = load_movies()
    while True:
        q = input("\nMovie title (or 'quit'): ")
        if q.lower() == "quit":
            break
        answer = llm_review(q, movies)
        print(answer)
        # Step 4: log feedback for DPO later
        rating = input("Good answer? (y/n): ")
        with open("feedback_llm.jsonl", "a") as f:
            f.write(json.dumps({"question": q, "answer": answer,
                                "rating": rating}) + "\n")