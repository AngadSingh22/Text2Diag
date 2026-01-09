#!/usr/bin/env python3
"""
Step W2: Baseline Training & Eval Entrypoint.
"""
import argparse
import json
import sys
import torch
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from text2diag.model.baseline import build_model
from text2diag.data.jsonl_dataset import Text2DiagDataset
from text2diag.train.train_baseline import run_training
from text2diag.eval.eval_baseline import evaluate_and_dump

def main():
    parser = argparse.ArgumentParser(description="Train Baseline Model")
    
    # Data Args
    parser.add_argument("--data_dir", type=Path, required=True, help="Path to processed JSONL files")
    parser.add_argument("--out_dir", type=Path, default=Path("results/week2"), help="Output directory")
    
    # Model Args
    parser.add_argument("--model_name", type=str, default="distilbert-base-uncased")
    parser.add_argument("--max_len", type=int, default=256)
    
    # Training Args
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
    
    # 1. Load Label Map
    # Look for label2id.json or labels.json in data_dir
    label2id = {}
    label_path = args.data_dir / "labels.json" # W1 output
    
    if label_path.exists():
        with open(label_path, "r", encoding="utf-8") as f:
            labels = json.load(f)
            label2id = {l: i for i, l in enumerate(sorted(labels))}
    else:
        # Try label2id.json if specificed in Prompt (though W1 output labels.json)
        l2id_path = args.data_dir / "label2id.json"
        if l2id_path.exists():
            with open(l2id_path, "r", encoding="utf-8") as f:
                label2id = json.load(f)
        else:
             raise FileNotFoundError(f"Could not find labels.json or label2id.json in {args.data_dir}")

    id2label = {i: l for l, i in label2id.items()}
    num_labels = len(label2id)
    print(f"Loaded {num_labels} labels from {args.data_dir}")
    
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
    
    # 5. Load Best (Trainer usually reloads, but redundant check ensures we use it for final eval)
    # The run_training function returns the path. 
    # Note: Trainer.train() with load_best_model_at_end=True keeps the best model in memory
    # BUT if we want to be safe, we can reload. 
    # train_baseline logic uses load_best_model_at_end=True, so 'model' passed to eval should be best.
    
    # 6. Evaluation
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
        
    # Markdown Summary
    md_path = args.out_dir / "metrics.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Week 2 Baseline Results\n\n")
        f.write(f"**Model**: {args.model_name}\n")
        f.write(f"**Best Checkpoint**: {best_ckpt_path}\n\n")
        
        for split in ["val", "test"]:
            f.write(f"## {split.capitalize()} Metrics\n")
            res = metrics[split]
            f.write(f"- **Micro F1**: {res['micro_f1']:.4f}\n")
            f.write(f"- **Macro F1**: {res['macro_f1']:.4f}\n")
            f.write(f"- **Micro AUC**: {res.get('micro_roc_auc', -1):.4f}\n\n")

    print(f"Done. Artifacts saved to {args.out_dir}")

if __name__ == "__main__":
    main()
