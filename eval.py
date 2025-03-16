import os
import json
import argparse
import time
import random
from tqdm import tqdm
from openai import OpenAI
from anthropic import Anthropic

def load_evaluation_dataset(file_path="eval_dataset.json"):
    """
    Load the evaluation dataset from a JSON file.
    
    Args:
        file_path (str): Path to the evaluation dataset JSON file
        
    Returns:
        list: List of question-answer pairs
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} evaluation examples from {file_path}")
        return data
    except Exception as e:
        print(f"Error loading evaluation dataset: {e}")
        return []

def get_model_response(client, model_name, question, max_retries=3, retry_delay=2):
    """
    Get a response from a model for a given question.
    
    Args:
        client: API client (OpenAI or Anthropic)
        model_name (str): Name of the model to use
        question (str): Question to ask the model
        max_retries (int): Maximum number of retries on failure
        retry_delay (int): Delay between retries in seconds
        
    Returns:
        str: Model's response
    """
    system_prompt = "\nRespond in the following format:\n<reasoning>\n...\n</reasoning>\n<answer>\n...\n</answer>\n"
    
    try:
        if "gpt" in model_name.lower() or "ft:" in model_name:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            return response.choices[0].message.content
        
        elif "claude" in model_name.lower():
            response = client.messages.create(
                model=model_name,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": question}
                ],
                max_tokens=2000
            )
            return response.content[0].text
        
        else:
            raise ValueError(f"Unsupported model: {model_name}")
                
    except Exception as e:
        print(f"Error getting response from {model_name}: {e}")
        return f"Error: Failed to get response from {model_name}."

def judge_responses(client, question, reference_answer, model_a_response, model_b_response, model_a_name, model_b_name):
    """
    Use GPT-4o as a judge to determine which model's response is better.
    
    Args:
        client: OpenAI API client
        question (str): The original question
        reference_answer (str): The reference answer from the dataset
        model_a_response (str): Response from model A
        model_b_response (str): Response from model B
        model_a_name (str): Name of model A
        model_b_name (str): Name of model B
        
    Returns:
        str: 'A' if model A's response is better, 'B' if model B's response is better
    """
    # Normal judging process
    if random.random() < 0.5:
        first_response = model_a_response
        second_response = model_b_response
        first_model = model_a_name
        second_model = model_b_name
        mapping = {'first': 'A', 'second': 'B'}
    else:
        first_response = model_b_response
        second_response = model_a_response
        first_model = model_b_name
        second_model = model_a_name
        mapping = {'first': 'B', 'second': 'A'}
    
    prompt = f"""
You are an impartial judge evaluating the quality of responses to a mathematical reasoning question.

QUESTION:
{question}

REFERENCE ANSWER:
{reference_answer}

FIRST RESPONSE ({first_model}):
{first_response}

SECOND RESPONSE ({second_model}):
{second_response}

Follow these strict evaluation criteria to determine a winner (there must be a winner, no ties allowed):

1. CORRECTNESS: First, determine if each answer is mathematically correct based on the reference answer.

   - If BOTH answers are correct (match the reference answer in mathematical substance):
     * The more CONCISE answer wins. Evaluate based on brevity while still maintaining clarity.

   - If ONE answer is correct and the other is wrong:
     * The correct answer WINS.

   - If BOTH answers are wrong:
     * The answer that makes more progress toward the correct solution wins.
     * The answer with fewer mathematical errors wins.

Your evaluation must be fair and unbiased. You MUST choose a winner - no ties allowed.

OUTPUT FORMAT:
Provide your evaluation in the following format:
CORRECTNESS ASSESSMENT: [Are both answers correct? Is one correct and one wrong? Are both wrong?]
WINNER: [first/second]
REASONING: [brief explanation of your decision based on the criteria above]
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content
        
        if "WINNER: first" in content:
            return mapping['first']
        elif "WINNER: second" in content:
            return mapping['second']
        else:
            # Fallback in case the format isn't followed exactly
            if "first" in content.lower() and "better" in content.lower():
                return mapping['first']
            elif "second" in content.lower() and "better" in content.lower():
                return mapping['second']
            else:
                # If we can't determine a winner, randomly choose one
                return random.choice([mapping['first'], mapping['second']])
            
    except Exception as e:
        print(f"Error in judging responses: {e}")
        # In case of error, randomly choose a winner
        return random.choice([mapping['first'], mapping['second']])

