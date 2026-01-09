"""
Baseline Model Builder.

Wraps HuggingFace AutoModelForSequenceClassification for multi-label tasks.
"""
from typing import Tuple, Any
from transformers import AutoTokenizer, AutoModelForSequenceClassification, PreTrainedTokenizer, PreTrainedModel

def build_model(
    model_name: str, 
    num_labels: int,
    id2label: dict[int, str] = None,
    label2id: dict[str, int] = None
) -> Tuple[PreTrainedTokenizer, PreTrainedModel]:
    """
    Load tokenizer and model for multi-label classification.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Configure mapping if provided
    config_kwargs = {"num_labels": num_labels}
    if id2label and label2id:
        config_kwargs["id2label"] = id2label
        config_kwargs["label2id"] = label2id
        
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        problem_type="multi_label_classification",
        **config_kwargs
    )
    
    return tokenizer, model
