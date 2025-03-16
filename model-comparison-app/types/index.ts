export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  model?: string;
}

export interface ChatState {
  messages: Message[];
  modelAResponses: Message[];
  modelBResponses: Message[];
  isLoading: boolean;
  votes: Vote[];
}

export interface ModelConfig {
  modelA: string;
  modelB: string;
  openaiKey: string;
  anthropicKey?: string;
}

export interface Vote {
  messageIndex: number;
  winner: 'A' | 'B';
}

export interface VoteStats {
  modelA: {
    wins: number;
    winRate: number;
  };
  modelB: {
    wins: number;
    winRate: number;
  };
}

export const availableModels = [
  { value: 'ft:gpt-4o-2024-08-06:personal::BB3cCJ1L', label: 'Fine-tuned GPT-4o' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'claude-3-7-sonnet-20240307', label: 'Claude 3.7 Sonnet' },
  // Add your fine-tuned model here
]; 