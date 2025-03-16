import os
import json
import glob
import argparse

def combine_qa_files(input_dir="reasoning_traces", output_file="combined_dataset.jsonl"):
    """
    Combine all JSON files in the input directory into a single JSONL file for training.
    Formats the data for fine-tuning with OpenAI API.
    
    Args:
        input_dir (str): Directory containing the JSON files with Q/A pairs
        output_file (str): Path to the output JSONL file
        
    Returns:
        str: Path to the output file
    """
    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to combine")
    
    all_qa_pairs = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                print(f"Loaded {len(data)} QA pairs from {json_file}")
                all_qa_pairs.extend(data)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    print(f"Total QA pairs collected: {len(all_qa_pairs)}")
    
    formatted_data = []
    for pair in all_qa_pairs:
        messages = pair.get('prompt', [])
        
        if not messages:
            messages = [
                {"role": "system", "content": "You are a mathematical reasoning assistant that provides detailed step-by-step solutions."},
                {"role": "user", "content": pair.get('question', '')}
            ]
        
        messages.append({
            "role": "assistant", 
            "content": f"<reasoning>\n{pair.get('answer', '')}\n</reasoning>\n<answer>\n{pair.get('answer', '')}\n</answer>"
        })
        
        formatted_data.append({"messages": messages})
    
    with open(output_file, 'w') as f:
        for item in formatted_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"Successfully wrote {len(formatted_data)} examples to {output_file}")
    return output_file

def combine_eval_files(input_dir="evals/eval_dataset", output_file="eval_dataset.json"):
    """
    Combine all JSON files in the evaluation dataset directory into a single JSON file.
    Preserves the original format for evaluation purposes.
    
    Args:
        input_dir (str): Directory containing the evaluation dataset files
        output_file (str): Path to the output file
        
    Returns:
        str: Path to the output file
    """
    json_files = glob.glob(os.path.join(input_dir, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return
    
    print(f"Found {len(json_files)} evaluation JSON files to combine")
    
    all_qa_pairs = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                print(f"Loaded {len(data)} QA pairs from {json_file}")
                all_qa_pairs.extend(data)
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    print(f"Total evaluation QA pairs collected: {len(all_qa_pairs)}")
    
    with open(output_file, 'w') as f:
        json.dump(all_qa_pairs, f, indent=2)
    
    print(f"Successfully wrote {len(all_qa_pairs)} examples to {output_file}")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="Format and combine QA pairs for training or evaluation")
    parser.add_argument("--mode", choices=["train", "eval"], default="train", 
                        help="Mode: 'train' to format training data, 'eval' to combine evaluation data")
    parser.add_argument("--input_dir", 
                        help="Input directory containing JSON files (default: 'reasoning_traces' for train mode, 'evals/eval_dataset' for eval mode)")
    parser.add_argument("--output_file", 
                        help="Output file path (default: 'combined_dataset.jsonl' for train mode, 'eval_dataset.json' for eval mode)")
    
    args = parser.parse_args()
    
    if args.mode == "train":
        input_dir = args.input_dir or "reasoning_traces"
        output_file = args.output_file or "combined_dataset.jsonl"
        combine_qa_files(input_dir, output_file)
    else:
        input_dir = args.input_dir or "evals/eval_dataset"
        output_file = args.output_file or "eval_dataset.json"
        combine_eval_files(input_dir, output_file)

if __name__ == "__main__":
    main() 