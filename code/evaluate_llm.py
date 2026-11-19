# evaluate_llm.py
# Runs baseline and LLM on the same questions and compares them
import json
from baseline_bot import load_movies, make_review
from llm_bot import llm_review

movies = load_movies()
known = [m["title"] for m in movies]                           # should be answered
unknown = ["Zzyzx Road Returns 9", "asdfgh", "weather today"]  # should abstain

def abstained(a):
    return "couldn't find" in a

def cited(a):
    # baseline cites with links, LLM cites with [1], [2], [3]
    return "http" in a or any(tag in a for tag in ["[1]", "[2]", "[3]"])

def run(bot):
    known_answers = [bot(t, movies) for t in known]
    unknown_answers = [bot(t, movies) for t in unknown]
    answer_rate = sum(not abstained(a) for a in known_answers) / len(known)
    cite_rate = sum(cited(a) for a in known_answers) / len(known)
    abstain_rate = sum(abstained(a) for a in unknown_answers) / len(unknown)
    return answer_rate, cite_rate, abstain_rate, known_answers

results = {}
for name, bot in [("Baseline", make_review), ("Qwen", llm_review)]:
    a, c, ab, answers = run(bot)
    results[name] = answers
    print(f"{name}: answer {a:.0%} | cited {c:.0%} | abstain {ab:.0%}")

# Save all answers so you can read them and judge quality by hand
with open("answers.json", "w") as f:
    json.dump({"movies": known, **results}, f, indent=2)