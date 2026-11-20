import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';

const bedrockClient = new BedrockRuntimeClient({ region: 'eu-west-1' });

const TARGET_ALLOCATIONS = {
  Conservative: { ukEquities: 20, internationalEquities: 15, fixedIncome: 40, alternatives: 10, cash: 15 },
  Balanced: { ukEquities: 30, internationalEquities: 25, fixedIncome: 25, alternatives: 12, cash: 8 },
  Growth: { ukEquities: 40, internationalEquities: 30, fixedIncome: 15, alternatives: 10, cash: 5 }
};

/**
 * Generate AI rebalancing insights using Amazon Bedrock (Claude).
 * @param {object} allocation - Current allocation percentages
 * @param {string} riskProfile - "Conservative" | "Balanced" | "Growth"
 * @param {object} riskMetrics - Current risk metrics (volatility, sharpeRatio, maxDrawdown, betaFTSE100)
 * @returns {Promise<string[]>} Array of 3-4 actionable suggestions
 */
export async function generateInsights(allocation, riskProfile, riskMetrics) {
  const target = TARGET_ALLOCATIONS[riskProfile] || TARGET_ALLOCATIONS.Balanced;

  const prompt = `You are a senior wealth management advisor. Analyse the following client portfolio and provide exactly 3-4 actionable rebalancing suggestions. Each suggestion must include specific percentage values and reference specific asset classes.

Current Allocation:
- UK Equities: ${allocation.ukEquities}%
- International Equities: ${allocation.internationalEquities}%
- Fixed Income: ${allocation.fixedIncome}%
- Alternatives: ${allocation.alternatives}%
- Cash: ${allocation.cash}%

Risk Profile: ${riskProfile}

Target Allocation for ${riskProfile} profile:
- UK Equities: ${target.ukEquities}%
- International Equities: ${target.internationalEquities}%
- Fixed Income: ${target.fixedIncome}%
- Alternatives: ${target.alternatives}%
- Cash: ${target.cash}%

Current Risk Metrics:
- Annualised Volatility: ${riskMetrics.volatility}%
- Sharpe Ratio: ${riskMetrics.sharpeRatio}
- Max Drawdown (12M): ${riskMetrics.maxDrawdown}%
- Beta vs FTSE 100: ${riskMetrics.betaFTSE100}

Respond with a JSON array of 3-4 strings, each being one actionable suggestion. Only output the JSON array, no other text.`;

  const command = new InvokeModelCommand({
    modelId: 'eu.anthropic.claude-sonnet-4-6',
    contentType: 'application/json',
    accept: 'application/json',
    body: JSON.stringify({
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }]
    })
  });

  const response = await bedrockClient.send(command);
  const responseBody = JSON.parse(new TextDecoder().decode(response.body));

  // Claude returns content as an array of content blocks
  const textContent = responseBody.content
    .filter((block) => block.type === 'text')
    .map((block) => block.text)
    .join('');

  // Extract JSON array from the response text
  const suggestions = parseJsonArray(textContent);
  return suggestions;
}

/**
 * Parse a JSON array from text that may contain markdown code fences or extra whitespace.
 * @param {string} text - Raw text from Claude response
 * @returns {string[]}
 */
function parseJsonArray(text) {
  // Try direct parse first
  try {
    const parsed = JSON.parse(text.trim());
    if (Array.isArray(parsed)) return parsed;
  } catch {
    // Fall through to regex extraction
  }

  // Extract JSON array from markdown code fences or surrounding text
  const match = text.match(/\[[\s\S]*\]/);
  if (match) {
    try {
      const parsed = JSON.parse(match[0]);
      if (Array.isArray(parsed)) return parsed;
    } catch {
      // Fall through
    }
  }

  // Last resort: return the text as a single suggestion
  return [text.trim()];
}
