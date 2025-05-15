import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';

export async function POST(req: NextRequest) {
  try {
    const { provider, apiKey } = await req.json();
    
    if (!provider || !apiKey) {
      return NextResponse.json(
        { error: 'Provider and API key are required' },
        { status: 400 }
      );
    }
    
    let credits = '';
    
    if (provider === 'openai') {
      try {
        const openai = new OpenAI({ apiKey });
        //Check billing info for credits
        const response = await fetch('https://api.openai.com/dashboard/billing/credit_grants', {
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          credits = `$${data.total_available.toFixed(2)}`;
        } else {
          //Fallback; check organization info
          const orgResponse = await openai.organizations.list();
          if (orgResponse.data && orgResponse.data.length > 0) {
            credits = 'API key valid, but credits info unavailable';
          } else {
            throw new Error('Could not verify API key');
          }
        }
      } catch (error) {
        console.error('Error checking OpenAI credits:', error);
        return NextResponse.json(
          { error: 'Failed to check OpenAI credits', details: (error as Error).message },
          { status: 500 }
        );
      }
    } else if (provider === 'anthropic') {
      try {
        const anthropic = new Anthropic({ apiKey });
        const response = await fetch('https://api.anthropic.com/v1/models', {
          headers: {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01'
          }
        });
        
        if (response.ok) {
          credits = 'API key valid, credits info unavailable';
        } else {
          throw new Error('Invalid API key');
        }
      } catch (error) {
        console.error('Error checking Anthropic credits:', error);
        return NextResponse.json(
          { error: 'Failed to check Anthropic credits', details: (error as Error).message },
          { status: 500 }
        );
      }
    } else {
      return NextResponse.json(
        { error: 'Unsupported provider' },
        { status: 400 }
      );
    }
    
    return NextResponse.json({ credits });
  } catch (error) {
    console.error('Error in check-credits API:', error);
    return NextResponse.json(
      { error: 'Failed to process request', details: (error as Error).message },
      { status: 500 }
    );
  }
} 