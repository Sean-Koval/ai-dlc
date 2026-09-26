"""Safe report contracts, independent of local machine state."""

import copy
import json

import pytest

from ai_dlc.environment import report_compare, report_schema


def payload():
    engine = {
        "package_version": "0.4.0",
        "installation_kind": "source",
        "source_revision": "a" * 40,
        "source_dirty": False,
        "artifact_sha256": None,
        "state": "observed",
        "reasons": {
            "package_version": None,
            "source_revision": None,
            "source_dirty": None,
            "artifact_sha256": "not-applicable",
        },
    }
    return {
        "schema_version": 1,
        "observed_at": "2026-09-26T12:00:00Z",
        "engine": {
            **{k: v for k, v in engine.items() if k not in ("state", "reasons")},
            "current_process": copy.deepcopy(engine),
            "path_selected": copy.deepcopy(engine),
        },
        "platform": {
            "os": "linux",
            "architecture": "x86_64",
            "shell_family": "bash",
            "reasons": {"os": None, "architecture": None, "shell_family": None},
        },
        "profile": {
            "id": None,
            "commit": None,
            "content_sha256": None,
            "state": "not-applicable",
            "reasons": {
                "id": "not-applicable",
                "commit": "not-applicable",
                "content_sha256": "not-applicable",
            },
        },
        "sources": [],
        "runtimes": [
            {
                "id": "python",
                "required": True,
                "version": {
                    "intended": ">=3.12,<4",
                    "observed": "3.12.1",
                    "state": "observed",
                    "reason": None,
                },
            }
        ],
        "clients": [
            {
                "id": "codex",
                "edition": "cli",
                "version": {
                    "intended": None,
                    "observed": "1.0.0",
                    "state": "observed",
                    "reason": None,
                },
                "configured": "yes",
                "rendered": "yes",
                "recognized": "unknown",
                "authenticated": "unknown",
                "reasons": {
                    "id": None,
                    "edition": None,
                    "configured": None,
                    "rendered": None,
                    "recognized": "not-assessed",
                    "authenticated": "not-assessed",
                },
            }
        ],
        "project": {
            "engine_constraint": ">=0.4,<1",
            "roles": [],
            "components": [
                {
                    "id": "core",
                    "platform_support": {
                        "os": ["linux", "macos"],
                        "architecture": ["x86_64", "arm64"],
                        "shell_family": ["bash", "zsh"],
                    },
                }
            ],
            "client_ids": ["codex"],
            "configuration_sha256": None,
            "guidance": [
                {
                    "id": "agents",
                    "kind": "instruction",
                    "expected_sha256": "b" * 64,
                    "observed_sha256": "b" * 64,
                    "state": "match",
                    "native_server": None,
                    "reasons": {"id": None, "expected_sha256": None, "observed_sha256": None},
                }
            ],
            "state": "known",
            "reasons": {"engine_constraint": None},
        },
        "auth": [],
        "limitations": [],
        "configuration_identity": None,
        "observation_identity": None,
    }


def report(**changes):
    value = payload()
    value.update(changes)
    return report_schema.finalize_report(value)


def compare(left, right):
    return report_compare.compare_reports(
        report_schema.finalize_report(left), report_schema.finalize_report(right)
    )


