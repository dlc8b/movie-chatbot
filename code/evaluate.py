# evaluate.py
# Measures the baseline so you have "Initial Results" for the report
from baseline_bot import load_movies, make_review

movies = load_movies()
known = [m["title"] for m in movies]                  # bot SHOULD answer these
unknown = ["Zzyzx Road Returns 9", "asdfgh", "weather today"]  # bot SHOULD abstain

def abstained(answer):
    return "couldn't find" in answer

# Run the bot on every test question
known_answers = [make_review(t, movies) for t in known]
unknown_answers = [make_review(t, movies) for t in unknown]

# Metric 1: share of real movies the bot answered
answer_rate = sum(not abstained(a) for a in known_answers) / len(known)
# Metric 2: share of answers that include a source link
citation_rate = sum("http" in a for a in known_answers) / len(known)
# Metric 3: share of unanswerable questions where the bot abstained
abstain_rate = sum(abstained(a) for a in unknown_answers) / len(unknown)

print(f"Answer rate:   {answer_rate:.0%}")
print(f"Citation rate: {citation_rate:.0%}")
print(f"Abstain rate:  {abstain_rate:.0%}")