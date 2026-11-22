import json
import os
import tempfile
import unittest

from feedback import collect_section_feedback, save_feedback


class FeedbackTests(unittest.TestCase):
    def test_collects_one_rating_for_each_section(self):
        answers = iter(["y", "n", " y ", "N"])

        feedback = collect_section_feedback(lambda _prompt: next(answers))

        self.assertEqual(
            feedback,
            {
                "general_review": "y",
                "critic_response": "n",
                "audience_review": "y",
                "comparison_of_reviews": "n",
            },
        )

    def test_reprompts_on_invalid_rating(self):
        answers = iter(["maybe", "Y", "y", "n", "y", "n"])
        prompts = []

        def input_fn(prompt):
            prompts.append(prompt)
            return next(answers)

        feedback = collect_section_feedback(input_fn)

        self.assertEqual(feedback["general_review"], "y")
        self.assertEqual(len(prompts), 5)

    def test_saves_section_feedback_as_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "feedback.jsonl")
            section_feedback = {
                "general_review": "y",
                "critic_response": "n",
                "audience_review": "y",
                "comparison_of_reviews": "n",
            }

            save_feedback(path, "Inception", "A sample answer", section_feedback)

            with open(path, encoding="utf-8") as feedback_file:
                record = json.loads(feedback_file.readline())

        self.assertEqual(record["question"], "Inception")
        self.assertEqual(record["answer"], "A sample answer")
        self.assertEqual(record["section_feedback"], section_feedback)


if __name__ == "__main__":
    unittest.main()
