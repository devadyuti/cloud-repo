// R3 — Alternative, even more explicit "money moment": an explicit forbid.
//
// AgentCore policy semantics are forbid-wins: even if a broad `permit` exists,
// a matching `forbid` denies the call. This version PERMITS the privileged
// action generally but FORBIDS it above a threshold, so a large refund is
// denied by an explicit rule (reads very cleanly on a projector).
//
// Substitute <GATEWAY_ARN> from `agentcore status`.

// Baseline allow for the privileged tool...
permit(
  principal,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>"
);

// ...but explicitly DENY high-value refunds. forbid wins over permit.
forbid(
  principal,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"<GATEWAY_ARN>"
)
when {
  context.input.amount >= 1000
};
