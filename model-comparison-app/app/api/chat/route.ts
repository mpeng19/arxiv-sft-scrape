import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';

export async function POST(req: NextRequest) {
  try {
    const { message, modelA, modelB, openaiKey, anthropicKey } = await req.json();

    console.log('API request received:', {
      message: message.substring(0, 50) + (message.length > 50 ? '...' : ''),
      modelA,
      modelB,
      hasOpenAIKey: !!openaiKey,
      hasAnthropicKey: !!anthropicKey,
    });

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    if (!modelA || !modelB) {
      return NextResponse.json(
        { error: 'Both models must be specified' },
        { status: 400 }
      );
    }

    // Check if OpenAI key is provided for OpenAI models
    if ((modelA.includes('gpt') || modelA.includes('ft:')) && !openaiKey) {
      return NextResponse.json(
        { error: 'OpenAI API key is required for model A' },
        { status: 400 }
      );
    }

    if ((modelB.includes('gpt') || modelB.includes('ft:')) && !openaiKey) {
      return NextResponse.json(
        { error: 'OpenAI API key is required for model B' },
        { status: 400 }
      );
    }

    // Check if Anthropic key is provided for Claude models
    if (modelA.includes('claude') && !anthropicKey) {
      return NextResponse.json(
        { error: 'Anthropic API key is required for model A' },
        { status: 400 }
      );
    }

    if (modelB.includes('claude') && !anthropicKey) {
      return NextResponse.json(
        { error: 'Anthropic API key is required for model B' },
        { status: 400 }
      );
    }

    const responses = await Promise.all([
      getModelResponse(message, modelA, openaiKey, anthropicKey),
      getModelResponse(message, modelB, openaiKey, anthropicKey)
    ]);

    return NextResponse.json({
      modelAResponse: responses[0],
      modelBResponse: responses[1]
    });
  } catch (error) {
    console.error('Error in chat API:', error);
    return NextResponse.json(
      { error: 'Failed to process request', details: (error as Error).message },
      { status: 500 }
    );
  }
}

async function getModelResponse(
  message: string,
  model: string,
  openaiKey?: string,
  anthropicKey?: string
): Promise<string> {
  const systemPrompt = `
Respond in the following format:
<reasoning>
Your step-by-step reasoning process here
</reasoning>
<answer>
Your final answer here
</answer>

Important guidelines for LaTeX formatting:
1. Always use the <reasoning> and <answer> tags in your response.
2. Always use LaTeX syntax for mathematical expressions:
   - Use $ for inline math: $x^2$, $\\alpha$, $\\frac{a}{b}$
   - Use $$ for display math: $$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$
3. Format all mathematical expressions properly with LaTeX:
   - Variables and single letters should be in LaTeX: $x$, $n$, $\\alpha$
   - Equations must be in LaTeX: $x^2 + 2x + 1 = 0$
   - Fractions should use \\frac: $\\frac{a}{b}$
   - Use proper LaTeX symbols for operations: $\\times$, $\\div$, $\\cdot$
4. Ensure all backslashes in LaTeX expressions are properly escaped (use \\\\ instead of \\).
5. Keep your answers concise and to the point.
`;

  try {
    if (model.includes('gpt') || model.includes('ft:')) {
      if (!openaiKey) {
        return "Error: OpenAI API key is required for this model.";
      }
      
      console.log(`Sending request to OpenAI model: ${model}`);
      const openai = new OpenAI({ apiKey: openaiKey });
      
      try {
        const response = await openai.chat.completions.create({
          model: model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: message }
          ],
          temperature: 0.2,
          max_tokens: 2000
        });

        let content = response.choices[0].message.content || "No response generated";
        
        // Ensure the response has the required tags
        if (!content.includes('<reasoning>') && !content.includes('<answer>')) {
          content = `<reasoning>\nThe model did not provide explicit reasoning.\n</reasoning>\n<answer>\n${content}\n</answer>`;
        } else if (!content.includes('<reasoning>')) {
          const answerStart = content.indexOf('<answer>');
          const beforeAnswer = content.substring(0, answerStart).trim();
          content = `<reasoning>\n${beforeAnswer || 'The model did not provide explicit reasoning.'}\n</reasoning>\n` + content.substring(answerStart);
        } else if (!content.includes('<answer>')) {
          const reasoningEnd = content.indexOf('</reasoning>');
          const afterReasoning = content.substring(reasoningEnd + 11).trim();
          content = content.substring(0, reasoningEnd + 11) + `\n<answer>\n${afterReasoning || 'The model did not provide an explicit answer.'}\n</answer>`;
        }
        
        return content;
      } catch (openaiError) {
        console.error(`OpenAI API error for model ${model}:`, openaiError);
        return `Error: ${(openaiError as Error).message}`;
      }
    } 
    else if (model.includes('claude')) {
      if (!anthropicKey) {
        return "Error: Anthropic API key is required for this model.";
      }
      
      console.log(`Sending request to Anthropic model: ${model}`);
      const anthropic = new Anthropic({ apiKey: anthropicKey });
      
      try {
        const response = await anthropic.messages.create({
          model: model,
          system: systemPrompt,
          messages: [
            { role: "user", content: message }
          ],
          max_tokens: 2000
        });
        
        let content = '';
        if (response.content[0].type === 'text') {
          content = response.content[0].text;
        }
        
        // Ensure the response has the required tags
        if (!content.includes('<reasoning>') && !content.includes('<answer>')) {
          content = `<reasoning>\nThe model did not provide explicit reasoning.\n</reasoning>\n<answer>\n${content}\n</answer>`;
        } else if (!content.includes('<reasoning>')) {
          const answerStart = content.indexOf('<answer>');
          const beforeAnswer = content.substring(0, answerStart).trim();
          content = `<reasoning>\n${beforeAnswer || 'The model did not provide explicit reasoning.'}\n</reasoning>\n` + content.substring(answerStart);
        } else if (!content.includes('<answer>')) {
          const reasoningEnd = content.indexOf('</reasoning>');
          const afterReasoning = content.substring(reasoningEnd + 11).trim();
          content = content.substring(0, reasoningEnd + 11) + `\n<answer>\n${afterReasoning || 'The model did not provide an explicit answer.'}\n</answer>`;
        }
        
        return content;
      } catch (anthropicError) {
        console.error(`Anthropic API error for model ${model}:`, anthropicError);
        return `Error: ${(anthropicError as Error).message}`;
      }
    } 
    else {
      return `Error: Unsupported model: ${model}`;
    }
  } catch (error) {
    console.error(`Error getting response from ${model}:`, error);
    return `Error: Failed to get response from ${model}. ${(error as Error).message}`;
  }
} 