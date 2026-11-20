# R4 — Evaluation: deterministic + LLM-as-judge (captured evidence)

Both evaluators were run on ONE recorded interaction (session
`33b05303-6021-4772-8eb5-b6d85bc36a21` — the "weather in Athens?" turn).

Command:
```bash
agentcore run eval --runtime agentops \
  --evaluator ToolAndPolicyCheck HelpfulnessJudge \
  --session-id 33b05303-6021-4772-8eb5-b6d85bc36a21 --json
```

## Deterministic grader — `ToolAndPolicyCheck` (code-based, no LLM)
- **value: 1 → label: Pass**
- explanation: *"Expected tool 'weather' was called. Tools observed: ['weather']."*
- tokenUsage: 0 (pure code — the result is fully reproducible)

Checks the recorded spans and passes only if the expected tool was actually
invoked. A weather question that skipped the `weather` tool would be a
deterministic FAIL.

## LLM-as-judge — `HelpfulnessJudge` (Sonnet 4.5, 1–5 quality scale)
- **value: 5 → label: Excellent**
- explanation: *"The assistant's response directly answers the user's question
  about the weather in Athens. It correctly used the weather tool with the
  appropriate parameter (city: 'Athens'), received the tool result ('very
  sunny'), and accurately conveyed this information... clear, well-formatted...
  concise, friendly, and fully addresses the user's query without any errors or
  omissions."*
- tokenUsage: 788 (a real judge call)

## Why this satisfies R4
- A **deterministic** pass/fail on "expected tool called" (0 tokens → same input,
  same result every time).
- An **LLM-as-judge** score **with its explanation** on a helpfulness rubric.
- Both produced from a single recorded interaction, on demand.

Raw results: `agentops/agentcore/.cli/eval-results/eval_2026-09-28_22-11-50.json`

Evaluator ARNs:
- `arn:aws:bedrock-agentcore:eu-west-1:123456789012:evaluator/agentops_ToolAndPolicyCheck-dZfaia4SjZ`
- `arn:aws:bedrock-agentcore:eu-west-1:123456789012:evaluator/agentops_HelpfulnessJudge-RhI9KmGhMr`
