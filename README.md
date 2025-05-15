# Model Comparison and SFT Pipeline

tool for generating supervised fine-tuning (SFT) data from arxiv papers.

## SFT Data Generation Pipeline
   ```bash
   python scraper.py --output_dir pdfs/ --query "your search query" && python extract_traces.py --input_dir pdfs/ --output_dir reasoning_traces/ --model gpt-4o && python format_data.py --input_dir reasoning_traces/ --output_file sft_data.jsonl && python sft.py --training_file sft_data.jsonl --model gpt-4o --output_dir models/ && python extract_traces.py --input_dir pdfs/ --output_dir evals/ --model models/your-fine-tuned-model --eval_mode && python format_data.py --input_dir evals/ --output_file eval_data.jsonl --eval_mode && python eval.py --input_file eval_data.jsonl --output_dir eval_results/
   ```

## Web App for Model Comparison
   ```bash
   cd model-comparison-app
   bun install
   bun dev
   ```
   - Open [http://localhost:3000](http://localhost:3000) in your browser

