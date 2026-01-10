import argparse
import json
import re
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_file", type=Path, required=True)
    args = parser.parse_args()
    
    # Diagnosis terms to check (Case Insensitive)
    # These are the labels we are trying to predict.
    # If they appear in input, it's leakage.
    forbidden = [
        "adhd", "add", 
        "depression", "depressed", 
        "anxiety", "anxious", 
        "bipolar", 
        "ptsd", 
        "ocd", 
        "schizophrenia", "schizo"
    ]
    
    # Simple regex for whole words
    # Note: This might catch "anti-depressants" as "depress" if not careful, 
    # but we want to be strict.
    pattern = re.compile(r'\b(' + '|'.join(forbidden) + r')\b', re.IGNORECASE)
    
    print(f"Scanning {args.data_file} for leakage...")
    print(f"Forbidden terms: {forbidden}")
    
    total = 0
    leaked = 0
    matches = []
    
    with open(args.data_file, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            data = json.loads(line)
            text = data.get("text", "")
            
            found = pattern.findall(text)
            if found:
                leaked += 1
                # Store first few comparisons
                if len(matches) < 10:
                    matches.append(f"Found {found}: {text[:100]}...")
    
    rate = (leaked / total) * 100 if total > 0 else 0
    
    print(f"\nStats:")
    print(f"Total Examples: {total}")
    print(f"Examples with Forbidden Terms: {leaked}")
    print(f"Leakage Rate: {rate:.2f}%")
    
    if matches:
        print("\nSample Leaks:")
        for m in matches:
            print(f"- {m}")
    
    if rate < 1.0:
        print("\nVERDICT: CLEAN (Acceptable Tolerance <1%)")
        if leaked > 0:
            print("Note: Minor residuals found. Suggest review if critical.")
    else:
        print(f"\nVERDICT: LEAK DETECTED (>1%). Rate: {rate:.2f}%")

if __name__ == "__main__":
    main()
