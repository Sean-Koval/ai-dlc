# Original document review case

This is a fictional SDK project, not company material.

Code `client.py` contains:
```python
def send(operation):
    for attempt in range(2):
        if operation():
            return True
    return False
```

`docs/reference.md` lines 1–5:
1. # SDK requests
2.
3. The client retries a failed operation three times after its first attempt.
4. Set an idempotency key before sending a payment request. Reuse it when retrying the same payment.
5. Request timeout must be 15 seconds according to the approved behavioral spec.

`docs/how-to.md` lines 1–3:
1. # Sending payments
2.
3. Before submitting a payment, assign its idempotency token. Keep that token unchanged for retries of that payment.

`docs/onboarding.md` lines 1–3:
1. # Getting started
2.
3. Payment requests need an idempotency key so a retry does not charge twice. See the detailed SDK reference before sending your first request.

`openspec/specs/payments/spec.md` requires a15-second timeout. Another code constant is currently TIMEOUT_SECONDS = 10. No live remote behavior is available.

Task: review these documents and propose the smallest safe change set. Distinguish unnecessary semantic duplication from useful audience-specific repetition, decide what to do about code/spec disagreements, and state what evidence would justify declaring the review current as development continues. Do not implement or fetch external sources. Return findings and next actions.
