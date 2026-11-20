---
inclusion: fileMatch
fileMatchPattern: "**/services/**,**/insights*,**/bedrock*,**/agent*"
---

# Amazon Bedrock Integration Guide

## Cross-Region Inference Profiles

Use inference profiles for higher availability — Bedrock routes requests across regions automatically.

| Model | Profile ID |
|-------|-----------|
| Claude Sonnet 4.6 | `eu.anthropic.claude-sonnet-4-6` |
| Claude Haiku 4.5 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` |
| Claude Opus 4.7 | `us.anthropic.claude-opus-4-7` |

## SDK Usage (Node.js)

```javascript
import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';

const client = new BedrockRuntimeClient({ region: 'eu-west-1' });

const response = await client.send(new InvokeModelCommand({
  modelId: 'eu.anthropic.claude-sonnet-4-6',
  contentType: 'application/json',
  body: JSON.stringify({
    anthropic_version: 'bedrock-2023-05-31',
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }],
  }),
}));

const result = JSON.parse(new TextDecoder().decode(response.body));
const text = result.content[0].text;
```

## SDK Usage (Python)

```python
import boto3
import json

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

response = bedrock.invoke_model(
    modelId='us.anthropic.claude-sonnet-4-6',
    contentType='application/json',
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': 1024,
        'messages': [{'role': 'user', 'content': prompt}],
    }),
)

result = json.loads(response['body'].read())
text = result['content'][0]['text']
```

## IAM Policy for Bedrock

```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": [
    "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-4-6",
    "arn:aws:bedrock:*:ACCOUNT_ID:inference-profile/eu.anthropic.claude-sonnet-4-6"
  ]
}
```

**Critical:** Wildcard the region (`*`) — inference profiles route across regions.

## Prompt Engineering Tips

- Be specific about the output format (JSON, bullet points, etc.)
- Include context about the domain (wealth management, risk profiles)
- Set a system message for consistent persona/tone
- Keep prompts under 2000 tokens for fast responses
- Parse the response defensively — model output can vary

## Error Handling

- Bedrock can throttle — implement exponential backoff for retries
- Set Lambda timeout to 30s for Bedrock calls (model inference takes 3-15s)
- Handle `ThrottlingException` and `ModelTimeoutException` gracefully
- Return a user-friendly message if Bedrock is unavailable
