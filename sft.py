import os
import argparse
import json
import time
from openai import OpenAI

def validate_jsonl_file(file_path):
    print(f"Validating file: {file_path}")
    
    with open(file_path, 'r') as f:
        line_count = 0
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line)
                line_count += 1
                
                if 'messages' not in data:
                    print(f"Error on line {line_num}: Missing 'messages' field")
                    return False
                
                if not isinstance(data['messages'], list) or len(data['messages']) < 2:
                    print(f"Error on line {line_num}: 'messages' must be a list with at least 2 messages")
                    return False
                
                for i, msg in enumerate(data['messages']):
                    if 'role' not in msg or 'content' not in msg:
                        print(f"Error on line {line_num}, message {i}: Missing 'role' or 'content'")
                        return False
                    
                    if msg['role'] not in ['system', 'user', 'assistant']:
                        print(f"Error on line {line_num}, message {i}: Invalid role '{msg['role']}'")
                        return False
            
            except json.JSONDecodeError:
                print(f"Error on line {line_num}: Invalid JSON")
                return False
    
    print(f"Validation successful. File contains {line_count} valid examples.")
    return True

def upload_file(client, file_path):
    try:
        with open(file_path, "rb") as file:
            response = client.files.create(
                file=file,
                purpose="fine-tune"
            )
        print(f"File uploaded successfully. File ID: {response.id}")
        return response.id
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_fine_tuning_job(client, file_id, model="gpt-4o-2024-08-06", suffix=None, epochs=3):
    try:
        job_params = {
            "training_file": file_id,
            "model": model,
            "hyperparameters": {
                "n_epochs": epochs
            }
        }
        
        if suffix:
            job_params["suffix"] = suffix
        
        response = client.fine_tuning.jobs.create(**job_params)
        
        print(f"Fine-tuning job created successfully. Job ID: {response.id}")
        print(f"Status: {response.status}")
        print(f"Model: {response.fine_tuned_model or 'Not available yet'}")
        print(f"Epochs: {epochs}")
        
        return response.id
    except Exception as e:
        print(f"Error creating fine-tuning job: {e}")
        return None

def check_fine_tuning_status(client, job_id):
    try:
        response = client.fine_tuning.jobs.retrieve(job_id)
        
        print(f"Job ID: {response.id}")
        print(f"Status: {response.status}")
        print(f"Created at: {response.created_at}")
        print(f"Finished at: {response.finished_at or 'Not finished yet'}")
        print(f"Fine-tuned model: {response.fine_tuned_model or 'Not available yet'}")
        
        if response.error:
            print(f"Error: {response.error}")
        
        return response.status
    except Exception as e:
        print(f"Error checking fine-tuning status: {e}")
        return None

def run_fine_tuning(api_key=None, input_file="combined_dataset.jsonl", model="gpt-4o-2024-08-06", suffix=None, wait=False, epochs=3):
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key not provided. Please set OPENAI_API_KEY environment variable or use the --api_key argument.")
    
    client = OpenAI(api_key=api_key)
    
    if not validate_jsonl_file(input_file):
        print("File validation failed. Please fix the issues and try again.")
        return
    
    file_id = upload_file(client, input_file)
    if not file_id:
        print("File upload failed. Aborting fine-tuning.")
        return
    
    print("Waiting for file to be processed...")
    time.sleep(5)
    
    job_id = create_fine_tuning_job(client, file_id, model, suffix, epochs)
    if not job_id:
        print("Fine-tuning job creation failed. Aborting.")
        return
    
    if wait:
        print("Monitoring fine-tuning job status...")
        status = None
        while status not in ["succeeded", "failed", "cancelled"]:
            status = check_fine_tuning_status(client, job_id)
            if status in ["succeeded", "failed", "cancelled"]:
                break
            print("Waiting 60 seconds before checking again...")
            time.sleep(60)
        
        print(f"Fine-tuning job {status}.")
        if status == "succeeded":
            response = client.fine_tuning.jobs.retrieve(job_id)
            print(f"Fine-tuned model name: {response.fine_tuned_model}")
    else:
        print("Fine-tuning job started. You can check its status later with:")
        print(f"  python sft.py --check_status {job_id}")

def check_job_status(api_key=None, job_id=None):
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key not provided. Please set OPENAI_API_KEY environment variable or use the --api_key argument.")
    
    if not job_id:
        raise ValueError("Job ID not provided. Please use the --check_status argument.")
    
    client = OpenAI(api_key=api_key)
    check_fine_tuning_status(client, job_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune GPT-4o on mathematical reasoning data")
    parser.add_argument("--api_key", help="OpenAI API key (if not provided, will use OPENAI_API_KEY environment variable)")
    parser.add_argument("--input_file", default="combined_dataset.jsonl", help="Path to the JSONL file containing the training data")
    parser.add_argument("--model", default="gpt-4o-2024-08-06", help="Base model to fine-tune")
    parser.add_argument("--suffix", help="Custom suffix for the fine-tuned model name")
    parser.add_argument("--wait", action="store_true", help="Wait and monitor the fine-tuning job until completion")
    parser.add_argument("--check_status", help="Check the status of an existing fine-tuning job by ID")
    parser.add_argument("--epochs", type=int, default=3, help="Number of epochs for fine-tuning (default: 3)")
    
    args = parser.parse_args()
    
    if args.check_status:
        check_job_status(args.api_key, args.check_status)
    else:
        run_fine_tuning(args.api_key, args.input_file, args.model, args.suffix, args.wait, args.epochs) 