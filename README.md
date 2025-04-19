# Model Comparison and SFT Pipeline

This repository contains tools for generating supervised fine-tuning (SFT) data and a web application for comparing different language models side-by-side.

## SFT Data Generation Pipeline

   ```bash
   python scraper.py --output_dir pdfs/ --query "your search query"
   ```
   ```bash
   python extract_traces.py --input_dir pdfs/ --output_dir reasoning_traces/ --model gpt-4o
   ```
   ```bash
   python format_data.py --input_dir reasoning_traces/ --output_file sft_data.jsonl
   ```
   ```bash
   python sft.py --training_file sft_data.jsonl --model gpt-4o --output_dir models/
   ```
   ```bash
   python extract_traces.py --input_dir pdfs/ --output_dir evals/ --model models/your-fine-tuned-model --eval_mode
   ```
   ```bash
   python format_data.py --input_dir evals/ --output_file eval_data.jsonl --eval_mode
   ```
   ```bash
   python eval.py --input_file eval_data.jsonl --output_dir eval_results/
   ```

## Web App for Model Comparison
   ```bash
   cd model-comparison-app
   ```
   ```bash
   npm install
   # or
   bun install
   ```
   ```bash
   npm run dev
   # or
   bun dev
   ```
   - Open [http://localhost:3000](http://localhost:3000) in your browser

