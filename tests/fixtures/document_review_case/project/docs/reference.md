# SDK requests

The client retries a failed operation three times after its first attempt.
Set an idempotency key before sending a payment request. Reuse it when retrying the same payment.
Request timeout must be 15 seconds according to the approved behavioral spec.