def evaluate_models(eval_dataset, model_a, model_b, openai_api_key=None, anthropic_api_key=None, num_examples=None, start_index=0, output_file=None):
    """
    Evaluate two models on the evaluation dataset.
    
    Args:
        eval_dataset (list): List of question-answer pairs
        model_a (str): Name of model A (e.g., "gpt-4o" or a fine-tuned model ID)
        model_b (str): Name of model B (e.g., "claude-3-7-sonnet-20240307")
        openai_api_key (str): OpenAI API key
        anthropic_api_key (str): Anthropic API key
        num_examples (int): Number of examples to evaluate (if None, evaluate all)
        start_index (int): Index to start evaluation from (skip first start_index examples)
        output_file (str): Path to save detailed results (if None, don't save)
        
    Returns:
        dict: Evaluation results
    """
    if not openai_api_key:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if not openai_api_key:
        raise ValueError("OpenAI API key not provided. Please set OPENAI_API_KEY environment variable or use the --openai_api_key argument.")
    
    openai_client = OpenAI(api_key=openai_api_key)
    
    anthropic_client = None
    if "claude" in model_a.lower() or "claude" in model_b.lower():
        if not anthropic_api_key:
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not anthropic_api_key:
            raise ValueError("Anthropic API key not provided but Claude model requested. Please set ANTHROPIC_API_KEY environment variable or use the --anthropic_api_key argument.")
        
        anthropic_client = Anthropic(api_key=anthropic_api_key)
    
    # Skip the first start_index examples
    if start_index > 0:
        if start_index >= len(eval_dataset):
            raise ValueError(f"Start index {start_index} is greater than or equal to the dataset size {len(eval_dataset)}")
        eval_dataset = eval_dataset[start_index:]
        print(f"Skipping first {start_index} examples. Starting from example {start_index+1}.")
    
    if num_examples and num_examples < len(eval_dataset):
        eval_dataset = eval_dataset[:num_examples]
    
    results = {
        'model_a_wins': 0,
        'model_b_wins': 0,
        'ties': 0,
        'errors': 0,
        'details': []
    }
    
    print(f"Evaluating {model_a} vs {model_b} on {len(eval_dataset)} examples...")
    
    for i, example in enumerate(tqdm(eval_dataset, desc="Evaluating")):
        question = example['question']
        reference_answer = example['answer']
        
        model_a_client = anthropic_client if "claude" in model_a.lower() else openai_client
        model_b_client = anthropic_client if "claude" in model_b.lower() else openai_client
        
        model_a_response = get_model_response(model_a_client, model_a, question)
        time.sleep(1)  # Small delay between API calls
        model_b_response = get_model_response(model_b_client, model_b, question)
        time.sleep(1)  # Small delay between API calls
        
        winner = judge_responses(openai_client, question, reference_answer, model_a_response, model_b_response, model_a, model_b)
        
        if winner == 'A':
            results['model_a_wins'] += 1
        elif winner == 'B':
            results['model_b_wins'] += 1
        else:
            results['errors'] += 1
        
        results['details'].append({
            'question': question,
            'reference_answer': reference_answer,
            'model_a_response': model_a_response,
            'model_b_response': model_b_response,
            'winner': winner
        })
        
        if (i + 1) % 10 == 0:
            print(f"Progress: {i + 1}/{len(eval_dataset)} examples evaluated")
            print(f"Current scores: {model_a}: {results['model_a_wins']}, {model_b}: {results['model_b_wins']}")
    
    total = results['model_a_wins'] + results['model_b_wins']
    if total > 0:
        results['model_a_win_percentage'] = results['model_a_wins'] / total * 100
        results['model_b_win_percentage'] = results['model_b_wins'] / total * 100
    
    print("\nEvaluation Results:")
    print(f"{model_a} wins: {results['model_a_wins']} ({results.get('model_a_win_percentage', 0):.2f}%)")
    print(f"{model_b} wins: {results['model_b_wins']} ({results.get('model_b_win_percentage', 0):.2f}%)")
    print(f"Errors: {results['errors']}")
    
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Detailed results saved to {output_file}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned models against baseline models")
    parser.add_argument("--model_a", default="gpt-4o", help="Model A name (e.g., 'gpt-4o' or a fine-tuned model ID)")
    parser.add_argument("--model_b", default="claude-3-7-sonnet-20240307", help="Model B name (e.g., 'claude-3-7-sonnet-20240307')")
    parser.add_argument("--eval_dataset", default="eval_dataset.json", help="Path to the evaluation dataset JSON file")
    parser.add_argument("--openai_api_key", help="OpenAI API key (if not provided, will use OPENAI_API_KEY environment variable)")
    parser.add_argument("--anthropic_api_key", help="Anthropic API key (if not provided, will use ANTHROPIC_API_KEY environment variable)")
    parser.add_argument("--num_examples", type=int, help="Number of examples to evaluate (if not provided, evaluate all)")
    parser.add_argument("--start", type=int, default=0, help="Index to start evaluation from (skip first N examples)")
    parser.add_argument("--output_file", help="Path to save detailed results (if not provided, don't save)")
    
    args = parser.parse_args()
    
    eval_dataset = load_evaluation_dataset(args.eval_dataset)
    
    if not eval_dataset:
        print("No evaluation examples found. Exiting.")
        return
    
    evaluate_models(
        eval_dataset,
        args.model_a,
        args.model_b,
        args.openai_api_key,
        args.anthropic_api_key,
        args.num_examples,
        args.start,
        args.output_file
    )

if __name__ == "__main__":
    main() 