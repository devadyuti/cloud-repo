# BackendAdapter Architecture Review

## Customer Answers (13 July 2026)

| # | Question | Answer |
|---|----------|--------|
| 1 | Where does Backend GraphQL live? | Windows EC2 instances, **same VPC** |
| 2 | Auth flow? | Simple POST (org/user/password) → JWT. TTL TBC. |
| 3 | Concurrency? | Low — tens max. All back-end, not user-facing. |
| 4 | Existing API Gateway? | Yes, several already deployed. |
| 5 | Same account/VPC/region? | Yes — all callers in same account, VPC, region. |
| 6 | Must stay off public internet? | Not strictly required if encrypted, but internal preferred. |
| 7 | GraphQL schema available? | Not yet — requested from vendor multiple times. |

### What this means for the design

- **Same VPC = simple networking.** The BackendAdapter Lambda just needs to be in the same VPC (or subnets with route to Backend's EC2s). No peering, no Transit Gateway, no PrivateLink needed.
- **Low concurrency (tens) = no scaling concerns.** Default Lambda concurrency and API Gateway throttling are more than adequate. No need for provisioned concurrency or token caching in DynamoDB — in-memory caching in the Lambda warm instance is fine.
- **Single account = simplest IAM model.** No cross-account assume-role complexity. Resource policies can reference roles directly by ARN.
- **"Internal preferred" + existing API Gateways = Regional API Gateway is confirmed as the right choice.** Private APIGW adds complexity for marginal benefit when everything is already in one VPC/account and IAM + resource policy locks it down.
- **No schema yet = design the adapter interface first.** Define the internal contract (REST routes + request/response shapes) independently of the GraphQL mutations. When the schema arrives, the adapter's internal implementation maps to it — callers are unaffected.

---

## Summary

The customer's proposed architecture is **sound and well-reasoned**. A centralised Lambda adapter fronted by API Gateway with IAM auth is a well-established pattern for exactly this type of legacy-to-modern integration. Below is a review of the architecture plus answers to the customer's specific questions.

---

## Architecture Validation

### What's solid ✓

| Aspect | Assessment |
|--------|-----------|
| Centralised facade pattern | Correct — avoids duplicating Backend auth, GraphQL logic, error mapping, and schema changes across 5+ callers |
| API Gateway + AWS_IAM auth | Best practice for internal service-to-service calls within the same account |
| SigV4 from all callers | Unifies identity model — EC2 instance profiles, Lambda execution roles, Step Functions roles all natively support this |
| Secrets Manager for Backend creds | Correct — credentials never leave the adapter, callers are unaware of them |
| Bearer token caching in Lambda | Sensible — cache in memory (warm invocation) or a short-TTL SSM/ElastiCache entry if concurrency is high |
| VPC attachment for Lambda | Required to reach the Backend GraphQL endpoint on private networking |
| Per-caller IAM scoping | `execute-api:Invoke` can be scoped to specific resources: `arn:aws:execute-api:{region}:{account}:{api-id}/{stage}/{method}/{resource}` |

### Suggestions

- **Token caching**: For a Lambda-based adapter, cache the Backend bearer token in a Lambda global (module-level) variable with a TTL check. This survives warm starts. If concurrency scaling creates many cold starts, consider a short-TTL DynamoDB item or SSM Parameter Store SecureString as a shared token cache.
- **DynamoDB caller mapping table**: The "optional" DynamoDB idea is good as an audit/extensibility mechanism, but keep IAM as the **primary** access control — DynamoDB should be a secondary lookup for caller-specific Backend org/username, not a replacement for IAM permissions.
- **Idempotency**: For `CreateClaim`/`CreateComm`, consider adding an idempotency key (e.g. caller-supplied correlation ID) stored in DynamoDB to prevent duplicate claim creation on retries.

---

## Question 1: API Gateway Type — Regional vs Private

### The Step Functions constraint (as of mid-2025)

The **native Step Functions → API Gateway optimized integration** (`arn:aws:states:::apigateway:invoke`) supports **REST APIs** (both Regional and Edge-Optimized) but **does NOT support Private API Gateway endpoints** natively.

However, since **re:Invent 2024**, Step Functions **HTTP Tasks** can invoke private APIs via **VPC Lattice Resource Configurations + EventBridge Connections**. This is a newer integration path.

### Recommendation: **Regional API Gateway with AWS_IAM — simplest and sufficient**

| Option | Verdict |
|--------|---------|
| **Regional + AWS_IAM** ✅ Recommended | Simple, works natively with Step Functions, Lambda, and EC2 callers. IAM provides strong identity-based access control. API Gateway resource policy restricts to approved principals/accounts. No internet exposure in practice because IAM rejects unsigned requests. |
| Private APIGW + proxy Lambda for SFN | Adds unnecessary complexity and latency — a Lambda just to bridge Step Functions to a private endpoint defeats the purpose |
| Private APIGW (HTTP callers) + direct Lambda invoke (SFN) | Two intake contracts = two sets of auth, logging, and error handling to maintain. Splits the centralisation benefit. |

**Why Regional + IAM is secure enough:**

- AWS_IAM auth means every request must be SigV4-signed with valid credentials — unsigned internet traffic gets `403 Missing Authentication Token`
- Add a **resource policy** on the API Gateway to explicitly deny all principals except the known caller roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::123456789012:role/StepFunctionsBackendRole",
          "arn:aws:iam::123456789012:role/HangfireEC2Role",
          "arn:aws:iam::123456789012:role/SQLAgentEC2Role",
          "arn:aws:iam::123456789012:role/DotNetAppRole",
          "arn:aws:iam::123456789012:role/LambdaCallerRole"
        ]
      },
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:eu-west-2:123456789012:*/*"
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:eu-west-2:123456789012:*/*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalAccount": "123456789012"
        }
      }
    }
  ]
}
```

- Optionally add **WAF** for rate limiting if needed, though IAM + resource policy is generally sufficient for internal use.

**If private networking is a hard compliance requirement later**, the VPC Lattice + HTTP Task path (re:Invent 2024 feature) is now available — but it adds significant infrastructure overhead (Resource Gateway, Resource Configuration, EventBridge Connection) for marginal security gain over Regional + IAM + resource policy in a single-account scenario.

---

## Question 2: Application-specific assumed roles from shared EC2 hosts

**Yes — this is a sensible and recommended pattern.**

- Each application on a shared EC2 host assumes its own IAM role via `sts:AssumeRole`
- The EC2 instance profile grants `sts:AssumeRole` permission to the application-specific roles
- Each application role has scoped `execute-api:Invoke` permissions (e.g. Hangfire can only call `/prod/POST/CreateComm`)

This gives you:

| Benefit | Detail |
|---------|--------|
| Least privilege | Each app can only call its permitted Backend operations |
| Auditability | CloudTrail logs show which assumed role made each call |
| No shared credentials | No API keys, no shared secrets between apps |
| Independent rotation | Roles can be modified per-app without affecting others |

**Implementation pattern:**

```
EC2 Instance Profile Role
  └── Trust policy allows sts:AssumeRole to:
        ├── arn:aws:iam::*:role/HangfireBackendCallerRole
        ├── arn:aws:iam::*:role/SQLAgentBackendCallerRole
        └── arn:aws:iam::*:role/DotNetAppBackendCallerRole
