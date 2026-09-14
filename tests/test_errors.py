"""One exception base and one result envelope shared by the CLI and MCP."""

import json

import pytest
from typer.testing import CliRunner

from ai_dlc.contracts import FAILURE_STATUSES, ServiceResult, succeeded
from ai_dlc.errors import AiDlcError, RefusedError, UncertainError


def test_every_custom_exception_derives_from_the_base_and_keeps_its_legacy_base():
    from ai_dlc.files import GitError
    from ai_dlc.harness.components import MissingComponentGuidance
    from ai_dlc.harness.user_agents import UserAgentOwnershipConflict
    from ai_dlc.harness.workflow_bundles import MissingBundlePath
    from ai_dlc.providers.jira_cloud import JiraFieldError, JiraRefusal, JiraUncertain
    from ai_dlc.providers.plane import PlaneUncertain
    from ai_dlc.setup.project import RuntimeUnavailable

    refused = [JiraRefusal, JiraFieldError, MissingBundlePath, MissingComponentGuidance]
    refused.append(UserAgentOwnershipConflict)
    uncertain = [JiraUncertain, PlaneUncertain, RuntimeUnavailable]
    for cls in [*refused, *uncertain, GitError]:
        assert issubclass(cls, AiDlcError), cls
        assert cls.exit_code == 2
    assert all(issubclass(cls, RefusedError) and issubclass(cls, ValueError) for cls in refused)
    assert all(
        issubclass(cls, UncertainError) and issubclass(cls, RuntimeError) for cls in uncertain
    )
    assert issubclass(GitError, ValueError) and issubclass(GitError, RuntimeError)


@pytest.mark.parametrize(
    "result,expected",
    [
        ({"status": "completed"}, True),
        ({"status": "planned", "plan": {}}, True),
        ({"path": "x"}, True),
        ({}, True),
        *[({"status": status}, False) for status in sorted(FAILURE_STATUSES)],
        ({"valid": True}, True),
        ({"valid": False, "errors": ["x"]}, False),
        ({"ready": False, "status": "started"}, False),
        ({"passed": True, "status": "failed"}, True),
        ({"clean": False}, False),
    ],
)
def test_succeeded_reads_the_envelope_with_verdict_keys_authoritative(result, expected):
    assert succeeded(result) is expected
    assert ServiceResult.model_validate(result).model_dump(exclude_none=True) == result


def test_generated_envelope_schema_allows_extra_fields_and_names_every_verdict_key():
    schema = ServiceResult.model_json_schema()
    assert schema["additionalProperties"] is True
    assert set(schema["properties"]) == {"status", "valid", "ready", "passed", "clean"}


class _Boom(AiDlcError):
    exit_code = 3


@pytest.mark.parametrize(
    "error,code,stderr",
    [
        (ValueError("bad input"), 2, "Error: bad input\n"),
        (RuntimeError("remote failed"), 2, "Error: remote failed\n"),
        (OSError("disk"), 2, "Error: disk\n"),
        (TypeError("shape"), 2, "Error: shape\n"),
        (RefusedError("refused"), 2, "Error: refused\n"),
        (_Boom("custom"), 3, "Error: custom\n"),
    ],
)
def test_service_call_reports_every_failure_once_with_the_error_exit_code(error, code, stderr):
    import typer

    from ai_dlc.cli import service_call

    app = typer.Typer()

    @app.command()
    def run():
        with service_call():
            raise error

    result = CliRunner().invoke(app, [])
    assert result.exit_code == code
    assert result.stderr == stderr
    assert result.stdout == ""


def test_service_call_echoes_exception_notes_after_the_message():
    import typer

    from ai_dlc.cli import service_call

    app = typer.Typer()

    @app.command()
    def run():
        with service_call():
            error = RefusedError("bundle source is invalid")
            error.add_note("Bundle import retained .ai-dlc/bundles/x; inspect before removal.")
            raise error

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 2
    assert result.stderr == (
        "Error: bundle source is invalid\n"
        "Bundle import retained .ai-dlc/bundles/x; inspect before removal.\n"
    )


@pytest.mark.parametrize("result,code", [({"status": "completed"}, 0), ({"status": "blocked"}, 1)])
def test_conclude_emits_the_result_and_maps_the_envelope_to_exit_status(result, code):
    import typer

    from ai_dlc.cli import conclude

    app = typer.Typer()

    @app.command()
    def run():
        conclude(result)

    outcome = CliRunner().invoke(app, [])
    assert outcome.exit_code == code
    assert json.loads(outcome.stdout) == result


def test_unexpected_exceptions_are_not_swallowed_by_the_handler():
    from ai_dlc.cli import service_call

    with pytest.raises(KeyError), service_call():
        raise KeyError("programming error")
