import json
import os
import tempfile
import unittest
from unittest.mock import Mock

from feedback import (
    FEEDBACK_SECTIONS,
    assemble_response,
    collect_section_preferences,
    save_comparison,
)


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.candidate_a = {
            section[0]: f"A {section[0]}" for section in FEEDBACK_SECTIONS
        }
        self.candidate_b = {
            section[0]: f"B {section[0]}" for section in FEEDBACK_SECTIONS
        }

    def test_collects_a_b_or_skip_for_each_section(self):
        answers = iter(["a", "B", "skip", " b "])

        input_fn = Mock(side_effect=answers)
        preferences = collect_section_preferences(
            self.candidate_a,
            self.candidate_b,
            input_fn=input_fn,
            output_fn=Mock(),
        )

        self.assertEqual(
            preferences,
            {
                "general_review": "a",
                "critic_response": "b",
                "audience_review": "skip",
                "comparison_of_reviews": "b",
            },
        )

    def test_reprompts_on_invalid_preference(self):
        answers = iter(["maybe", "A", "b", "a", "skip", "a"])
        input_fn = Mock(side_effect=answers)

        preferences = collect_section_preferences(
            self.candidate_a, self.candidate_b, input_fn, Mock()
        )

        self.assertEqual(preferences["general_review"], "a")
        self.assertEqual(input_fn.call_count, 5)

    def test_assembles_each_section_from_the_selected_candidate(self):
        preferences = {
            "general_review": "a",
            "critic_response": "b",
            "audience_review": "skip",
            "comparison_of_reviews": "b",
        }

        response = assemble_response(
            self.candidate_a, self.candidate_b, preferences
        )

        self.assertIn("A general_review", response)
        self.assertIn("B critic_response", response)
        self.assertIn("A audience_review", response)
        self.assertIn("B comparison_of_reviews", response)

    def test_saves_prompt_and_candidates_for_training_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "comparisons.jsonl")
            prompts = {
                section[0]: f"prompt {section[0]}"
                for section in FEEDBACK_SECTIONS
            }
            preferences = {
                section[0]: "a" for section in FEEDBACK_SECTIONS
            }

            save_comparison(
                path, "Inception", "Inception (2010)", "Evidence",
                prompts, self.candidate_a, self.candidate_b, preferences,
                "Qwen test",
            )

            with open(path, encoding="utf-8") as comparison_file:
                record = json.loads(comparison_file.readline())

        self.assertEqual(record["prompts"], prompts)
        self.assertEqual(record["candidate_a"], self.candidate_a)
        self.assertEqual(record["candidate_b"], self.candidate_b)
        self.assertEqual(record["preferences"], preferences)


if __name__ == "__main__":
    unittest.main()