def test_complete_report_roundtrip_and_comparison():
    value = report()
    assert report_schema.parse_report(report_schema.report_bytes(value)) == value
    assert report_schema.completeness(value) == (True, True)
    result = report_compare.compare_reports(value, value)
    assert result["configuration_complete"] and result["observation_complete"]
    assert {f["field"] for f in result["findings"]} == {
        "clients.codex.recognized",
        "clients.codex.authenticated",
    }
    assert all(f["class"] == "unknown" for f in result["findings"])
    assert report_compare.comparison_exit_code(result) == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("observed_at", "2026-09-27T12:00:00Z"),
        (
            "auth",
            [
                {
                    "kind": "client",
                    "id": "codex",
                    "credential_presence": "present",
                    "verification": "not-assessed",
                    "verified_at": None,
                    "evidence_identity": None,
                    "reasons": {
                        "id": None,
                        "verified_at": "not-assessed",
                        "evidence_identity": "not-assessed",
                    },
                }
            ],
        ),
    ],
)
def test_time_auth_and_native_evidence_do_not_change_identities(field, value):
    original = report()
    changed = payload()
    changed[field] = value
    changed["clients"][0]["recognized"] = "yes"
    changed["clients"][0]["reasons"]["recognized"] = None
    new = report_schema.finalize_report(changed)
    assert new["configuration_identity"] == original["configuration_identity"]
    assert new["observation_identity"] == original["observation_identity"]


def test_observed_version_changes_only_observation_identity():
    original = report()
    changed = payload()
    changed["clients"][0]["version"]["observed"] = "1.0.1"
    new = report_schema.finalize_report(changed)
    assert new["configuration_identity"] == original["configuration_identity"]
    assert new["observation_identity"] != original["observation_identity"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p.update(schema_version=True),
        lambda p: p.update(secret="PRIVATE_SENTINEL"),
        lambda p: p["clients"][0].update(command="PRIVATE_SENTINEL"),
        lambda p: p["clients"][0]["version"].update(observed="PRIVATE_SENTINEL"),
        lambda p: p["runtimes"].append(copy.deepcopy(p["runtimes"][0])),
        lambda p: p["engine"].update(source_revision="b" * 40),
        lambda p: p["project"].update(engine_constraint="^3"),
        lambda p: p["clients"][0]["reasons"].update(extra=None),
        lambda p: p["platform"].update(os=None),
    ],
)
def test_rejects_unsafe_or_inconsistent_payload_without_echo(mutation):
    value = payload()
    mutation(value)
    with pytest.raises(ValueError) as error:
        report_schema.finalize_report(value)
    assert "PRIVATE_SENTINEL" not in str(error.value)
    assert len(str(error.value)) < 100


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema_version":1,"schema_version":1}',
        b'{"x":NaN}',
        b" " * (1024 * 1024 + 1),
        b"[" * 14 + b"]" * 14,
        b'"PRIVATE_SENTINEL"',
        b"\xff",
    ],
)
def test_parser_rejects_bounded_unsafe_inputs(raw):
    with pytest.raises(ValueError) as error:
        report_schema.parse_report(raw)
    assert len(str(error.value)) < 100
    assert "PRIVATE_SENTINEL" not in str(error.value)


def test_parser_rejects_forged_identity():
    value = report()
    value["observation_identity"] = "c" * 64
    with pytest.raises(ValueError):
        report_schema.parse_report(json.dumps(value).encode())


@pytest.mark.parametrize(
    "case,classification",
    [
        ("source", "blocking"),
        ("dirty", "unknown"),
        ("provenance", "unknown"),
        ("guidance", "blocking"),
        ("edition", "blocking"),
        ("client-version", "unknown"),
        ("runtime-range", "informational"),
        ("runtime-exact", "blocking"),
        ("runtime-missing", "blocking"),
        ("platform", "expected-platform"),
        ("platform-unknown", "unknown"),
        ("platform-unsupported", "blocking"),
    ],
)
def test_drift_classification(case, classification):
    left, right = payload(), payload()
    if case in ("source", "dirty", "provenance"):
        key, value = {
            "source": ("source_revision", "c" * 40),
            "dirty": ("source_dirty", True),
            "provenance": ("source_revision", None),
        }[case]
        right["engine"][key] = value
        right["engine"]["current_process"][key] = value
        if value is None:
            right["engine"]["current_process"]["reasons"][key] = "provenance-unavailable"
    elif case == "guidance":
        right["project"]["guidance"][0].update(observed_sha256=None, state="mismatch")
        right["project"]["guidance"][0]["reasons"]["observed_sha256"] = "safe-digest-unavailable"
    elif case == "edition":
        right["clients"][0]["edition"] = "desktop"
    elif case == "client-version":
        right["clients"][0]["version"]["observed"] = "1.0.1"
    elif case.startswith("runtime"):
        version = right["runtimes"][0]["version"]
        version["observed"] = "3.13.0"
        if case == "runtime-exact":
            version["intended"] = "3.12.1"
        if case == "runtime-missing":
            version.update(observed=None, state="missing", reason="not-found")
    else:
        right["platform"]["os"] = "macos"
        if case == "platform-unknown":
            right["project"]["components"][0]["platform_support"]["os"] = None
        if case == "platform-unsupported":
            right["project"]["components"][0]["platform_support"]["os"] = ["linux"]
    result = compare(left, right)
    assert classification in {f["class"] for f in result["findings"]}
    assert report_compare.comparison_exit_code(result) == (
        0 if case in ("runtime-range", "platform") else 1
    )


