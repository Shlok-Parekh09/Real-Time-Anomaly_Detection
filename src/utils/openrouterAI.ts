/**
 * OpenRouter AI Integration
 * Model: google/gemma-4-31b-it:free
 *
 * API key is REQUIRED — user provides it via the top bar.
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

const SYSTEM_PROMPT = `You are a fraud detection AI specialising in document forensics.
Analyse the provided document context and return ONLY valid JSON — no markdown, no preamble.

Required JSON structure:
{
  "risk_score": 75.0,
  "trust_score": 25.0,
  "fraud_signals": [
    {
      "id": "signal-1",
      "name": "Signal Name",
      "severity": "high",
      "summary": "One-line summary",
      "description": "Detailed explanation in 1-2 sentences.",
      "evidence": ["Evidence item 1", "Evidence item 2"],
      "confidence": 0.9,
      "highlight_values": ["suspicious value", "another value"]
    }
  ],
  "ai_explanation": {
    "summary": "Overall assessment in 1-2 sentences.",
    "likely_alteration": "What was most likely altered or fabricated.",
    "recommended_action": "accept or reject"
  }
}

Rules:
- risk_score + trust_score must equal 100
- Include 3-7 fraud signals covering different aspects
- highlight_values must be specific strings found in the document
- Severity: high = likely fraud, medium = suspicious, low = minor anomaly
- Be thorough; justify each signal with concrete evidence`;

/**
 * Analyze document for fraud using OpenRouter's Gemma 4 31B model.
 * @param documentContext  Context extracted by the backend
 * @param apiKey           OpenRouter API key (required)
 */
export async function analyzeDocumentWithAI(
  documentContext: {
    file_name: string;
    file_type: string;
    metadata: any;
    forensic_data: any;
    text_sample: string;
    image_base64?: string;
  },
  apiKey: string | undefined
): Promise<FraudAnalysisResult> {
  if (!apiKey?.trim()) {
    throw new Error('OpenRouter API key is required for browser-side AI analysis.');
  }

  // Build the user message — include image inline if available
  const contextForAI = {
    file_name: documentContext.file_name,
    file_type: documentContext.file_type,
    metadata: documentContext.metadata,
    forensic_data: documentContext.forensic_data,
    text_sample: documentContext.text_sample,
  };

  // Build message content — multimodal for images
  let userContent: any;
  if (documentContext.file_type === 'image' && documentContext.image_base64) {
    userContent = [
      {
        type: 'text',
        text: `Analyze this document image for fraud. Context:\n${JSON.stringify(contextForAI, null, 2)}\n\nReturn ONLY the JSON fraud analysis.`,
      },
      {
        type: 'image_url',
        image_url: {
          url: `data:image/jpeg;base64,${documentContext.image_base64}`,
        },
      },
    ];
  } else {
    userContent = `Analyze for fraud and return ONLY JSON:\n\n${JSON.stringify(contextForAI, null, 2)}`;
  }

  console.log('[OPENROUTER] Calling google/gemma-4-31b-it:free...');

  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey.trim()}`,
        'HTTP-Referer': window.location.origin,
        'X-Title': 'Fraud Detection System',
      },
      body: JSON.stringify({
        model: 'google/gemma-4-31b-it:free',
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'user',   content: userContent },
        ],
        temperature: 0.1,
        max_tokens: 4000,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[OPENROUTER] Error:', response.status, errorText);
      throw new Error(`OpenRouter API error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const content: string | undefined = data.choices?.[0]?.message?.content;

    if (!content) {
      throw new Error('Empty response from OpenRouter.');
    }

    console.log('[OPENROUTER] Raw response:', content.slice(0, 300));

    // Extract JSON — handle markdown fences or raw objects
    let jsonStr = content.trim();
    const fenceMatch = content.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
    if (fenceMatch) {
      jsonStr = fenceMatch[1];
    } else {
      const objMatch = content.match(/\{[\s\S]*\}/);
      if (objMatch) jsonStr = objMatch[0];
    }

    let result: FraudAnalysisResult;
    try {
      result = JSON.parse(jsonStr);
    } catch {
      throw new Error('AI returned malformed JSON.');
    }

    // Validate required fields
    if (
      result.risk_score === undefined ||
      result.trust_score === undefined ||
      !Array.isArray(result.fraud_signals) ||
      !result.ai_explanation
    ) {
      throw new Error('AI response is missing required fields.');
    }

    console.log('[OPENROUTER] Analysis complete:', result.fraud_signals.length, 'signals detected');
    return result;

  } catch (error) {
    console.error('[OPENROUTER] Fetch or processing failed:', error);
    throw error;
  }
}
