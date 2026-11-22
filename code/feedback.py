import json


FEEDBACK_SECTIONS = (
    ("general_review", "General review"),
    ("critic_response", "Critic response"),
    ("audience_review", "Audience review"),
    ("comparison_of_reviews", "Comparison of reviews"),
)


def collect_section_feedback(input_fn=None):
    if input_fn is None:
        input_fn = input

    feedback = {}
    for key, label in FEEDBACK_SECTIONS:
        while True:
            answer = input_fn(f"Was the {label} helpful and accurate? (y/n): ")
            answer = answer.strip().lower()
            if answer in ("y", "n"):
                feedback[key] = answer
                break
            print("Please enter y or n.")
    return feedback


def save_feedback(path, question, answer, section_feedback):
    record = {
        "question": question,
        "answer": answer,
        "section_feedback": section_feedback,
    }
    with open(path, "a", encoding="utf-8") as feedback_file:
        feedback_file.write(json.dumps(record, ensure_ascii=False) + "\n")
