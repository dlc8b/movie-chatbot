import argparse
import json
from pathlib import Path


MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"


def read_preference_dataset(path):
    records = []
    with open(path, encoding="utf-8") as dataset_file:
        for line_number, line in enumerate(dataset_file, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object on line {line_number}")
            for field in ("prompt", "chosen", "rejected"):
                if not isinstance(record.get(field), str) or not record[field].strip():
                    raise ValueError(
                        f"Missing or empty {field!r} on line {line_number}"
                    )
            if record["chosen"].strip() == record["rejected"].strip():
                raise ValueError(
                    f"Chosen and rejected are identical on line {line_number}"
                )
            records.append({
                "prompt": record["prompt"],
                "chosen": record["chosen"],
                "rejected": record["rejected"],
            })
    return records


def train(args):
    records = read_preference_dataset(args.dataset)
    if not records:
        raise SystemExit(f"No preference pairs found in {args.dataset}")
    if len(records) < args.min_pairs and not args.allow_small_dataset:
        raise SystemExit(
            f"Found {len(records)} pairs; collect at least {args.min_pairs} "
            "reviewed pairs before training, or pass --allow-small-dataset "
            "for an experimental run."
        )

    try:
        import torch  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        if exc.name != "torch":
            raise
        raise SystemExit(
            "PyTorch is required. Install a CUDA-enabled PyTorch build for "
            "your GPU before training."
        ) from exc

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is not available. DPO training requires a CUDA-enabled "
            "PyTorch install and a compatible NVIDIA GPU for this setup."
        )

    try:
        from datasets import Dataset  # type: ignore[import-not-found]
        from peft import LoraConfig  # type: ignore[import-not-found]
        from transformers import AutoTokenizer  # type: ignore[import-not-found]
        from trl import DPOConfig, DPOTrainer  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        missing_package = exc.name or "a training dependency"
        raise SystemExit(
            f"Missing required package: {missing_package}. Install the training "
            "dependencies (datasets, peft, transformers, and trl) before running DPO training."
        ) from exc

    supports_bf16 = torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if supports_bf16 else torch.float16
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    dataset = Dataset.from_list(records)

    training_args = DPOConfig(
        output_dir=args.output_dir,
        model_init_kwargs={"dtype": dtype},
        num_train_epochs=args.epochs,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=1e-5,
        beta=0.1,
        logging_steps=1,
        save_strategy="epoch",
        gradient_checkpointing=True,
        bf16=supports_bf16,
        fp16=not supports_bf16,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        report_to="none",
    )
    peft_config = LoraConfig(
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        task_type="CAUSAL_LM",
    )
    trainer = DPOTrainer(
        model=MODEL_NAME,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved DPO adapter to {args.output_dir}")


def main():
    code_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="LoRA DPO fine-tuning for the movie review assistant."
    )
    parser.add_argument(
        "--dataset",
        default=str(code_dir / "dpo_dataset.jsonl"),
        help="JSONL file with prompt, chosen, and rejected fields.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(code_dir / "movie_dpo_adapter"),
        help="Directory where the trained adapter will be saved.",
    )
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--min-pairs", type=int, default=20)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--max-prompt-length", type=int, default=768)
    parser.add_argument(
        "--allow-small-dataset",
        action="store_true",
        help="Allow an experimental run with fewer than --min-pairs.",
    )
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
