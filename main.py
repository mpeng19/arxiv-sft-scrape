#!/usr/bin/env python3

import argparse
import subprocess
import os
from pathlib import Path

def run_command(cmd):
    """Run a shell command and print its output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {' '.join(cmd)}")
        print(f"Error output: {result.stderr}")
        raise Exception(f"Command failed with return code {result.returncode}")
    print(result.stdout)
    return result

def scrape_data(args):
    """Handle the data scraping and processing pipeline."""
    base_dir = Path(args.output_dir)
    pdf_dir = base_dir / "pdfs"
    traces_dir = base_dir / "reasoning_traces"
    output_file = base_dir / "sft_data.jsonl"

    for dir_path in [pdf_dir, traces_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)

    run_command([
        "python", "scraper.py",
        "--output_dir", str(pdf_dir),
        "--query", args.query
    ])

    run_command([
        "python", "extract_traces.py",
        "--input_dir", str(pdf_dir),
        "--output_dir", str(traces_dir),
        "--model", args.model
    ])

    run_command([
        "python", "format_data.py",
        "--input_dir", str(traces_dir),
        "--output_file", str(output_file)
    ])

    print(f"\nScraping pipeline completed successfully!")
    print(f"PDFs saved to: {pdf_dir}")
    print(f"Reasoning traces saved to: {traces_dir}")
    print(f"Formatted data saved to: {output_file}")

def train_and_eval(args):
    """Handle the training and evaluation pipeline."""
    base_dir = Path(args.output_dir)
    models_dir = Path("models")
    evals_dir = base_dir / "evals"
    eval_data_file = base_dir / "eval_data.jsonl"
    eval_results_dir = Path("eval_results")

    models_dir.mkdir(exist_ok=True)
    evals_dir.mkdir(exist_ok=True)
    eval_results_dir.mkdir(exist_ok=True)

    run_command([
        "python", "sft.py",
        "--training_file", str(base_dir / "sft_data.jsonl"),
        "--model", args.model,
        "--output_dir", str(models_dir)
    ])

    run_command([
        "python", "extract_traces.py",
        "--input_dir", str(base_dir / "pdfs"),
        "--output_dir", str(evals_dir),
        "--model", str(models_dir / args.fine_tuned_model),
        "--eval_mode"
    ])

    run_command([
        "python", "format_data.py",
        "--input_dir", str(evals_dir),
        "--output_file", str(eval_data_file),
        "--eval_mode"
    ])

    run_command([
        "python", "eval.py",
        "--input_file", str(eval_data_file),
        "--output_dir", str(eval_results_dir)
    ])

    print(f"\nTraining and evaluation pipeline completed successfully!")
    print(f"Model saved to: {models_dir}")
    print(f"Evaluation results saved to: {eval_results_dir}")

def main():
    parser = argparse.ArgumentParser(description="SFT Pipeline for arXiv papers")
    subparsers = parser.add_subparsers(dest="mode", help="Pipeline mode")

    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--output_dir", default="data", help="Base directory for all outputs")
    common_parser.add_argument("--model", default="gpt-4", help="Model to use")

    scrape_parser = subparsers.add_parser("scrape", parents=[common_parser], help="Run data scraping pipeline")
    scrape_parser.add_argument("--query", required=True, help="Search query for arXiv papers")

    train_parser = subparsers.add_parser("train", parents=[common_parser], help="Run training and evaluation pipeline")
    train_parser.add_argument("--fine_tuned_model", required=True, help="Name of the fine-tuned model to use for evaluation")

    args = parser.parse_args()

    if args.mode == "scrape":
        scrape_data(args)
    elif args.mode == "train":
        train_and_eval(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 