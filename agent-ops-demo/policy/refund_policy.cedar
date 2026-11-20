// R3 — AgentOps demo: default-deny governance policy (Cedar)
//
// AgentCore policy engines are DEFAULT-DENY: a tool call is denied unless a
// `permit` matches, and any matching `forbid` wins over every `permit`.
//
// This file expresses the demo's rule: the privileged action `process_refund`
// is allowed ONLY for small refunds (< $1000). The demo then triggers a large
// refund ($5000), which no `permit` covers -> deterministic DENY, logged to
// CloudWatch and visible in the trace.
//
// Substitute <GATEWAY_ARN> with the value from `agentcore status` (or the
// create_policy helper resolves it). The action id is
// "<TargetName>___<toolName>" -> "RefundTarget___process_refund".

permit(
  principal,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>"
)
when {
  context.input.amount < 1000
};
