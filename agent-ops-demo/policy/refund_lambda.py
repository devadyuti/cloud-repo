"""
Synthetic 'process_refund' tool backing the AgentOps demo gateway target (R3).

This is intentionally trivial and side-effect-free: it does NOT move money. It
exists only so the AgentCore Gateway has a real tool to route to, and so the
Cedar policy engine has something to allow/deny. All data is synthetic.

Gateway Lambda targets receive the tool name via the
`bedrockAgentCoreToolName` context field and the tool arguments as the event.
"""

import json


def handler(event, context):
    # The gateway passes tool input as the event body. Be liberal in parsing.
    amount = None
    if isinstance(event, dict):
        amount = event.get("amount")
        if amount is None and "body" in event:
            try:
                amount = json.loads(event["body"]).get("amount")
            except Exception:
                pass

    # If we ever actually execute (i.e. the policy ALLOWED it), return a
    # synthetic success. When the policy DENIES, the gateway blocks the call
    # and this code never runs — that's the observable denial.
    return {
        "status": "refunded",
        "amount": amount,
        "note": "SYNTHETIC demo refund — no money moved.",
    }
