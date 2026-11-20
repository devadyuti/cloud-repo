# R2 — Readable trace (captured evidence)

One invocation produces a full OpenTelemetry trace in AgentCore Observability →
CloudWatch. Spans land in the `spans` stream of the agent's log group
`/aws/bedrock-agentcore/runtimes/agentops_agentops-133RNOGqJm-DEFAULT`
(scope `strands.telemetry.tracer`, exported by ADOT `0.20.0-aws`). View in the
CloudWatch **GenAI Observability** console, or `agentcore traces`.

## Session → trace → span (the "weather in Athens" turn)

The trace reconstructs the whole agentic loop for a single invocation:

```
POST /invocations                         4474.8 ms   (end-to-end)
└─ invoke_agent Strands Agents            4411.2 ms
   ├─ execute_event_loop_cycle            1771.9 ms   (iteration 1)
   │  └─ chat                             1769.5 ms   in=1988 out=51  TTFT=1529 ms
   │     model=global.anthropic.claude-sonnet-4-5
   ├─ execute_tool weather                   1.3 ms   (tool call)
   └─ execute_event_loop_cycle            2638.2 ms   (iteration 2)
      └─ chat                             2637.4 ms   in=2054 out=17  TTFT=2267 ms
```

Each `chat` span also carries the conversation as inline events:
`gen_ai.system.message` (system prompt), `gen_ai.user.message` (the question),
`gen_ai.assistant.message` (the `toolUse` for `weather`), `gen_ai.tool.message`
(the tool result), and `gen_ai.choice` (the final answer). That is the readable
model-call / tool-call / decision breakdown R2 asks for.

---

# R5 — Cost / latency / iteration glance (same run)

From the same trace's span attributes — visible on one screen:

| Metric | Value |
|---|---|
| End-to-end latency | **4.47 s** |
| Model (iterations / event-loop cycles) | **2** model calls |
| Tool calls | **1** (`weather`, 1.3 ms) |
| Tokens — call 1 | in 1988 / out 51 / total 2039 |
| Tokens — call 2 | in 2054 / out 17 / total 2071 |
| Tokens — interaction total | **~4110** |
| Time-to-first-token | 1529 ms, then 2267 ms |
| Model | `global.anthropic.claude-sonnet-4-5` |

This connects operational cost (tokens) and latency back to the morning's
model-routing dimension: a cheaper/faster model on the simple tool-call turns
would cut both token spend and TTFT.

_All values pulled directly from the OTEL `chat` spans; no estimation._
