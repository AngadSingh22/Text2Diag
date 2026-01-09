"""
Training Logic for Baseline Model.

Uses HuggingFace Trainer for multi-label classification.
"""
import numpy as np
import torch
from pathlib import Path
from typing import Dict, Any, List, Optional
from transformers import (
    Trainer, 
    TrainingArguments, 
    PreTrainedModel, 
    PreTrainedTokenizer,
    EvalPrediction
)
from sklearn.metrics import f1_score, roc_auc_score

def compute_metrics(p: EvalPrediction) -> Dict[str, float]:
    """
    Compute micro/macro F1 for validation during training.
    Uses sigmoid threshold 0.5.
    """
    logits = p.predictions
    labels = p.label_ids
    
    # Sigmoid + Threshold
    probs = 1.0 / (1.0 + np.exp(-logits))
    preds = (probs > 0.5).astype(int)
    
    # F1
    micro_f1 = f1_score(labels, preds, average="micro", zero_division=0)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    
    return {
        "micro_f1": micro_f1, 
        "macro_f1": macro_f1
    }

def run_training(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    train_dataset: Any,
    val_dataset: Any,
    output_dir: Path,
    batch_size: int = 8,
    grad_accum_steps: int = 4,
    learning_rate: float = 2e-5,
    epochs: int = 3,
    seed: int = 1337,
    fp16: bool = True
) -> str:
    """
    Run training and return path to best checkpoint.
    """
    # Arguments
    args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        evaluation_strategy="epoch",
        save_strategy="epoch",
        logging_strategy="epoch",
        learning_rate=learning_rate,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        gradient_accumulation_steps=grad_accum_steps,
        num_train_epochs=epochs,
        weight_decay=0.01,
        seed=seed,
        fp16=fp16 and torch.cuda.is_available(),
        load_best_model_at_end=True,
        metric_for_best_model="micro_f1",
        save_total_limit=1,
        dataloader_num_workers=0, # Avoid Windows multiprocessing issues
        push_to_hub=False,
        remove_unused_columns=False # Required for custom Dataset with 'example_id'
    )
    
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer
    )
    
    print("Starting training...")
    trainer.train()
    
    best_ckpt = trainer.state.best_model_checkpoint
    print(f"Training complete. Best checkpoint: {best_ckpt}")
    
    return best_ckpt if best_ckpt else str(output_dir / "checkpoints" / "final")
