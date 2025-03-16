# Model Comparison and SFT Pipeline

This repository contains tools for generating supervised fine-tuning (SFT) data and a web application for comparing different language models side-by-side.

## SFT Data Generation Pipeline

Follow these steps to generate and evaluate SFT data:

1. **Scrape data for training**:
   ```bash
   python scraper.py --output_dir pdfs/ --query "your search query"
   ```
   This will download PDFs related to your query and save them in the pdfs directory.

2. **Extract reasoning traces from base model**:
   ```bash
   python extract_traces.py --input_dir pdfs/ --output_dir reasoning_traces/ --model gpt-4o
   ```
   This extracts reasoning traces from the base model for each document.

3. **Format data for fine-tuning**:
   ```bash
   python format_data.py --input_dir reasoning_traces/ --output_file sft_data.jsonl
   ```
   This formats the reasoning traces into the proper format for fine-tuning.

4. **Fine-tune the model**:
   ```bash
   python sft.py --training_file sft_data.jsonl --model gpt-4o --output_dir models/
   ```
   This fine-tunes the model using the formatted data.

5. **Extract evaluation traces**:
   ```bash
   python extract_traces.py --input_dir pdfs/ --output_dir evals/ --model models/your-fine-tuned-model --eval_mode
   ```
   This extracts reasoning traces from your fine-tuned model for evaluation.

6. **Format evaluation data**:
   ```bash
   python format_data.py --input_dir evals/ --output_file eval_data.jsonl --eval_mode
   ```
   This formats the evaluation traces for comparison.

7. **Run evaluation**:
   ```bash
   python eval.py --input_file eval_data.jsonl --output_dir eval_results/
   ```
   This evaluates the performance of your fine-tuned model against the base model.

## Setting Up the Web App for Model Comparison

The web app allows you to compare different models side-by-side and generate additional training data.

1. **Navigate to the app directory**:
   ```bash
   cd model-comparison-app
   ```

2. **Install dependencies**:
   ```bash
   npm install
   # or
   bun install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   # or
   bun dev
   ```

4. **Access the application**:
   - Open [http://localhost:3000](http://localhost:3000) in your browser
   - Select your models (including your fine-tuned model) and enter your API keys
   - Start comparing model responses

## Using the Web App for Additional Training Data

1. **Setup the comparison interface**:
   - Select your fine-tuned model and a reference model (e.g., Claude 3.7 Sonnet)
   - Enter your API keys for both services

2. **Generate comparison data**:
   - Ask questions in the chat interface
   - Both models will provide responses with reasoning and answers
   - Vote for the better response using the "Vote Best" button

3. **Export the data**:
   - The voting data is stored in your browser's localStorage
   - You can access this data in the browser console with:
     ```javascript
     const modelConfig = JSON.parse(localStorage.getItem('modelConfig'));
     const chatState = JSON.parse(localStorage.getItem('chatState'));
     console.log({modelConfig, chatState});
     ```

4. **Extract and format for additional fine-tuning**:
   ```bash
   python extract_from_webapp.py --input_file exported_data.json --output_file additional_sft_data.jsonl
   ```
   This extracts the winning responses and formats them for additional fine-tuning.

## API Keys

- OpenAI API keys can be obtained from [OpenAI's platform](https://platform.openai.com/api-keys)
- Anthropic API keys can be obtained from [Anthropic's console](https://console.anthropic.com/)
- API keys are stored only in your browser's localStorage and are never sent to any server other than the respective API providers
