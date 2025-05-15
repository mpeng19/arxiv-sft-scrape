'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { availableModels, ModelConfig } from '@/types';
import { ThemeToggle } from '@/components/theme-toggle';

const formSchema = z.object({
  modelA: z.string().min(1, 'Model A is required'),
  modelB: z.string().min(1, 'Model B is required'),
  customModelA: z.string().optional(),
  customModelB: z.string().optional(),
  openaiKey: z.string().optional(),
  anthropicKey: z.string().optional(),
});

export default function Home() {
  const router = useRouter();
  
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      modelA: '',
      modelB: '',
      customModelA: '',
      customModelB: '',
      openaiKey: '',
      anthropicKey: '',
    },
  });

  //Load saved values from localStorage on initial render
  useEffect(() => {
    const savedConfig = localStorage.getItem('modelConfig');
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig) as ModelConfig;
        form.setValue('modelA', config.modelA);
        form.setValue('modelB', config.modelB);
        
        if (!availableModels.some(model => model.value === config.modelA)) {
          form.setValue('customModelA', config.modelA);
          form.setValue('modelA', 'custom');
        }
        
        if (!availableModels.some(model => model.value === config.modelB)) {
          form.setValue('customModelB', config.modelB);
          form.setValue('modelB', 'custom');
        }
        
        if (config.openaiKey) {
          form.setValue('openaiKey', config.openaiKey);
        }
        
        if (config.anthropicKey) {
          form.setValue('anthropicKey', config.anthropicKey);
        }
      } catch (error) {
        console.error('Failed to parse saved config:', error);
      }
    }
  }, [form]);

  const onSubmit = (values: z.infer<typeof formSchema>) => {
    const modelConfig: ModelConfig = {
      modelA: values.modelA === 'custom' ? values.customModelA! : values.modelA,
      modelB: values.modelB === 'custom' ? values.customModelB! : values.modelB,
      openaiKey: values.openaiKey || '',
      anthropicKey: values.anthropicKey || '',
    };

    localStorage.setItem('modelConfig', JSON.stringify(modelConfig));
    router.push('/chat');
  };

  const selectedModelA = form.watch('modelA');
  const selectedModelB = form.watch('modelB');
  
  const modelBOptions = availableModels.filter(model => 
    model.value !== (selectedModelA === 'custom' ? form.watch('customModelA') : selectedModelA)
  );
  
  const modelAOptions = availableModels.filter(model => 
    model.value !== (selectedModelB === 'custom' ? form.watch('customModelB') : selectedModelB)
  );

  return (
    <div className="container mx-auto p-4 max-w-2xl">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Model Comparison</h1>
        <ThemeToggle />
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>Select Models</CardTitle>
          <CardDescription>
            Choose two models to compare and provide API keys.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="modelA"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Model A</FormLabel>
                      <Select 
                        onValueChange={field.onChange} 
                        defaultValue={field.value}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select Model A" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                           {modelAOptions.map((model) => (
                             <SelectItem key={model.value} value={model.value}>
                              {model.label}
                            </SelectItem>
                          ))}
                           <SelectItem value="custom">Custom Model</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                 
                 {form.watch('modelA') === 'custom' && (
                   <FormField
                     control={form.control}
                     name="customModelA"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>Custom Model A ID</FormLabel>
                         <FormControl>
                           <Input placeholder="Enter model ID" {...field} />
                         </FormControl>
                         <FormDescription>
                           Enter the full model ID (e.g., ft:gpt-4o-2024-08-06:personal::BB3cCJ1L)
                         </FormDescription>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                 )}
                
                <FormField
                  control={form.control}
                  name="modelB"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Model B</FormLabel>
                      <Select 
                        onValueChange={field.onChange} 
                        defaultValue={field.value}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select Model B" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                           {modelBOptions.map((model) => (
                             <SelectItem key={model.value} value={model.value}>
                              {model.label}
                            </SelectItem>
                          ))}
                           <SelectItem value="custom">Custom Model</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                 {form.watch('modelB') === 'custom' && (
                   <FormField
                     control={form.control}
                     name="customModelB"
                     render={({ field }) => (
                       <FormItem>
                         <FormLabel>Custom Model B ID</FormLabel>
                         <FormControl>
                           <Input placeholder="Enter model ID" {...field} />
                         </FormControl>
                         <FormDescription>
                           Enter the full model ID (e.g., ft:gpt-4o-2024-08-06:personal::BB3cCJ1L)
                         </FormDescription>
                         <FormMessage />
                       </FormItem>
                     )}
                   />
                 )}
                 
                 <div className="pt-4 border-t">
                   <h3 className="text-lg font-medium mb-4">API Keys</h3>
                   
                   <div className="space-y-4">
                <FormField
                  control={form.control}
                  name="openaiKey"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>OpenAI API Key</FormLabel>
                      <FormControl>
                             <Input 
                               type="password" 
                               placeholder="sk-..." 
                               {...field} 
                             />
                      </FormControl>
                      <FormDescription>
                             Required for OpenAI models. Your API key is stored locally.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                
                <FormField
                  control={form.control}
                  name="anthropicKey"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Anthropic API Key</FormLabel>
                      <FormControl>
                             <Input 
                               type="password" 
                               placeholder="sk-ant-..." 
                               {...field} 
                             />
                      </FormControl>
                      <FormDescription>
                             Required for Claude models. Your API key is stored locally.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                   </div>
                 </div>
              </div>
                
               <Button type="submit" className="w-full cursor-pointer">
                 Start Comparison
               </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
