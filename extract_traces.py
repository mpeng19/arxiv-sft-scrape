import os
import argparse
import json
import time
import sys
import re
import glob
from PyPDF2 import PdfReader
from openai import OpenAI
import pandas as pd
from tqdm import tqdm

def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        sys.exit(1)

def chunk_text(text, max_chunk_size=8000, overlap=500):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        if end < len(text) and end - start == max_chunk_size:
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            end = max(last_period, last_newline)
            if end <= start:
                end = start + max_chunk_size
        
        chunks.append(text[start:end])
        start = end - overlap if end < len(text) else end
    
    return chunks

def extract_paper_metadata(text, client, model="gpt-4o-mini"):
    prompt = f"""
    Extract key metadata from this academic paper. Focus on:
    1. The paper's title
    2. The main topic/field
    3. The key mathematical or algorithmic contributions
    4. Any named theorems, algorithms, or models introduced
    
    Format your response as a JSON object with these fields.
    
    TEXT (first part of the paper):
    {text[:5000]}
    
    OUTPUT FORMAT:
    {{
        "title": "Paper title",
        "field": "Main field/topic",
        "contributions": ["Key contribution 1", "Key contribution 2", ...],
        "named_elements": ["Theorem/Algorithm/Model name 1", "Theorem/Algorithm/Model name 2", ...]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content
        
        try:
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                metadata = json.loads(json_str)
                return metadata
            else:
                print("Error: Could not find JSON object in metadata response")
                return {}
        except json.JSONDecodeError:
            print("Error: Failed to parse JSON from metadata response")
            return {}
            
    except Exception as e:
        print(f"Error calling OpenAI API for metadata extraction: {e}")
        return {}

def extract_qa_pairs_from_full_text(text, metadata, client, model="gpt-4o", max_retries=3, retry_delay=2):
    context = f"Title: {metadata.get('title', 'Unknown')}\n"
    context += f"Field: {metadata.get('field', 'Operations Research')}\n"
    
    if metadata.get('contributions'):
        context += f"Key contributions: {', '.join(metadata.get('contributions', []))}\n"
    
    if metadata.get('named_elements'):
        context += f"Named theorems/algorithms: {', '.join(metadata.get('named_elements', []))}\n"
    
    max_text_length = 60000
    if len(text) > max_text_length:
        text = text[:max_text_length]
    
    prompt = f"""
    You are an expert at extracting challenging MATHEMATICAL REASONING problems from academic papers.
    
    PAPER CONTEXT:
    {context}
    
    Extract question-answer pairs from the following academic paper.
    FOCUS EXCLUSIVELY on mathematical content that requires PROOF, DERIVATION, or COMPLEX REASONING.
    
    PRIORITIZE questions that require:
    1. Proving mathematical theorems, lemmas, or properties
    2. Deriving equations or formulas
    3. Analyzing algorithm complexity with mathematical reasoning
    4. Solving optimization problems step-by-step
    5. Formal mathematical arguments and logical deductions
    
    DO NOT include questions that:
    - Simply ask for facts or information from the paper
    - Can be answered without mathematical reasoning
    - Are about general concepts without requiring proof or derivation
    
    Format your response as a JSON array of objects with 'question' and 'answer' fields.
    
    IMPORTANT: The questions should be formulated in a GENERIC way that doesn't require access to the paper.
    Instead of saying "Prove Theorem 3.2 from the paper", say "Given that [state the theorem], prove that..."
    
    Each question MUST:
    - Require mathematical reasoning, proof, or derivation to solve
    - Include all necessary context from the paper
    - Be self-contained with all required information
    - Capture complete chains of mathematical reasoning
    
    The answer should provide a detailed, step-by-step mathematical solution with proper notation.
    
    Try to extract 10-15 high-quality MATHEMATICAL REASONING question-answer pairs.
    
    PAPER TEXT:
    {text}
    
    OUTPUT FORMAT:
    [
        {{
            "question": "Given that a telescope network scheduling problem can be formulated as an integer linear program with variables x_ij representing whether observation i is scheduled at time j, prove that the constraint Σj x_ij ≤ 1 ensures no observation is scheduled more than once.",
            "answer": "To prove that the constraint Σj x_ij ≤ 1 ensures no observation is scheduled more than once, we need to analyze what this constraint means mathematically... [detailed mathematical reasoning]"
        }},
        {{
            "question": "Derive the time complexity of the dynamic programming algorithm for solving the telescope scheduling problem with n observations and m time slots, and prove its correctness.",
            "answer": "To derive the time complexity, we analyze each step of the algorithm... [step-by-step mathematical derivation]"
        }},
        ...
    ]
    """
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            
            try:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    qa_pairs = json.loads(json_str)
                    qa_pairs = [pair for pair in qa_pairs if "question" in pair and "answer" in pair]
                    return qa_pairs
                else:
                    print("Error: Could not find JSON array in response")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        return []
            except json.JSONDecodeError:
                print("Error: Failed to parse JSON from response")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return []
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return []
    
    return []

def extract_qa_pairs(text_chunk, metadata, chunk_index, total_chunks, client, model="gpt-4o-mini", max_retries=3, retry_delay=2):
    context = f"Title: {metadata.get('title', 'Unknown')}\n"
    context += f"Field: {metadata.get('field', 'Operations Research')}\n"
    
    if metadata.get('contributions'):
        context += f"Key contributions: {', '.join(metadata.get('contributions', []))}\n"
    
    if metadata.get('named_elements'):
        context += f"Named theorems/algorithms: {', '.join(metadata.get('named_elements', []))}\n"
    
    chunk_position = "beginning" if chunk_index == 0 else "middle" if chunk_index < total_chunks - 1 else "end"
    
    prompt = f"""
    You are an expert at extracting challenging MATHEMATICAL REASONING problems from academic papers.
    
    PAPER CONTEXT:
    {context}
    
    You are analyzing chunk {chunk_index + 1} of {total_chunks} (the {chunk_position} of the paper).
    
    Extract question-answer pairs from the following text from this specific paper.
    FOCUS EXCLUSIVELY on mathematical content that requires PROOF, DERIVATION, or COMPLEX REASONING.
    
    PRIORITIZE questions that require:
    1. Proving mathematical theorems, lemmas, or properties
    2. Deriving equations or formulas
    3. Analyzing algorithm complexity with mathematical reasoning
    4. Solving optimization problems step-by-step
    5. Formal mathematical arguments and logical deductions
    
    DO NOT include questions that:
    - Simply ask for facts or information from the paper
    - Can be answered without mathematical reasoning
    - Are about general concepts without requiring proof or derivation
    
    Format your response as a JSON array of objects with 'question' and 'answer' fields.
    
    IMPORTANT: The questions should be formulated in a GENERIC way that doesn't require access to the paper.
    Instead of saying "Prove Theorem 3.2 from the paper", say "Given that [state the theorem], prove that..."
    
    Each question MUST:
    - Require mathematical reasoning, proof, or derivation to solve
    - Include all necessary context from the paper
    - Be self-contained with all required information
    
    The answer should provide a detailed, step-by-step mathematical solution with proper notation.
    
    If this chunk contains part of a proof or algorithm that continues from a previous chunk or extends to the next chunk, create questions that focus on the complete parts visible in this chunk.
    
    Try to extract 3-5 high-quality MATHEMATICAL REASONING question-answer pairs if possible.
    
    TEXT:
    {text_chunk}
    
    OUTPUT FORMAT:
    [
        {{
            "question": "Given that a telescope network scheduling problem can be formulated as an integer linear program with variables x_ij representing whether observation i is scheduled at time j, prove that the constraint Σj x_ij ≤ 1 ensures no observation is scheduled more than once.",
            "answer": "To prove that the constraint Σj x_ij ≤ 1 ensures no observation is scheduled more than once, we need to analyze what this constraint means mathematically... [detailed mathematical reasoning]"
        }},
        {{
            "question": "Derive the time complexity of the dynamic programming algorithm for solving the telescope scheduling problem with n observations and m time slots, and prove its correctness.",
            "answer": "To derive the time complexity, we analyze each step of the algorithm... [step-by-step mathematical derivation]"
        }},
        ...
    ]
    """
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            try:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    qa_pairs = json.loads(json_str)
                    qa_pairs = [pair for pair in qa_pairs if "question" in pair and "answer" in pair]
                    
                    for pair in qa_pairs:
                        pair["chunk_index"] = chunk_index
                    
                    return qa_pairs
                else:
                    print(f"Error: Could not find JSON array in response for chunk {chunk_index+1}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    else:
                        return []
            except json.JSONDecodeError:
                print(f"Error: Failed to parse JSON from response for chunk {chunk_index+1}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    return []
                
        except Exception as e:
            print(f"Error calling OpenAI API for chunk {chunk_index+1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                return []
    
    return []

def analyze_cross_chunk_content(all_qa_pairs, full_text, client, model="gpt-4o-mini"):
    if not all_qa_pairs:
        return []
    
    grouped_pairs = {}
    for pair in all_qa_pairs:
        question = pair["question"].lower()
        for term in ["theorem", "lemma", "algorithm", "proof", "equation", "model"]:
            if term in question:
                if term not in grouped_pairs:
                    grouped_pairs[term] = []
                grouped_pairs[term].append(pair)
    
    enhanced_pairs = []
    processed_indices = set()
    
    for term, pairs in grouped_pairs.items():
        if len(pairs) <= 1:
            continue
        
        pairs.sort(key=lambda x: x["chunk_index"])
        
        for i in range(len(pairs) - 1):
            if pairs[i]["chunk_index"] + 1 == pairs[i+1]["chunk_index"] or pairs[i]["chunk_index"] + 2 == pairs[i+1]["chunk_index"]:
                if pairs[i]["chunk_index"] in processed_indices or pairs[i+1]["chunk_index"] in processed_indices:
                    continue
                
                start_pos = max(0, pairs[i]["chunk_index"] * 7500)
                end_pos = min(len(full_text), (pairs[i+1]["chunk_index"] + 1) * 7500)
                relevant_text = full_text[start_pos:end_pos]
                
                prompt = f"""
                I have identified related mathematical content that spans multiple sections of the paper.
                
                CONTENT FROM SECTION {pairs[i]["chunk_index"] + 1}-{pairs[i+1]["chunk_index"] + 1}:
                {relevant_text[:8000]}
                
                RELATED QUESTIONS IDENTIFIED:
                1. {pairs[i]["question"]}
                2. {pairs[i+1]["question"]}
                
                Please create ONE comprehensive question-answer pair that covers this mathematical content completely.
                The question MUST require mathematical reasoning, proof, or derivation to solve.
                The answer should provide a complete, step-by-step mathematical solution with proper notation.
                
                IMPORTANT: The question should be formulated in a GENERIC way that doesn't require access to the paper.
                Include enough context from the paper so it can be understood without access to the paper.
                
                OUTPUT FORMAT (return ONLY this JSON object, nothing else):
                {{
                    "question": "Comprehensive mathematical reasoning question covering the full mathematical content",
                    "answer": "Complete, detailed mathematical solution with all necessary steps and reasoning"
                }}
                """
                
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                        max_tokens=2000
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    try:
                        if content.startswith('```json'):
                            content = content[7:]
                        if content.endswith('```'):
                            content = content[:-3]
                        
                        content = content.strip()
                        
                        start_idx = content.find('{')
                        end_idx = content.rfind('}') + 1
                        
                        if start_idx >= 0 and end_idx > start_idx:
                            json_str = content[start_idx:end_idx]
                            enhanced_pair = json.loads(json_str)
                            if "question" in enhanced_pair and "answer" in enhanced_pair:
                                enhanced_pairs.append(enhanced_pair)
                                processed_indices.add(pairs[i]["chunk_index"])
                                processed_indices.add(pairs[i+1]["chunk_index"])
                            else:
                                print("Error: Enhanced pair missing question or answer fields")
                        else:
                            print("Error: Could not find JSON object in cross-chunk response")
                    except json.JSONDecodeError as e:
                        print(f"Error: Failed to parse JSON from cross-chunk response: {e}")
                        
                except Exception as e:
                    print(f"Error calling OpenAI API for cross-chunk analysis: {e}")
    
    for pair in all_qa_pairs:
        if pair["chunk_index"] not in processed_indices:
            pair_copy = pair.copy()
            if "chunk_index" in pair_copy:
                del pair_copy["chunk_index"]
            enhanced_pairs.append(pair_copy)
        
    return enhanced_pairs

def deduplicate_qa_pairs(qa_pairs):
    seen_questions = set()
    unique_pairs = []
    
    for pair in qa_pairs:
        question = re.sub(r'[^\w\s]', '', pair["question"].strip().lower())
        question = re.sub(r'\s+', ' ', question)
        if question not in seen_questions:
            seen_questions.add(question)
            unique_pairs.append(pair)
    
    return unique_pairs

def format_qa_pairs_for_output(qa_pairs, max_pairs=50):
    qa_pairs = qa_pairs[:max_pairs]
    
    formatted_pairs = []
    for i, pair in enumerate(qa_pairs):
        question = pair['question']
        
        formatted_pair = {
            'question': question,
            'answer': pair['answer'],
            'prompt': [
                {
                    'content': '\nRespond in the following format:\n<reasoning>\n...\n</reasoning>\n<answer>\n...\n</answer>\n',
                    'role': 'system'
                },
                {
                    'content': question,
                    'role': 'user'
                }
            ]
        }
        formatted_pairs.append(formatted_pair)
    
    return formatted_pairs

def process_pdf(pdf_path, output_dir="reasoning_traces", output_index=1, api_key=None, model="gpt-4o", max_pairs=50, force_chunking=False):
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("Error: OpenAI API key not provided. Please set OPENAI_API_KEY environment variable or use the --api_key argument.")
    
    client = OpenAI(api_key=api_key)
    
    print(f"Processing PDF {output_index}: {os.path.basename(pdf_path)}")
    
    text = extract_text_from_pdf(pdf_path)
    metadata = extract_paper_metadata(text, client, model)
    
    use_chunking = force_chunking or len(text) > 60000
    
    if use_chunking:
        chunks = chunk_text(text, max_chunk_size=8000, overlap=500)
        print(f"Processing {len(chunks)} chunks...")
        
        all_qa_pairs = []
        for i, chunk in enumerate(tqdm(chunks, desc="Processing", leave=False)):
            qa_pairs = extract_qa_pairs(chunk, metadata, i, len(chunks), client, model=model)
            all_qa_pairs.extend(qa_pairs)
            
            if i < len(chunks) - 1:
                time.sleep(1)
        
        enhanced_qa_pairs = analyze_cross_chunk_content(all_qa_pairs, text, client, model)
    else:
        all_qa_pairs = extract_qa_pairs_from_full_text(text, metadata, client, model=model)
        enhanced_qa_pairs = all_qa_pairs
    
    unique_qa_pairs = deduplicate_qa_pairs(enhanced_qa_pairs)
    formatted_pairs = format_qa_pairs_for_output(unique_qa_pairs, max_pairs)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_path = os.path.join(output_dir, f"output{output_index}.json")
    with open(output_path, 'w') as f:
        json.dump(formatted_pairs, f, indent=2)
    
    print(f"Extracted {len(formatted_pairs)} QA pairs from PDF {output_index}")
    return output_path

def process_pdfs_directory(api_key=None, max_pairs=50, num_pdfs=None, force_chunking=False, eval_dir=None):
    if eval_dir:
        pdf_dir = os.path.join("evals", "pdfs")
        output_dir = os.path.join("evals", "eval_dataset")
    else:
        pdf_dir = "pdfs"
        output_dir = "reasoning_traces"
    
    if not os.path.exists(pdf_dir):
        raise ValueError(f"Error: PDF directory does not exist: {pdf_dir}")
    
    existing_outputs = 0
    if os.path.exists(output_dir):
        existing_outputs = len([f for f in os.listdir(output_dir) if f.startswith("output") and f.endswith(".json")])
    
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    
    if num_pdfs and num_pdfs < len(pdf_files):
        pdf_files = pdf_files[:num_pdfs]
    
    if existing_outputs > 0:
        print(f"Found {existing_outputs} existing output files. Skipping the first {existing_outputs} PDFs.")
        if existing_outputs >= len(pdf_files):
            print("All PDFs have already been processed. Nothing to do.")
            return
        pdf_files = pdf_files[existing_outputs:]
    
    print(f"Processing {len(pdf_files)} PDF files from {pdf_dir}")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for i, pdf_file in enumerate(pdf_files):
        output_index = i + 1 + existing_outputs
        pdf_path = os.path.join(pdf_dir, pdf_file)
        
        try:
            process_pdf(pdf_path, output_dir, output_index, api_key, "gpt-4o", max_pairs, force_chunking)
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
    
    print(f"Processing complete. Processed {len(pdf_files)} PDF files.")
    
    if eval_dir:
        print(f"To combine the evaluation files, run: python format_data.py --mode eval")
    else:
        print(f"To combine the training files, run: python format_data.py --mode train")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract mathematical reasoning question-answer pairs from PDFs")
    parser.add_argument("--api_key", help="OpenAI API key (if not provided, will use OPENAI_API_KEY environment variable)")
    parser.add_argument("--max_pairs", type=int, default=50, help="Maximum number of Q/A pairs to include per document (default: 50)")
    parser.add_argument("--num_pdfs", type=int, help="Number of PDFs to process (default: all)")
    parser.add_argument("--force_chunking", action="store_true", help="Force using chunking even for small PDFs")
    parser.add_argument("--eval", help="Process PDFs from the specified evaluation directory instead of the default pdfs directory")
    args = parser.parse_args()
    
    process_pdfs_directory(args.api_key, args.max_pairs, args.num_pdfs, args.force_chunking, args.eval)
