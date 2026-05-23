/**
 * OpenRouter AI Integration
 * Free Gemma 4 31B model via OpenRouter
 * 
 * NO API KEY REQUIRED - Using free tier
 */

export interface FraudSignal {
  id: string;
  name: string;
  severity: 'high' | 'medium' | 'low';
  summary: string;
  description: string;
  evidence: string[];
  confidence: number;
  highlight_values: string[];
}

export interface AIExplanation {
  summary: string;
  likely_alteration: string;
  recommended_action: string;
}

export interface FraudAnalysisResult {
  risk_score: number;
  trust_score: number;
  fraud_signals: FraudSignal[];
  ai_explanation: AIExplanation;
}

/**
 * Analyze document for fraud using OpenRouter's free Gemma 4 31B model
 */
export async function analyzeDocumentWithAI(
  documentContext: {
    file_name: string;
    file_type: string;
    metadata: any;
    forensic_data: any;
    text_sample: string;
  },
  apiKey?: string
): Promise<FraudAnalysisResult> {
  const systemPrompt = `You are a fraud detection AI. Analyze documents and return JSON.

Return ONLY valid JSON with this structure:
{
  "risk_score": 75.0,
  "trust_score": 25.0,
  "fraud_signals": [
    {
      "id": "signal-1",
      "name": "Signal Name",
      "severity": "high",
      "summary": "Brief summary",
      "description": "Detailed explanation in 1-2 sentences.",
      "evidence": ["Evidence 1", "Evidence 2"],
      "confidence": 0.9,
      "highlight_values": ["$1000", "2024-01-15"]
    }
  ],
  "ai_explanation": {
    "summary": "Brief overview in 1-2 sentences.",
    "likely_alteration": "What was altered.",
    "recommended_action": "accept or reject"
  }
}

Rules:
- risk_score + trust_score = 100
- Include 3-7 fraud signals
- highlight_values = specific suspicious values only
- Be thorough and accurate in your analysis
- Provide detailed evidence for each signal`;

  const userPrompt = `Analyze for fraud and return JSON:\n\n${JSON.stringify(documentContext, null, 2)}`;

  try {
    console.log('[OPENROUTER] Calling Gemma 4 31B via OpenRouter...');
    console.log('[OPENROUTER] Document context:', documentContext);
    console.log('[OPENROUTER] Using API key:', apiKey ? 'Yes (custom)' : 'No (free tier)');
    
    // Build headers
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'HTTP-Referer': window.location.origin,
      'X-Title': 'Fraud Detection System',
    };
    
    // Add API key if provided
    if (apiKey) {
      headers['Authorization'] = `Bearer ${apiKey}`;
    }
    
    // Call OpenRouter API with free Gemma 4 31B model
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: 'google/gemma-4-31b-it:free',
        messages: [
          {
            role: 'system',
            content: systemPrompt
          },
          {
            role: 'user',
            content: userPrompt
          }
        ],
        temperature: 0.1, // Low temperature for accuracy
        max_tokens: 4000,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[OPENROUTER] API Error:', response.status, errorText);
      throw new Error(`OpenRouter API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('[OPENROUTER] Received response:', data);

    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error('No content in OpenRouter response');
    }

    console.log('[OPENROUTER] Response content:', content);
    
    // Try to extract JSON from markdown code blocks
    let jsonStr = content;
    const jsonMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
    if (jsonMatch) {
      jsonStr = jsonMatch[1];
    } else {
      // Try to find JSON object
      const objMatch = content.match(/\{[\s\S]*\}/);
      if (objMatch) {
        jsonStr = objMatch[0];
      }
    }

    console.log('[OPENROUTER] Extracted JSON string:', jsonStr);
    const result = JSON.parse(jsonStr);

    // Validate structure
    if (!result.risk_score || !result.trust_score || !result.fraud_signals || !result.ai_explanation) {
      throw new Error('Invalid response structure from AI');
    }

    console.log('[OPENROUTER] Analysis complete:', result.fraud_signals.length, 'signals');

    return result;
  } catch (error) {
    console.error('[OPENROUTER] Error analyzing document:', error);
    console.error('[OPENROUTER] Error details:', error instanceof Error ? error.message : String(error));
    
    // Provide helpful error messages
    if (error instanceof Error) {
      if (error.message.includes('rate limit') || error.message.includes('429')) {
        throw new Error('Rate limit reached. Please wait a moment and try again.');
      }
      if (error.message.includes('model')) {
        throw new Error('AI model not available. Please try again later.');
      }
    }
    
    throw error;
  }
}
