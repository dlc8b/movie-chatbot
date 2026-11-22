import argparse
import json
from pathlib import Path

from feedback import FEEDBACK_SECTIONS


def comparison_to_pairs(record):
    examples = []
    preferences = record.get("preferences", {})
    prompts = record.get("prompts", {})
    candidate_a = record.get("candidate_a", {})
    candidate_b = record.get("candidate_b", {})

    for section in FEEDBACK_SECTIONS:
        key = section[0]
        preference = preferences.get(key)
        if preference == "skip":
            continue
        if preference not in ("a", "b"):
            raise ValueError(f"Invalid preference for {key}: {preference!r}")

        prompt = prompts.get(key)
        answer_a = candidate_a.get(key)
        answer_b = candidate_b.get(key)
        if not all(isinstance(value, str) and value.strip()
                   for value in (prompt, answer_a, answer_b)):
            raise ValueError(f"Missing prompt or candidate text for {key}")
        if answer_a.strip() == answer_b.strip():
            continue

        chosen, rejected = (
            (answer_a, answer_b) if preference == "a" else (answer_b, answer_a)
        )
        examples.append({
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
        })
    return examples


def prepare_dataset(input_path, output_path):
    examples = []
    with open(input_path, encoding="utf-8") as comparison_file:
        for line_number, line in enumerate(comparison_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {input_path}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object on line {line_number}")
            try:
                examples.extend(comparison_to_pairs(record))
            except ValueError as exc:
                raise ValueError(
                    f"Invalid comparison on line {line_number}: {exc}"
                ) from exc

    if not examples:
        raise ValueError(
            "No usable A/B preferences found. Collect comparisons where a "
            "reviewer chose A or B for at least one section."
        )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as dataset_file:
        for example in examples:
            dataset_file.write(json.dumps(example, ensure_ascii=False) + "\n")
    return len(examples)


def main():
    code_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Convert reviewed A/B comparisons to DPO preference pairs."
    )
    parser.add_argument(
        "--input",
        default=str(code_dir / "comparisons.jsonl"),
        help="Raw A/B comparison log.",
    )
    parser.add_argument(
        "--output",
        default=str(code_dir / "dpo_dataset.jsonl"),
        help="Generated prompt/chosen/rejected JSONL dataset.",
    )
    args = parser.parse_args()

    count = prepare_dataset(args.input, args.output)
    print(f"Wrote {count} preference pairs to {args.output}")


if __name__ == "__main__":
    main()