```

Each application uses the AWS SDK to call `AssumeRole`, gets temporary credentials, and signs its API Gateway requests with those.

---

## Question 3: Other considerations

| Topic | Recommendation |
|-------|---------------|
| **Concurrency & throttling** | Set API Gateway throttling per-method. Consider Lambda reserved concurrency to prevent Backend being overwhelmed. |
| **Circuit breaker** | If Backend goes down, implement a circuit breaker in the adapter (e.g. track consecutive failures, short-circuit with a 503 for a backoff period) rather than letting all callers hammer a dead endpoint. |
| **Observability** | API Gateway access logs + Lambda structured logging + X-Ray tracing gives end-to-end visibility. Include a correlation ID header that flows from caller → APIGW → Lambda → Backend. |
| **GraphQL schema versioning** | Pin to a specific Backend schema version. When Backend updates their schema, update the adapter centrally — callers are unaffected (the whole point of the facade). |
| **Cold starts** | If latency matters, use Lambda Provisioned Concurrency or SnapStart (if using Java). For .NET/Python, cold starts in a VPC are ~1-2s. |
| **Retry strategy** | API Gateway has built-in retry for 5xx. Additionally, configure Step Functions retry policies. The adapter itself should NOT retry mutations (CreateClaim) to avoid duplicates — only retry reads. |
| **Testing** | Stand up a mock Backend GraphQL endpoint (e.g. Apollo Server on Fargate or a Lambda) for integration testing without hitting production Backend. |

---

## Proposed Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Account                              │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │SQL Agent │  │.NET App  │  │Hangfire  │  │  Lambda/SFN  │   │
│  │(EC2)     │  │(EC2)     │  │(EC2)     │  │  Callers     │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │              │               │           │
│       │   SigV4 (assumed role per app)              │           │
│       ▼              ▼              ▼               ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         API Gateway (Regional, AWS_IAM auth)            │   │
│  │   /prod/POST/CreateClaim                                │   │
│  │   /prod/POST/CreateComm                                 │   │
│  │   /prod/POST/CreateTask                                 │   │
│  │   /prod/POST/ValidateClaim                              │   │
│  │   /prod/GET/ClaimStatus                                 │   │
│  └──────────────────────────┬──────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              BackendAdapter Lambda (VPC)                    │  │
│  │  • Validates request                                      │  │
│  │  • Acquires/caches Backend bearer token                    │  │
│  │  • Translates to GraphQL query/mutation                   │  │
│  │  • Calls Backend endpoint                                  │  │
│  │  • Normalises response/errors                             │  │
│  │  • Structured logging + correlation ID                    │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                          │                                      │
│              ┌───────────┼───────────┐                          │
│              ▼                       ▼                          │
│  ┌──────────────────┐   ┌─────────────────────┐               │
│  │ Secrets Manager  │   │ Backend GraphQL API   │               │
│  │ (Backend creds)   │   │ (private network)    │               │
│  └──────────────────┘   └─────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## IAM Permission Matrix

| Caller | Role | Permitted Operations |
|--------|------|---------------------|
| SQL Agent (EC2) | `SQLAgentBackendRole` | `POST /CreateClaim`, `GET /ClaimStatus` |
| .NET Apps (EC2) | `DotNetAppBackendRole` | `POST /CreateClaim`, `POST /ValidateClaim` |
| Hangfire (EC2) | `HangfireBackendRole` | `POST /CreateComm`, `POST /CreateTask` |
| Lambda callers | `LambdaCallerBackendRole` | (scoped per function) |
| Step Functions | `SFNBackendRole` | `POST /CreateClaim`, `GET /ClaimStatus` |

Each role gets an IAM policy like:
```json
{
  "Effect": "Allow",
  "Action": "execute-api:Invoke",
  "Resource": [
    "arn:aws:execute-api:eu-west-2:123456789012:{api-id}/prod/POST/CreateClaim",
    "arn:aws:execute-api:eu-west-2:123456789012:{api-id}/prod/GET/ClaimStatus"
  ]
}
```

---

## TL;DR for the customer

1. **Architecture is valid** — well-designed centralised adapter pattern
2. **Use Regional API Gateway + AWS_IAM** — simplest, secure, natively supported by all callers including Step Functions
3. **Assumed roles from shared EC2 = yes** — recommended pattern, gives per-app identity and least privilege
4. **Watch out for**: token caching strategy, mutation idempotency, circuit breaking, and correlation ID propagation