def test_matching_broken_reports_still_fail():
    value = payload()
    value["runtimes"][0]["version"].update(observed=None, state="missing", reason="not-found")
    result = compare(value, value)
    assert report_compare.comparison_exit_code(result) == 1
    assert any(f["class"] == "blocking" for f in result["findings"])


def test_optional_unknown_does_not_block_required_comparison():
    value = payload()
    value["runtimes"].append(
        {
            "id": "optional",
            "required": False,
            "version": {
                "intended": None,
                "observed": None,
                "state": "unknown",
                "reason": "not-assessed",
            },
        }
    )
    result = compare(value, value)
    assert any(f["class"] == "unknown" for f in result["findings"])
    assert report_compare.comparison_exit_code(result) == 0


def test_array_order_is_canonical_and_requiredness_is_desired_identity():
    value = payload()
    value["runtimes"].append(
        {
            "id": "node",
            "required": False,
            "version": {"intended": "22", "observed": "22.0", "state": "observed", "reason": None},
        }
    )
    original = report_schema.finalize_report(value)
    value["runtimes"].reverse()
    assert report_schema.report_bytes(
        report_schema.finalize_report(value)
    ) == report_schema.report_bytes(original)
    value["runtimes"][0]["required"] = True
    assert (
        report_schema.finalize_report(value)["configuration_identity"]
        != original["configuration_identity"]
    )


@pytest.mark.parametrize("collection", ["profile", "sources"])
def test_unknown_source_digest_does_not_hide_known_pin_drift(collection):
    def add_source(value, commit):
        source = {
            "id": "team",
            "commit": commit * 40,
            "content_sha256": None,
            "state": "unknown",
            "reasons": {"id": None, "commit": None, "content_sha256": "safe-digest-unavailable"},
        }
        value[collection] = source if collection == "profile" else [source]

    left, right = payload(), payload()
    add_source(left, "a")
    add_source(right, "b")
    result = compare(left, right)
    assert not result["configuration_complete"]
    assert any(
        f["field"].endswith("commit") and f["class"] == "blocking" for f in result["findings"]
    )


def test_optional_limitations_cannot_hide_required_collection_failure():
    value = payload()
    value["limitations"].append(
        {"field": "sources", "reason_code": "cache-corrupt", "required": False}
    )
    result = compare(value, value)
    assert not result["configuration_complete"]
    assert report_compare.comparison_exit_code(result) == 1


def test_auth_difference_is_informational_and_identity_independent():
    left = payload()
    left["auth"] = [
        {
            "kind": "client",
            "id": "codex",
            "credential_presence": "present",
            "verification": "not-assessed",
            "verified_at": None,
            "evidence_identity": None,
            "reasons": {
                "id": None,
                "verified_at": "not-assessed",
                "evidence_identity": "not-assessed",
            },
        }
    ]
    right = copy.deepcopy(left)
    right["auth"][0]["credential_presence"] = "missing"
    result = compare(left, right)
    assert {f["class"] for f in result["findings"] if f["field"].startswith("auth.")} == {
        "informational"
    }
    assert report_compare.comparison_exit_code(result) == 0


