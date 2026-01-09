"""
JSONL Dataset Loader for Text2Diag.

Reads canonical JSONL files and converts to tokenized tensors with multi-hot labels.
"""
import json
import torch
from pathlib import Path
from typing import List, Dict, Any, Union
from torch.utils.data import Dataset

class Text2DiagDataset(Dataset):
    def __init__(
        self, 
        data_path: Union[str, Path], 
        tokenizer: Any,
        label_map: Dict[str, int],
        max_len: int = 512,
        text_field: str = "text"
    ):
        self.data_path = Path(data_path)
        self.tokenizer = tokenizer
        self.label_map = label_map
        self.num_labels = len(label_map)
        self.max_len = max_len
        self.text_field = text_field
        
        self.examples = self._load_data()

    def _load_data(self) -> List[Dict]:
        examples = []
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")
            
        with open(self.data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    examples.append(json.loads(line))
        return examples

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        ex = self.examples[idx]
        text = ex[self.text_field]
        labels_list = ex.get("labels", [])
        example_id = ex.get("example_id", str(idx))
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_len,
            return_tensors="pt"
        )
        
        # Create multi-hot label vector
        label_vec = torch.zeros(self.num_labels, dtype=torch.float)
        for lbl in labels_list:
            if lbl in self.label_map:
                label_vec[self.label_map[lbl]] = 1.0
                
        # Remove batch dim added by tokenizer
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item["labels"] = label_vec
        item["example_id"] = example_id  # Passed for eval mapping (might need custom collator if using HF Trainer)
        
        return item
