/**
 * Puter.js AI Integration for Browser
 * Free, unlimited AI analysis in the browser using Puter's User-Pays model
 * 
 * NO API KEYS REQUIRED - Users authenticate with their own Puter account
 */

declare global {
  interface Window {
    puter: any;
  }
}

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
 * Check if Puter.js is available
 */
export function isPuterAvailable(): boolean {
  return typeof window !== 'undefined' && typeof window.puter !== 'undefined';
}

/**
 * Analyze document for fraud using Puter.js AI (runs in browser)
 */
export async function analyzeDocumentWithPuter(
  documentContext: {
    file_name: string;
    file_type: string;
    metadata: any;
    forensic_data: any;
    text_sample: string;
  }
): Promise<FraudAnalysisResult> {
  if (!isPuterAvailable()) {
    throw new Error('Puter.js is not loaded. Please refresh the page.');
  }

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
    console.log('[PUTER] Calling Gemma4 via Puter.js in browser...');
    
    // Call Puter AI with Gemma4 31B model (most accurate, not fast model)
    // DO NOT use fast models - accuracy is critical for fraud detection
    const response = await window.puter.ai.chat(
      `${systemPrompt}\n\n${userPrompt}`,
      {
        model: 'google/gemma-4-31b-it', // Gemma4 31B - Most accurate model
        temperature: 0.3, // Lower temperature for more accurate, deterministic results
      }
    );

    console.log('[PUTER] Received response from Gemma');

    // Extract JSON from response
    const content = response.message?.content || response;
    
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

    const result = JSON.parse(jsonStr);

    // Validate structure
    if (!result.risk_score || !result.trust_score || !result.fraud_signals || !result.ai_explanation) {
      throw new Error('Invalid response structure from AI');
    }

    console.log('[PUTER] Analysis complete:', result.fraud_signals.length, 'signals');

    return result;
  } catch (error) {
    console.error('[PUTER] Error analyzing document:', error);
    throw error;
  }
}

/**
 * Initialize Puter (optional - for authentication)
 */
export async function initializePuter(): Promise<void> {
  if (!isPuterAvailable()) {
    throw new Error('Puter.js is not loaded');
  }

  try {
    // Puter handles authentication automatically
    // Users will be prompted to sign in when they first use AI
    console.log('[PUTER] Puter.js initialized');
  } catch (error) {
    console.error('[PUTER] Failed to initialize:', error);
    throw error;
  }
}
