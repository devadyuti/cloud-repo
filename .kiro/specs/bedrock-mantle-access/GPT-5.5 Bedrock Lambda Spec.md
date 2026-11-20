# Spec: Lambda → GPT-5.5 via Amazon Bedrock Mantle

## Overview

A simple AWS Lambda function that invokes OpenAI's GPT-5.5 model through the Amazon Bedrock Mantle endpoint using the OpenAI Python SDK.

## Requirements

### Functional

- Accept a prompt (text input) via the Lambda event payload
- Call GPT-5.5 on the `bedrock-mantle` endpoint using the OpenAI Responses API
- Return the model's response text to the caller
- Support configurable region (`us-east-1` or `us-east-2`)

### Non-Functional

- Timeout: 60s (model responses can take time for complex prompts)
- Memory: 256 MB minimum
- Runtime: Python 3.12+
- API key stored in AWS Secrets Manager (not environment variables in production)

## Architecture

```
Client → Lambda → bedrock-mantle.{region}.api.aws → GPT-5.5

```

- **Endpoint**: `https://bedrock-mantle.{region}.api.aws/openai/v1`
- **Model ID**: `openai.gpt-5.5`
- **Auth**: Bedrock long-term API key (generated from Bedrock console)
- **SDK**: `openai` Python package (via Lambda Layer)

## IAM Policy

Attach the AWS managed policy to the Lambda execution role:

```
arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

```

This grants:

| Action | Resource | Purpose |
| --- | --- | --- |
| `bedrock-mantle:Get*` | `arn:aws:bedrock-mantle:*:*:project/*` | Read project metadata |
| `bedrock-mantle:List*` | `arn:aws:bedrock-mantle:*:*:project/*` | List available models/projects |
| `bedrock-mantle:CreateInference` | `arn:aws:bedrock-mantle:*:*:project/*` | Invoke the model |
| `bedrock-mantle:CallWithBearerToken` | `*` | Authenticate with API key |

Additionally, if using Secrets Manager for the API key:

```json
{
  "Effect": "Allow",
  "Action": ["secretsmanager:GetSecretValue"],
  "Resource": "arn:aws:secretsmanager:{region}:{account-id}:secret:bedrock-mantle-api-key-*"
}

```

## Lambda Handler

```python
import os
import json
import boto3
from openai import OpenAI

def get_api_key():
    """Retrieve API key from Secrets Manager."""
    client = boto3.client("secretsmanager")
    secret = client.get_secret_value(SecretId=os.environ["API_KEY_SECRET_ARN"])
    return json.loads(secret["SecretString"])["api_key"]

def lambda_handler(event, context):
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    
    client = OpenAI(
        api_key=get_api_key(),
        base_url=f"https://bedrock-mantle.{region}.api.aws/openai/v1"
    )

    prompt = event.get("prompt", "Hello, what can you do?")

    response = client.responses.create(
        model="openai.gpt-5.5",
        input=prompt
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "response": response.output_text,
            "model": "openai.gpt-5.5",
            "region": region
        })
    }

```

## Environment Variables

| Variable | Value | Description |
| --- | --- | --- |
| `API_KEY_SECRET_ARN` | `arn:aws:secretsmanager:...` | ARN of the secret holding the Bedrock API key |
| `BEDROCK_REGION` | `us-east-1` | Target region for inference |

## Lambda Layer

The `openai` package must be bundled as a Lambda Layer:

```bash
mkdir -p layer/python
pip install openai -t layer/python
cd layer && zip -r openai-layer.zip python/

```

## Deployment (SAM template)

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Resources:
  GPT55Function:
    Type: AWS::Serverless::Function
    Properties:
      Handler: handler.lambda_handler
      Runtime: python3.12
      Timeout: 60
      MemorySize: 256
      Layers:
        - !Ref OpenAILayer
      Environment:
        Variables:
          API_KEY_SECRET_ARN: !Ref ApiKeySecret
          BEDROCK_REGION: us-east-1
      Policies:
        - AmazonBedrockMantleInferenceAccess
        - Statement:
            - Effect: Allow
              Action: secretsmanager:GetSecretValue
              Resource: !Ref ApiKeySecret

  OpenAILayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      ContentUri: layer/
      CompatibleRuntimes:
        - python3.12

  ApiKeySecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: bedrock-mantle-api-key
      Description: API key for Bedrock Mantle GPT-5.5 access

```

## Notes

- **No EU availability** — GPT-5.5 is currently only in `us-east-1` and `us-east-2`
- The model does NOT appear in the standard Bedrock model catalog — it's on a separate `bedrock-mantle` endpoint
- Pricing matches OpenAI first-party rates; usage counts toward AWS commitments
- Context window: 272K tokens
- Supports text, image, audio, and video input modalities

