#!/usr/bin/env python3
"""
Week 3: Train Robust Baseline (Sanitized Data).

This script trains the model on the 'blinded' dataset where diagnosis words 
are masked. This forces the model to learn symptom patterns instead of shortcuts.
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.model.baseline import build_model
from text2diag.data.jsonl_dataset import Text2DiagDataset
from text2diag.train.train_baseline import run_training
from text2diag.eval.eval_baseline import evaluate_and_dump
import json

def main():
    parser = argparse.ArgumentParser(description="Train Robust Baseline (W3)")
    
    # Data Args
    parser.add_argument("--data_dir", type=Path, default=Path("data/processed/reddit_mh_sanitized"), help="Path to SANITIZED data")
    parser.add_argument("--out_dir", type=Path, default=Path("results/week3/robust_baseline"), help="Output directory")
    
    # Model Args
    parser.add_argument("--model_name", type=str, default="distilbert-base-uncased")
    parser.add_argument("--max_len", type=int, default=256)
    
    # Training Args (Identical to W2 Baseline for fair comparison)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--fp16", action="store_true", default=True)
    # Smoke Test
    parser.add_argument("--limit_examples", type=int, default=None, help="Limit dataset size for smoke testing")
    
    args = parser.parse_args()
    
    # Setup Output
    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Training ROBUST baseline on {args.data_dir}")
    print(f"Output: {args.out_dir}")
    
    # 1. Load Label Map
    l2id_path = args.data_dir / "label2id.json"
    if not l2id_path.exists():
         # Fallback to labels.json
         l2id_path = args.data_dir / "labels.json"
         if not l2id_path.exists():
            raise FileNotFoundError(f"Could not find labels.json or label2id.json in {args.data_dir}")
         with open(l2id_path, "r", encoding="utf-8") as f:
            labels = json.load(f)
            label2id = {l: i for i, l in enumerate(sorted(labels))}
    else:
        with open(l2id_path, "r", encoding="utf-8") as f:
            label2id = json.load(f)

    id2label = {i: l for l, i in label2id.items()}
    num_labels = len(label2id)
    print(f"Loaded {num_labels} labels")
    
    # 2. Build Model & Tokenizer
    print(f"Loading model: {args.model_name}")
    tokenizer, model = build_model(
        args.model_name, 
        num_labels=num_labels,
        id2label=id2label,
        label2id=label2id
    )
    
    # 3. Load Datasets
    print("Loading datasets...")
    train_ds = Text2DiagDataset(args.data_dir / "train.jsonl", tokenizer, label2id, args.max_len)
    val_ds = Text2DiagDataset(args.data_dir / "val.jsonl", tokenizer, label2id, args.max_len)
    
    if args.limit_examples:
        print(f"SMOKE TEST: Limiting training/val to {args.limit_examples} examples.")
        train_ds.examples = train_ds.examples[:args.limit_examples]
        val_ds.examples = val_ds.examples[:args.limit_examples]
    
    # 4. Train
    best_ckpt_path = run_training(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        val_dataset=val_ds,
        output_dir=args.out_dir,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum,
        learning_rate=args.lr,
        epochs=args.epochs,
        seed=args.seed,
        fp16=args.fp16
    )
    
    # 5. Evaluation
    test_ds = Text2DiagDataset(args.data_dir / "test.jsonl", tokenizer, label2id, args.max_len)
    if args.limit_examples:
        test_ds.examples = test_ds.examples[:args.limit_examples]
    
    metrics = {}
    
    # Eval Val
    val_metrics = evaluate_and_dump(model, val_ds, "val", args.out_dir, id2label)
    metrics["val"] = val_metrics
    
    # Eval Test
    test_metrics = evaluate_and_dump(model, test_ds, "test", args.out_dir, id2label)
    metrics["test"] = test_metrics
    
    # Save Metrics
    metrics_path = args.out_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"✅ Training Complete. Metrics saved to {metrics_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