@pytest.mark.parametrize(
    "version,constraint,want",
    [
        ("3.12.0", "3.12", True),
        ("3.12.1", "==3.12", False),
        ("3.12", ">3.12", False),
        ("3.13", ">3.12,<=3.13", True),
        ("3.10", ">=3.9,<4", True),
        ("4.0", ">=3.9,<4", False),
    ],
)
def test_numeric_version_comparison(version, constraint, want):
    assert report_schema.version_satisfies(version, constraint) is want


def test_null_runtime_identifier_requires_explicit_redaction_scope():
    value = payload()
    value["runtimes"][0]["id"] = None
    with pytest.raises(ValueError):
        report_schema.finalize_report(value)
    value["limitations"] = [
        {"field": "runtimes", "reason_code": "identifier-redacted", "required": True}
    ]
    assert report_schema.completeness(report_schema.finalize_report(value)) == (False, False)


def test_known_guidance_digest_mismatch_is_blocking_even_with_unknown_state():
    value = payload()
    value["project"]["guidance"][0].update(observed_sha256="c" * 64, state="unknown")
    result = compare(value, value)
    assert any(f["class"] == "blocking" and "guidance" in f["field"] for f in result["findings"])


def test_incomplete_context_cannot_claim_verified_native_authentication():
    value = report()
    value["platform"]["shell_family"] = None
    value["platform"]["reasons"]["shell_family"] = "not-assessed"
    value = report_schema.finalize_report(value)
    value["auth"] = [
        {
            "kind": "client",
            "id": "codex",
            "credential_presence": "present",
            "verification": "verified",
            "verified_at": value["observed_at"],
            "evidence_identity": {
                "configuration_identity": value["configuration_identity"],
                "observation_identity": value["observation_identity"],
            },
            "reasons": {"id": None, "verified_at": None, "evidence_identity": None},
        }
    ]
    with pytest.raises(ValueError):
        report_schema.finalize_report(value)


def test_client_constraint_violation_is_blocking_on_matching_reports():
    value = payload()
    value["clients"][0]["version"]["intended"] = "2.0"
    result = compare(value, value)
    assert any(
        f["class"] == "blocking" and f["reason_code"] == "constraint-violation"
        for f in result["findings"]
    )


def test_unknown_client_edition_is_incomplete():
    value = payload()
    value["clients"][0]["edition"] = None
    value["clients"][0]["reasons"]["edition"] = "not-assessed"
    result = compare(value, value)
    assert result["configuration_complete"]
    assert not result["observation_complete"]
    assert any(
        f["field"] == "clients.codex.edition" and f["class"] == "unknown"
        for f in result["findings"]
    )


@pytest.mark.parametrize(
    "reason", ["invalid-configuration", "unsupported-version", "conflicting-declarations"]
)
def test_invalid_constraint_scope_is_not_an_unconstrained_complete_declaration(reason):
    value = payload()
    value["runtimes"][0]["version"]["intended"] = None
    value["limitations"] = [
        {"field": "runtimes.python.intended", "reason_code": reason, "required": False}
    ]
    result = compare(value, value)
    assert not result["configuration_complete"]


def test_unknown_project_constraint_reason_invalidates_configuration():
    value = payload()
    value["project"]["engine_constraint"] = None
    value["project"]["reasons"]["engine_constraint"] = "unsupported-version"
    assert not report_schema.completeness(report_schema.finalize_report(value))[0]


def test_unknown_identifiers_aggregate_once_per_auth_collection():
    value = payload()
    value["auth"] = [
        {
            "kind": kind,
            "id": None,
            "credential_presence": "unknown",
            "verification": "not-assessed",
            "verified_at": None,
            "evidence_identity": None,
            "reasons": {
                "id": "identifier-redacted",
                "verified_at": "not-assessed",
                "evidence_identity": "not-assessed",
            },
        }
        for kind in ("provider", "client")
    ]
    with pytest.raises(ValueError):
        report_schema.finalize_report(value)


