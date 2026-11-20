# Bedrock Mantle → GPT-5.5 Lambda

An AWS Lambda function that invokes OpenAI's GPT-5.5 model through the Amazon
Bedrock Mantle endpoint using the OpenAI Python SDK (Responses API).

Built from `.kiro/specs/bedrock-mantle-access/GPT-5.5 Bedrock Lambda Spec.md`.

## Layout

```
bedrock-mantle-access/
├── src/handler.py          # Lambda handler
├── layer/requirements.txt  # OpenAI SDK layer dependency (built by `sam build`)
├── scripts/build-layer.sh  # Manual layer build (optional)
├── template.yaml           # SAM template
└── requirements.txt        # Function-level deps (SDK ships via the layer)
```

## How it works

```
Client → Lambda → bedrock-mantle.{region}.api.aws/openai/v1 → openai.gpt-5.5
```

- Endpoint: `https://bedrock-mantle.{region}.api.aws/openai/v1`
- Model ID: `openai.gpt-5.5`
- Auth: Bedrock long-term API key stored in AWS Secrets Manager
- Region: `us-east-1` (default) or `us-east-2`

## Deploy

```bash
cd bedrock-mantle-access
sam build
sam deploy --guided
```

`sam build` compiles the OpenAI SDK layer from `layer/requirements.txt`.

After the first deploy, populate the secret with the Bedrock Mantle API key.
The handler expects JSON with an `AWS_BEARER_TOKEN_BEDROCK` field, but also
accepts a raw plaintext key as a fallback:

```bash
# Option 1: JSON format (preferred)
aws secretsmanager put-secret-value \
  --secret-id BEDROCK_API_KEY \
  --secret-string '{"AWS_BEARER_TOKEN_BEDROCK":"<your-bedrock-mantle-api-key>"}'

# Option 2: raw plaintext
aws secretsmanager put-secret-value \
  --secret-id BEDROCK_API_KEY \
  --secret-string '<your-bedrock-mantle-api-key>'
```

## Invoke

The function accepts both direct Lambda invocations and API Gateway proxy events.

### Direct invocation

```bash
aws lambda invoke \
  --function-name <FunctionName-from-stack-outputs> \
  --payload '{"prompt":"Explain retrieval-augmented generation in two sentences."}' \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
```

### Public HTTP API endpoint (no auth — demo only)

The stack provisions an unauthenticated HTTP API and outputs its `InvokeUrl`.
POST a JSON body with a `prompt`:

```bash
curl -s -X POST <InvokeUrl> \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain retrieval-augmented generation in two sentences."}'
```

> Warning: this endpoint is open to the internet with no authentication. It is
> throttled (rate 5 / burst 10 req/s) to limit abuse, but anyone with the URL
> can invoke the model at your account's expense. For anything beyond a demo,
> add an authorizer, an API key + usage plan, or switch to a Function URL with
> IAM auth.

## Environment variables

| Variable | Description |
| --- | --- |
| `API_KEY_SECRET_ID` | Name (or ARN) of the Secrets Manager secret holding the API key |
| `BEDROCK_REGION` | Target region for inference (`us-east-1` / `us-east-2`) |

## Notes

- `openai.gpt-5.5` is served via the **Bedrock Mantle endpoint**, not the
  standard Bedrock model catalogue. That's why this function calls the OpenAI
  Responses API against `bedrock-mantle.{region}.api.aws/openai/v1` directly
  rather than using `bedrock-runtime` / `InvokeModel`.
- Availability is `us-east-1` / `us-east-2` only (no EU) per the spec.
- Auth uses a Bedrock long-term API key (generated from the Bedrock console),
  stored in Secrets Manager. The `AmazonBedrockMantleInferenceAccess` managed
  policy grants the `bedrock-mantle:*` actions, including `CallWithBearerToken`.
