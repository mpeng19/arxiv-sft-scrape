# Model Comparison and SFT Pipeline

tool for generating supervised fine-tuning (SFT) data from arxiv papers.

## SFT Data Generation Pipeline
   ```bash
   python main.py scrape --query "your search query" --output_dir data --model gpt-4
   python main.py train --output_dir data --model gpt-4 --fine_tuned_model your-fine-tuned-model
   ```

## Web App for Model Comparison
   ```bash
   cd model-comparison-app
   bun install
   bun dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser

