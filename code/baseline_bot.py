# baseline_bot.py
# A simple rule-based review bot (no language model yet).
# This is your BASELINE that DPO-tuned models get compared against later.
import json

def load_movies():
    with open("movies.json") as f:
        return json.load(f)

def to_percent(rating):
    # Convert "8.8/10", "87%", or "74/100" into a 0-100 number
    if "%" in rating:
        return float(rating.replace("%", ""))
    top, bottom = rating.split("/")
    return float(top) / float(bottom) * 100

def get_scores(movie):
    # Collect each source's rating on the same 0-100 scale
    scores = {}
    for r in movie["omdb"].get("Ratings", []):
        scores[r["Source"]] = to_percent(r["Value"])
    return scores

def make_review(question, movies):
    # Find a movie whose title appears in what the user typed
    match = None
    for m in movies:
        if m["title"].lower() in question.lower():
            match = m
    if match is None:
        # Abstain instead of guessing (a goal from your abstract)
        return "I couldn't find that movie in my data, so I won't guess."

    lines = [f"{match['title']} ({match['year']})"]

    # Summary: first two sentences of the Wikipedia intro
    summary = ". ".join(match["wikipedia"]["text"].split(". ")[:2])
    lines.append("Summary: " + summary)

    # Overall rating: average of all available sources
    scores = get_scores(match)
    if scores:
        overall = sum(scores.values()) / len(scores) / 10
        lines.append(f"Overall rating: {overall:.1f}/10")
        # Flag disagreement between sources (gap over 20 points)
        if max(scores.values()) - min(scores.values()) > 20:
            lines.append("Note: sources disagree: " +
                         ", ".join(f"{k}: {v:.0f}/100" for k, v in scores.items()))

    # Audience viewpoint: first two review snippets
    for r in match["tmdb"]["reviews"][:2]:
        lines.append("Audience review: " + r["text"][:200] + "...")

    # Citations (a goal from your abstract)
    lines.append("Sources: " + match["imdb_url"] + " | " +
                 match["wikipedia"]["url"] + " | " + match["tmdb"]["url"])
    return "\n".join(lines)

# This block only runs when you start this file directly
if __name__ == "__main__":
    movies = load_movies()
    while True:
        q = input("\nMovie title (or 'quit'): ")
        if q.lower() == "quit":
            break
        answer = make_review(q, movies)
        print(answer)
        # Save thumbs up/down: this becomes DPO training data later
        rating = input("Good answer? (y/n): ")
        with open("feedback.jsonl", "a") as f:
            f.write(json.dumps({"question": q, "answer": answer,
                                "rating": rating}) + "\n")