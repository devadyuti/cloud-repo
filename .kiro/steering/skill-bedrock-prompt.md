---
inclusion: auto
description: "Use when building AI features, writing prompts for Bedrock, integrating Claude for insights, or adding generative AI capabilities"
---

# Skill: Build Bedrock AI Feature

## Workflow

When adding a new AI-powered feature using Amazon Bedrock:

### Step 1: Design the Prompt

Structure prompts with clear context, instructions, and output format:

```javascript
const buildPrompt = (context) => {
  return `You are a senior wealth management advisor at a UK-based investment firm.

Context:
- Client risk profile: ${context.riskProfile}
- Current allocation: ${JSON.stringify(context.allocation)}
- Portfolio value: £${context.portfolioValue.toLocaleString()}

Task: Provide ${context.numSuggestions || 3} specific, actionable rebalancing suggestions.

Rules:
- Reference specific asset classes and percentages
- Consider the client's risk profile when making recommendations
- Include rationale for each suggestion
- Keep each suggestion to 2-3 sentences

Format your response as a JSON array:
[
  { "title": "Brief title", "suggestion": "Detailed recommendation", "priority": "high|medium|low" }
]`;
};
```

### Step 2: Create the Service Function

Add to `backend/src/services/`:

```javascript
// backend/src/services/aiInsights.js
import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';

const client = new BedrockRuntimeClient({ region: 'eu-west-1' });

export const generateInsights = async (prompt) => {
  const command = new InvokeModelCommand({
    modelId: 'eu.anthropic.claude-sonnet-4-6',
    contentType: 'application/json',
    body: JSON.stringify({
      anthropic_version: 'bedrock-2023-05-31',
      max_tokens: 1024,
      temperature: 0.3,  // Lower for more consistent financial advice
      messages: [{ role: 'user', content: prompt }],
    }),
  });

  const response = await client.send(command);
  const result = JSON.parse(new TextDecoder().decode(response.body));
  return result.content[0].text;
};
```

### Step 3: Create the Lambda Handler

```javascript
// backend/src/routes/insights.js
import { generateInsights } from '../services/aiInsights.js';

export const getInsights = async (event) => {
  try {
    const { id } = event.pathParameters || {};
    // Fetch client data, build prompt, call Bedrock
    const prompt = buildPrompt(clientData);
    const rawResponse = await generateInsights(prompt);

    // Parse AI response defensively
    let suggestions;
    try {
      suggestions = JSON.parse(rawResponse);
    } catch {
      suggestions = [{ title: 'AI Response', suggestion: rawResponse, priority: 'medium' }];
    }

    return { statusCode: 200, body: JSON.stringify({ suggestions }) };
  } catch (error) {
    if (error.name === 'ThrottlingException') {
      return { statusCode: 429, body: JSON.stringify({ message: 'AI service is busy. Please retry.' }) };
    }
    console.error('Insights error:', error);
    return { statusCode: 500, body: JSON.stringify({ message: 'Failed to generate insights' }) };
  }
};
```

### Step 4: Register in serverless.yml

```yaml
  generateInsights:
    handler: src/routes/insights.getInsights
    timeout: 30  # Bedrock needs more time
    events:
      - httpApi:
          path: /clients/{id}/insights
          method: post
```

### Step 5: IAM Permissions

```yaml
- Effect: Allow
  Action:
    - bedrock:InvokeModel
  Resource:
    - arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-6
    - arn:aws:bedrock:*:ACCOUNT_ID:inference-profile/eu.anthropic.claude-sonnet-4-6
```

### Step 6: Frontend Integration

```jsx
const [insights, setInsights] = useState([]);
const [loading, setLoading] = useState(false);

const handleGetInsights = async () => {
  setLoading(true);
  try {
    const response = await post({ apiName: 'portfolioApi', path: `/clients/${clientId}/insights` });
    const data = await response.body.json();
    setInsights(data.suggestions);
  } catch (err) {
    setError('Unable to generate insights. Please try again.');
  } finally {
    setLoading(false);
  }
};
```

## Prompt Engineering Tips

- Set temperature 0.2-0.4 for factual/financial content
- Always specify output format (JSON preferred for parsing)
- Include domain context (wealth management, UK market)
- Parse responses defensively — wrap JSON.parse in try/catch
- Keep prompts under 2000 tokens for fast responses (3-8s)

## Checklist

- [ ] Lambda timeout set to 30s
- [ ] IAM uses wildcard region for inference profiles
- [ ] Prompt includes clear output format specification
- [ ] Response parsing handles malformed AI output gracefully
- [ ] ThrottlingException and ModelTimeoutException handled
- [ ] Frontend shows loading state during AI call
- [ ] User-friendly error messages (not raw exceptions)
