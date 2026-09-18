"""Offline planning: no process, socket or credential value is touched here."""

from __future__ import annotations

import re

from pydantic import ValidationError

from ai_dlc.verification.evaluation.contracts import ARMS, Profile, Suite

SECRET_KEY = re.compile(r"secret|token|password|passwd|api[_-]?key|credential", re.IGNORECASE)
# Recognizable credential shapes only; this is a tripwire, not proof of absence.
SECRET_VALUE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{36,}|\bgithub_pat_[A-Za-z0-9_]{20,}"
    r"|\bsk-[A-Za-z0-9_-]{20,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|\bAKIA[0-9A-Z]{16}\b"
    r"|\bATATT[A-Za-z0-9_=-]{20,}"
)
NO_CLAIM = "none: one attempt per arm shows differences without supporting a conclusion"


def _refuse_secrets(value: object, path: str) -> None:
    """Name the field, never the value."""
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)):
                raise ValueError(f"Scenarios must not carry credentials: {path}.{key}")
            _refuse_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _refuse_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str) and SECRET_VALUE.search(value):
        raise ValueError(f"Scenarios must not carry credentials: {path}")


def _validated(model, raw: object, label: str):
    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors(include_input=False)
        )
        raise ValueError(f"Invalid evaluation {label}: {problems}") from None


def _unique(values: list[str], label: str) -> None:
    repeated = sorted({v for v in values if values.count(v) > 1})
    if repeated:
        raise ValueError(f"Duplicate {label}: {', '.join(repeated)}")


def plan(suite: object, profile: object) -> dict:
    """Expand the scenario, arm and attempt matrix, or refuse naming the offending field."""
    _refuse_secrets(suite, "suite")
    checked = _validated(Suite, suite, "suite")
    settings = _validated(Profile, profile, "profile")
    if settings.mode == "release" and not settings.engine.artifact.startswith("https://"):
        raise ValueError("Release mode requires a published https engine artifact and its sha256")
    if settings.driver.kind == "deterministic" and not settings.driver.script:
        raise ValueError(
            "Invalid evaluation profile: driver.script: the deterministic driver needs one"
        )
    _unique([s.id for s in checked.scenarios], "scenario identifier")
    attempts = []
    for scenario in checked.scenarios:
        _unique([a.id for a in scenario.assertions], f"assertion identifier in {scenario.id}")
        _unique(list(scenario.arms), f"arms in {scenario.id}")
        if "baseline" not in scenario.arms or "treatment" not in scenario.arms:
            raise ValueError(
                f"Scenario {scenario.id} must run both arms (treatment and baseline) so its "
                "result can be compared"
            )
        for arm in ARMS:
            for attempt in range(1, settings.attempts + 1):
                attempts.append(
                    {
                        "scenario": scenario.id,
                        "arm": arm,
                        "attempt": attempt,
                        # Option 2: the candidate is prebuilt into an image derived from
                        # the baseline image; the run verifies that derivation.
                        "image": settings.engine.image if arm == "treatment" else settings.image,
                        "fixture": scenario.fixture.model_dump(),
                        # The baseline differs in exactly one thing: no engine is installed.
                        "engine_sha256": settings.engine.sha256 if arm == "treatment" else None,
                        "limits": scenario.limits.model_dump(),
                        "assertions": [
                            a.id
                            for a in scenario.assertions
                            if arm == "treatment" or a.dimension != "workflow"
                        ],
                    }
                )
    return {
        "schema": 1,
        "suite": checked.id,
        "profile": settings.id,
        "mode": settings.mode,
        "driver": settings.driver.model_dump(),
        "model": settings.model,
        "engine": settings.engine.model_dump(),
        "budgets": settings.budgets.model_dump(),
        "credentials": settings.credentials,
        "resources": settings.resources,
        "attempts": attempts,
        "comparison": {
            "attempts_per_arm": settings.attempts,
            "claim": NO_CLAIM if settings.attempts == 1 else "descriptive differences only",
        },
    }
