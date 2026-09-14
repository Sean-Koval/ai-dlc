"""Real local tracker-migration project fixtures; no remote services."""

from __future__ import annotations


class Tickets:
    """Adapter fixture owns configured project validation and canonical ticket identity."""

    def __init__(self):
        self.identities = {"42": "T42", "url/42": "T42", "43": "T43"}
        self.calls = []
        self.on_read = None

    def invoke(self, operation, payload):
        self.calls.append(operation)
        assert operation == "read", "Migration must never mutate remote tickets"
        if self.on_read:
            self.on_read()
        reference = payload["reference"]
        if reference not in self.identities:
            raise ValueError("Target belongs to wrong project")
        ticket = self.identities[reference]
        return {"id": ticket, "url": f"https://tracker.test/project/{ticket}", "state": "open"}


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in [root / "ai-dlc.toml", *sorted((root / ".ai-dlc/work").glob("*.toml"))]
    }
