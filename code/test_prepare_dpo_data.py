import json
import os
import tempfile
import unittest

from feedback import FEEDBACK_SECTIONS
from prepare_dpo_data import comparison_to_pairs, prepare_dataset
from train_dpo import read_preference_dataset


class DpoDataTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "prompts": {},
            "candidate_a": {},
            "candidate_b": {},
            "preferences": {},
        }
        for section in FEEDBACK_SECTIONS:
            key = section[0]
            self.record["prompts"][key] = f"same prompt for {key}"
            self.record["candidate_a"][key] = f"A response for {key}"
            self.record["candidate_b"][key] = f"B response for {key}"
            self.record["preferences"][key] = "skip"

    def test_converts_each_selected_section_into_a_dpo_pair(self):
        self.record["preferences"]["general_review"] = "a"
        self.record["preferences"]["critic_response"] = "b"

        pairs = comparison_to_pairs(self.record)

        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0]["prompt"], "same prompt for general_review")
        self.assertEqual(pairs[0]["chosen"], "A response for general_review")
        self.assertEqual(pairs[0]["rejected"], "B response for general_review")
        self.assertEqual(pairs[1]["chosen"], "B response for critic_response")
        self.assertEqual(pairs[1]["rejected"], "A response for critic_response")

    def test_skips_ties_and_identical_candidates(self):
        self.record["preferences"]["general_review"] = "a"
        self.record["candidate_b"]["general_review"] = (
            self.record["candidate_a"]["general_review"]
        )

        self.assertEqual(comparison_to_pairs(self.record), [])

    def test_writes_jsonl_accepted_by_training_loader(self):
        self.record["preferences"]["audience_review"] = "b"
        with tempfile.TemporaryDirectory() as directory:
            raw_path = os.path.join(directory, "comparisons.jsonl")
            dataset_path = os.path.join(directory, "dpo_dataset.jsonl")
            with open(raw_path, "w", encoding="utf-8") as raw_file:
                raw_file.write(json.dumps(self.record) + "\n")

            count = prepare_dataset(raw_path, dataset_path)
            records = read_preference_dataset(dataset_path)

        self.assertEqual(count, 1)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["chosen"], "B response for audience_review")
        self.assertEqual(records[0]["rejected"], "A response for audience_review")


if __name__ == "__main__":
    unittest.main()
