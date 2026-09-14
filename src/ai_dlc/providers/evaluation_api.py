"""OpenAI Responses transport for explicitly requested skill evaluations."""

from urllib.parse import urlsplit

import httpx


class EvaluationClient:
    def __init__(self, api_url: str, token: str):
        url = urlsplit(api_url)
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.query
            or url.fragment
            or not url.path.endswith("/responses")
        ):
            raise ValueError("Evaluation requires an HTTPS Responses endpoint without credentials")
        self.api_url = api_url
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {token}"}, timeout=120, follow_redirects=False
        )

    def count_input_tokens(self, request):
        response = self.client.post(
            self.api_url + "/input_tokens",
            json={
                "model": request["model"],
                "input": request["input"],
            },
        )
        response.raise_for_status()
        return response.json()["input_tokens"]

    def complete(self, request):
        # Retain even an error response verbatim; the runner stops on missing usage.
        return self.client.post(self.api_url, json=request).text

    def close(self):
        self.client.close()
