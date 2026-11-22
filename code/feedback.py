import json


FEEDBACK_SECTIONS = (
    (
        "general_review",
        "General review",
        "Give a concise movie summary and an overall rating out of 10.",
    ),
    (
        "critic_response",
        "Critic response",
        "Summarize critic ratings such as Rotten Tomatoes or Metacritic when "
        "available. Do not describe ratings as written reviews.",
    ),
    (
        "audience_review",
        "Audience review",
        "Summarize the provided TMDB audience reviews. Say when none are available.",
    ),
    (
        "comparison_of_reviews",
        "Comparison of reviews",
        "Compare the available critic and audience evidence and note "
        "disagreements or missing evidence.",
    ),
)


def collect_section_preferences(candidate_a, candidate_b, input_fn=None,
                                output_fn=print):
    if input_fn is None:
        input_fn = input

    preferences = {}
    for section in FEEDBACK_SECTIONS:
        key, label = section[0], section[1]
        output_fn(f"\n{label}")
        output_fn(f"A: {candidate_a[key]}")
        output_fn(f"B: {candidate_b[key]}")
        while True:
            choice = input_fn(
                f"Which {label.lower()} is better? (a/b/skip): "
            ).strip().lower()
            if choice in ("a", "b", "skip"):
                preferences[key] = choice
                break
            output_fn("Please enter a, b, or skip.")
    return preferences


def assemble_response(candidate_a, candidate_b, preferences):
    sections = []
    for section in FEEDBACK_SECTIONS:
        key, label = section[0], section[1]
        candidate = candidate_b if preferences[key] == "b" else candidate_a
        sections.append(f"{label}:\n{candidate[key]}")
    return "\n\n".join(sections)


def save_comparison(path, question, movie_title, evidence, prompts,
                    candidate_a, candidate_b, preferences, model_name):
    record = {
        "question": question,
        "movie_title": movie_title,
        "evidence": evidence,
        "prompts": prompts,
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "preferences": preferences,
        "model": model_name,
        "candidate_generation": {
            "a": "greedy",
            "b": "sampled, temperature=0.8, top_p=0.95",
        },
    }
    with open(path, "a", encoding="utf-8") as comparison_file:
        comparison_file.write(json.dumps(record, ensure_ascii=False) + "\n")
