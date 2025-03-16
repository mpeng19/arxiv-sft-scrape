'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Toaster } from '@/components/ui/sonner';
import { toast } from 'sonner';
import { ChatState, Message, ModelConfig, Vote, VoteStats } from '@/types';
import { ThemeToggle } from '@/components/theme-toggle';
import { ThumbsUp } from 'lucide-react';
import 'katex/dist/katex.min.css';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export default function ChatPage() {
  const router = useRouter();
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    modelAResponses: [],
    modelBResponses: [],
    isLoading: false,
    votes: [],
  });
  const [input, setInput] = useState('');
  const [voteStats, setVoteStats] = useState<VoteStats>({
    modelA: { wins: 0, winRate: 0 },
    modelB: { wins: 0, winRate: 0 },
  });
  const responsesContainerRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  useEffect(() => {
    const storedConfig = localStorage.getItem('modelConfig');
    if (!storedConfig) {
      router.push('/');
      return;
    }

    try {
      const parsedConfig = JSON.parse(storedConfig) as ModelConfig;
      setConfig(parsedConfig);
    } catch (error) {
      console.error('Failed to parse model configuration:', error);
      router.push('/');
    }
  }, [router]);

  useEffect(() => {
    if (chatState.votes.length === 0) {
      setVoteStats({
        modelA: { wins: 0, winRate: 0 },
        modelB: { wins: 0, winRate: 0 },
      });
      return;
    }

    const modelAWins = chatState.votes.filter(vote => vote.winner === 'A').length;
    const modelBWins = chatState.votes.filter(vote => vote.winner === 'B').length;
    const totalVotes = chatState.votes.length;

    setVoteStats({
      modelA: {
        wins: modelAWins,
        winRate: Math.round((modelAWins / totalVotes) * 100),
      },
      modelB: {
        wins: modelBWins,
        winRate: Math.round((modelBWins / totalVotes) * 100),
      },
    });
  }, [chatState.votes]);

  useEffect(() => {
    const container = responsesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => {
        container.removeEventListener('scroll', handleScroll);
      };
    }
  }, []);

  const handleScroll = () => {
    if (responsesContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = responsesContainerRef.current;
      const isAtBottom = scrollHeight - scrollTop <= clientHeight + 100;
      
      if (!isAtBottom) {
        setUserScrolled(true);
      } else {
        setUserScrolled(false);
      }
    }
  };

  useEffect(() => {
    if (chatState.messages.length > 0 && !userScrolled) {
      const timeoutId = setTimeout(() => {
        const container = responsesContainerRef.current;
        if (container) {
          const isAtBottom = 
            container.scrollHeight - container.scrollTop <= 
            container.clientHeight + 100;
          
          if (isAtBottom || chatState.isLoading === false) {
            container.scrollTop = container.scrollHeight;
            
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
          }
        }
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [chatState.messages, chatState.modelAResponses, chatState.modelBResponses, chatState.isLoading, userScrolled]);

  const scrollResponsesContainerToBottom = () => {
    if (responsesContainerRef.current) {
      responsesContainerRef.current.scrollTop = responsesContainerRef.current.scrollHeight;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!input.trim() || !config) return;
    
    setUserScrolled(false);
    
    const userMessage: Message = { role: 'user', content: input };
    const messageIndex = chatState.messages.length;
    
    setChatState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
    }));
    
    setInput('');
    
    setTimeout(() => {
      if (responsesContainerRef.current) {
        responsesContainerRef.current.scrollTop = responsesContainerRef.current.scrollHeight;
      }
    }, 50);
    
    try {
      console.log('Sending request with:', {
        message: input,
        modelA: config.modelA,
        modelB: config.modelB,
        openaiKey: config.openaiKey ? '***' : undefined,
        anthropicKey: config.anthropicKey ? '***' : undefined,
      });
      
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input,
          modelA: config.modelA,
          modelB: config.modelB,
          openaiKey: config.openaiKey,
          anthropicKey: config.anthropicKey,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('API response error:', response.status, errorData);
        throw new Error(`Failed to get model responses: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Received responses:', {
        modelAResponse: data.modelAResponse?.substring(0, 50) + '...',
        modelBResponse: data.modelBResponse?.substring(0, 50) + '...',
      });
      
      const modelAMessage: Message = { 
        role: 'assistant', 
        content: data.modelAResponse,
        model: config.modelA
      };
      
      const modelBMessage: Message = { 
        role: 'assistant', 
        content: data.modelBResponse,
        model: config.modelB
      };
      
      setChatState((prev) => ({
        ...prev,
        modelAResponses: [...prev.modelAResponses, modelAMessage],
        modelBResponses: [...prev.modelBResponses, modelBMessage],
        isLoading: false,
      }));
      
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to get model responses. Please try again.');
      setChatState((prev) => ({ ...prev, isLoading: false }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleVote = (messageIndex: number, winner: 'A' | 'B') => {
    const existingVoteIndex = chatState.votes.findIndex(v => v.messageIndex === messageIndex);
    
    if (existingVoteIndex !== -1) {
      const updatedVotes = [...chatState.votes];
      updatedVotes[existingVoteIndex] = { messageIndex, winner };
      
      setChatState(prev => ({
        ...prev,
        votes: updatedVotes
      }));
      
      toast.success(`Changed vote to Model ${winner}`);
    } else {
      setChatState(prev => ({
        ...prev,
        votes: [...prev.votes, { messageIndex, winner }]
      }));
      
      toast.success(`Voted for Model ${winner}`);
    }
  };

  const getVoteForMessage = (messageIndex: number): 'A' | 'B' | null => {
    const vote = chatState.votes.find(v => v.messageIndex === messageIndex);
    return vote ? vote.winner : null;
  };

  const extractContent = (content: string, tag: string): string => {
    const regex = new RegExp(`<${tag}>([\\\s\\\S]*?)<\/${tag}>`, 'g');
    const match = regex.exec(content);
    
    if (match) {
      return match[1].trim();
    }
    
    if (tag === 'reasoning' && !content.includes('<reasoning>') && !content.includes('<answer>')) {
      return '';
    } else if (tag === 'answer' && !content.includes('<reasoning>') && !content.includes('<answer>')) {
      return content.trim();
    } else if (tag === 'reasoning' && !content.includes('<reasoning>') && content.includes('<answer>')) {
      const answerStart = content.indexOf('<answer>');
      return content.substring(0, answerStart).trim();
    } else if (tag === 'answer' && content.includes('<reasoning>') && !content.includes('<answer>')) {
      const reasoningEnd = content.indexOf('</reasoning>');
      return reasoningEnd !== -1 ? content.substring(reasoningEnd + 11).trim() : '';
    }
    
    return '';
  };

  const processContent = (content: string): string => {
    if (!content) return '';
    
    if (content.includes('$') && content.includes('\\')) {
      return content;
    }
    
    let processed = content;
    
    processed = processed.replace(/\\\\([a-zA-Z]+)/g, '\\$1');
    processed = processed.replace(/([^$])(\\?[a-zA-Z]+\([a-zA-Z0-9]+\))([^$])/g, '$1$$$2$$$3');
    processed = processed.replace(/([^$])([a-zA-Z])(\^[0-9]+)([^$])/g, '$1$$$2$3$$$4');
    processed = processed.replace(/([^$])([a-zA-Z])(_[0-9]+)([^$])/g, '$1$$$2$3$$$4');
    
    processed = processed.replace(/\$([^$]*)\$/g, (match) => {
      return match.trim();
    });
    
    return processed;
  };

  if (!config) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <div className="container mx-auto p-4 max-w-6xl h-screen overflow-hidden flex flex-col">
      <Toaster />
      <div className="flex flex-col h-full">
        <header className="py-4 border-b flex-shrink-0">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold">Model Comparison</h1>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button variant="outline" onClick={() => router.push('/')}>
                Change Models
              </Button>
            </div>
          </div>
          <div className="flex gap-4 mt-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">Model A:</span> 
              <span className="text-muted-foreground">{config.modelA}</span>
              {voteStats.modelA.wins > 0 && (
                <span className="bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-100 px-2 py-0.5 rounded-full text-xs">
                  {voteStats.modelA.winRate}% win rate ({voteStats.modelA.wins} votes)
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="font-medium">Model B:</span> 
              <span className="text-muted-foreground">{config.modelB}</span>
              {voteStats.modelB.wins > 0 && (
                <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-100 px-2 py-0.5 rounded-full text-xs">
                  {voteStats.modelB.winRate}% win rate ({voteStats.modelB.wins} votes)
                </span>
              )}
            </div>
          </div>
        </header>
        
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto py-4 space-y-4 max-h-[calc(100vh-200px)] scrollable-content" ref={responsesContainerRef}>
            {chatState.messages.length === 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="py-2">
                    <CardTitle className="text-sm font-medium">Model A: {config.modelA}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-20 flex items-center justify-center text-muted-foreground">
                      Enter a prompt to see the response
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="py-2">
                    <CardTitle className="text-sm font-medium">Model B: {config.modelB}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="h-20 flex items-center justify-center text-muted-foreground">
                      Enter a prompt to see the response
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            
            {chatState.messages.map((message, i) => (
              <div key={i} className="flex flex-col gap-4">
                <div className="bg-muted p-4 rounded-lg max-w-[80%] self-end">
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      code: ({className, children, ...props}: any) => {
                        const match = /language-(\w+)/.exec(className || '');
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        );
                      }
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {chatState.modelAResponses[i] && (
                    <Card className={getVoteForMessage(i) === 'A' ? 'border-2 border-green-500 dark:border-green-400' : ''}>
                      <CardHeader className="py-2">
                        <CardTitle className="text-sm font-medium">Model A: {config.modelA}</CardTitle>
                      </CardHeader>
                      <CardContent className="markdown-wrapper">
                        <div className="bg-muted/50 p-3 rounded-md my-2">
                          <strong>Reasoning:</strong>
                          <div className="markdown-content">
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                              components={{
                                code: ({className, children, ...props}: any) => {
                                  const match = /language-(\w+)/.exec(className || '');
                                  return (
                                    <code className={className} {...props}>
                                      {children}
                                    </code>
                                  );
                                }
                              }}
                            >
                              {processContent(extractContent(chatState.modelAResponses[i].content, 'reasoning'))}
                            </ReactMarkdown>
                          </div>
                        </div>
                        <div className="bg-primary/10 p-3 rounded-md my-2 border-l-4 border-primary">
                          <strong>Answer:</strong>
                          <div className="markdown-content">
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                              components={{
                                code: ({className, children, ...props}: any) => {
                                  const match = /language-(\w+)/.exec(className || '');
                                  return (
                                    <code className={className} {...props}>
                                      {children}
                                    </code>
                                  );
                                }
                              }}
                            >
                              {processContent(extractContent(chatState.modelAResponses[i].content, 'answer'))}
                            </ReactMarkdown>
                          </div>
                        </div>
                      </CardContent>
                      <CardFooter className="pt-2 pb-4 flex justify-center">
                        <Button 
                          variant={getVoteForMessage(i) === 'A' ? 'default' : 'outline'} 
                          size="sm"
                          onClick={() => handleVote(i, 'A')}
                          className="gap-2"
                        >
                          <ThumbsUp className="h-4 w-4" />
                          {getVoteForMessage(i) === 'A' ? 'Voted Best' : 'Vote Best'}
                        </Button>
                      </CardFooter>
                    </Card>
                  )}
                  
                  {chatState.modelBResponses[i] && (
                    <Card className={getVoteForMessage(i) === 'B' ? 'border-2 border-blue-500 dark:border-blue-400' : ''}>
                      <CardHeader className="py-2">
                        <CardTitle className="text-sm font-medium">Model B: {config.modelB}</CardTitle>
                      </CardHeader>
                      <CardContent className="markdown-wrapper">
                        <div className="bg-muted/50 p-3 rounded-md my-2">
                          <strong>Reasoning:</strong>
                          <div className="markdown-content">
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                              components={{
                                code: ({className, children, ...props}: any) => {
                                  const match = /language-(\w+)/.exec(className || '');
                                  return (
                                    <code className={className} {...props}>
                                      {children}
                                    </code>
                                  );
                                }
                              }}
                            >
                              {processContent(extractContent(chatState.modelBResponses[i].content, 'reasoning'))}
                            </ReactMarkdown>
                          </div>
                        </div>
                        <div className="bg-primary/10 p-3 rounded-md my-2 border-l-4 border-primary">
                          <strong>Answer:</strong>
                          <div className="markdown-content">
                            <ReactMarkdown
                              remarkPlugins={[remarkMath]}
                              rehypePlugins={[rehypeKatex]}
                              components={{
                                code: ({className, children, ...props}: any) => {
                                  const match = /language-(\w+)/.exec(className || '');
                                  return (
                                    <code className={className} {...props}>
                                      {children}
                                    </code>
                                  );
                                }
                              }}
                            >
                              {processContent(extractContent(chatState.modelBResponses[i].content, 'answer'))}
                            </ReactMarkdown>
                          </div>
                        </div>
                      </CardContent>
                      <CardFooter className="pt-2 pb-4 flex justify-center">
                        <Button 
                          variant={getVoteForMessage(i) === 'B' ? 'default' : 'outline'} 
                          size="sm"
                          onClick={() => handleVote(i, 'B')}
                          className="gap-2"
                        >
                          <ThumbsUp className="h-4 w-4" />
                          {getVoteForMessage(i) === 'B' ? 'Voted Best' : 'Vote Best'}
                        </Button>
                      </CardFooter>
                    </Card>
                  )}
                </div>
              </div>
            ))}
            
            {chatState.isLoading && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="h-20 flex items-center justify-center">
                      <div className="animate-pulse">Loading response from Model A...</div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="h-20 flex items-center justify-center">
                      <div className="animate-pulse">Loading response from Model B...</div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
          
          <form onSubmit={handleSubmit} className="py-4 border-t flex-shrink-0 mt-auto">
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                className="flex-1 min-h-24 max-h-24"
                disabled={chatState.isLoading}
              />
              <Button type="submit" disabled={chatState.isLoading || !input.trim()}>
                {chatState.isLoading ? 'Sending...' : 'Send'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
} 