def test_collection_limits_and_invalid_json_scalar_types():
    value = payload()
    value["sources"] = [
        {
            "id": f"source-{index}",
            "commit": "a" * 40,
            "content_sha256": "b" * 64,
            "state": "known",
            "reasons": {"id": None, "commit": None, "content_sha256": None},
        }
        for index in range(17)
    ]
    with pytest.raises(ValueError):
        report_schema.finalize_report(value)
    for raw in (b'{"schema_version":1.0}', b'{"x":Infinity}', b'{"x":1,"x":2}'):
        with pytest.raises(ValueError):
            report_schema.parse_report(raw)


def test_unavailable_native_recipe_is_not_complete_configuration():
    value = payload()
    item = value["project"]["guidance"][0]
    item["kind"] = "native-server"
    item["native_server"] = {
        "alias": "issues",
        "provider": "github",
        "transport": "stdio",
        "recipe_identity": None,
        "reasons": {
            "alias": None,
            "provider": None,
            "transport": None,
            "recipe_identity": "safe-digest-unavailable",
        },
    }
    result = compare(value, value)
    assert not result["configuration_complete"]
    assert any(
        f["field"].endswith("recipe_identity") and f["class"] == "unknown"
        for f in result["findings"]
    )


def test_release_source_same_version_cannot_mask_code_identity():
    left, right = payload(), payload()
    release = right["engine"]["current_process"]
    release.update(
        installation_kind="release",
        source_revision=None,
        source_dirty=None,
        artifact_sha256="d" * 64,
    )
    release["reasons"].update(
        source_revision="not-applicable", source_dirty="not-applicable", artifact_sha256=None
    )
    for key in ("installation_kind", "source_revision", "source_dirty", "artifact_sha256"):
        right["engine"][key] = release[key]
    result = compare(left, right)
    assert any(
        f["field"] == "engine.current_process.installation_kind" and f["class"] == "blocking"
        for f in result["findings"]
    )


def test_limitations_keep_distinct_safe_reasons_visible():
    value = payload()
    value["limitations"] = [
        {"field": "runtimes.python", "reason_code": reason, "required": True}
        for reason in ("probe-timeout", "output-limit")
    ]
    result = compare(value, value)
    assert {"probe-timeout", "output-limit"} <= {f["reason_code"] for f in result["findings"]}


def test_unknown_native_observations_are_visible_without_blocking_coverage():
    value = payload()
    result = compare(value, value)
    assert {"clients.codex.recognized", "clients.codex.authenticated"} <= {
        f["field"] for f in result["findings"] if f["class"] == "unknown"
    }
    assert report_compare.comparison_exit_code(result) == 0


def test_known_profile_enrollment_difference_is_blocking():
    left, right = payload(), payload()
    right["profile"] = {
        "id": "team",
        "commit": "a" * 40,
        "content_sha256": "b" * 64,
        "state": "known",
        "reasons": {"id": None, "commit": None, "content_sha256": None},
    }
    result = compare(left, right)
    assert any(f["field"] == "profile" and f["class"] == "blocking" for f in result["findings"])


def test_equal_unknown_credential_presence_remains_visible_and_optional():
    value = payload()
    value["auth"] = [
        {
            "kind": "provider",
            "id": "github",
            "credential_presence": "unknown",
            "verification": "not-assessed",
            "verified_at": None,
            "evidence_identity": None,
            "reasons": {
                "id": None,
                "verified_at": "not-assessed",
                "evidence_identity": "not-assessed",
            },
        }
    ]
    result = compare(value, value)
    assert any(
        f["field"] == "auth.provider.github.credential_presence" and f["class"] == "unknown"
        for f in result["findings"]
    )
    assert report_compare.comparison_exit_code(result) == 0
