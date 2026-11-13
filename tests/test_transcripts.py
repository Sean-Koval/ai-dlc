"""The ``transcripts`` role: Zoom and Google Meet providers and ``pull-transcripts`` (KAN-457).

Fakes behind ``httpx.MockTransport`` replay recorded API responses from
``tests/fixtures/transcripts``. A socket guard fails any real connection, so these
tests prove nothing about live OAuth scopes or recording access.
"""

import hashlib
import json
import socket
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from ai_dlc.cli import app
from ai_dlc.contracts import manifest, validate_response
from ai_dlc.documentation import knowledge_records as records
from ai_dlc.documentation.knowledge_check import check_records
from ai_dlc.documentation.knowledge_transcripts import TranscriptPull, parse_since, route
from ai_dlc.providers import Registry, transcripts_common
from ai_dlc.providers.google_meet import GoogleMeet, parse
from ai_dlc.providers.transcripts_common import (
    TranscriptRefusal,
    TranscriptUnavailable,
    vtt_segments,
)
from ai_dlc.providers.zoom import Zoom, meeting_path

FIXTURES = Path(__file__).parent / "fixtures" / "transcripts"
TOKEN = "fake-oauth-token-value"
SINCE = datetime(2026, 11, 1, tzinfo=UTC)
NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
CONFIG = {
    "roles": {"transcripts": ["zoom", "meet"], "knowledge": "records"},
    "providers": {
        "zoom": {"kind": "zoom", "auth_mode": "oauth_bearer", "token_env": "ZOOM_TOKEN"},
        "meet": {
            "kind": "google-meet",
            "auth_mode": "oauth_bearer",
            "token_env": "GOOGLE_MEET_TOKEN",
        },
    },
}
ENV = {"ZOOM_TOKEN": TOKEN, "GOOGLE_MEET_TOKEN": TOKEN}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a transcripts test opened a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)


class FakeZoom:
    def __init__(self):
        self.data = json.loads((FIXTURES / "zoom.json").read_text())
        self.meetings = {m["uuid"]: m for page in self.data["recordings"] for m in page["meetings"]}
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.raw_path.decode().split("?", 1)[0]
        if request.url.host == "ssrweb.zoom.us":
            assert "authorization" not in request.headers, "token sent off the API host"
            return httpx.Response(200, text=(FIXTURES / path.rsplit("/", 1)[-1]).read_text())
        assert request.headers["authorization"] == "Bearer " + TOKEN
        if path == "/v2/users/me/recordings":
            page = 1 if request.url.params.get("next_page_token") == "page-2" else 0
            return httpx.Response(200, json=self.data["recordings"][page])
        for uuid, meeting in self.meetings.items():
            encoded = meeting_path(uuid)
            if path == f"/v2/past_meetings/{encoded}/participants":
                people = self.data["participants"].get(uuid)
                if people is None:
                    return httpx.Response(404, json={"code": 3001})
                return httpx.Response(200, json={"participants": people})
            if path == f"/v2/meetings/{encoded}/recordings":
                return httpx.Response(200, json=meeting)
        if path.startswith("/rec/download/"):
            name = self.data["downloads"].get(path)
            if name is None:
                return httpx.Response(403, json={"message": "no access " + TOKEN})
            return httpx.Response(302, headers={"location": f"https://ssrweb.zoom.us/f/{name}"})
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))


class FakeDrive:
    def __init__(self):
        self.data = json.loads((FIXTURES / "drive.json").read_text())
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert request.headers["authorization"] == "Bearer " + TOKEN
        path = request.url.path
        if path == "/drive/v3/files":
            query = request.url.params["q"]
            assert "createdTime >= '2026-11-01T00:00:00'" in query
            assert request.url.params["supportsAllDrives"] == "true"
            return httpx.Response(200, json={"files": self.data["files"]})
        for row in self.data["files"]:
            if path == f"/drive/v3/files/{row['id']}/export":
                name = self.data["exports"].get(row["id"])
                if name is None:
                    return httpx.Response(403, json={"error": {"message": "denied"}})
                return httpx.Response(200, text=(FIXTURES / name).read_text(encoding="utf-8"))
            if path == f"/drive/v3/files/{row['id']}":
                return httpx.Response(200, json=row)
        return httpx.Response(404)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self.handle))


ALPHA = '[[transcripts.customers]]\nproject = "alpha"\nparticipants = ["@alpha.example"]\n'


def knowledge_repo(tmp_path: Path, routes: str = ALPHA, name: str = "knowledge") -> Path:
    root = tmp_path / name
    for folder in ("team", "projects", "inbox"):
        (root / folder).mkdir(parents=True)
    (root / "knowledge.toml").write_text(
        '[format]\nversion = 1\n[check]\nroots = ["team", "projects"]\n'
        f'[transcripts]\nowner = "ana"\nscope = "team"\n{routes}'
    )
    return root


def customer_env(tmp_path: Path) -> tuple[Path, dict]:
    alpha = knowledge_repo(tmp_path, "", name="knowledge-alpha")
    return alpha, {**ENV, "KNOWLEDGE_REPO_ALPHA": str(alpha)}


def registry(zoom: FakeZoom, drive: FakeDrive) -> Registry:
    found = Registry(CONFIG, environ=ENV)
    found.register(
        "zoom", Zoom(CONFIG["providers"]["zoom"], client=zoom.client(), environ=ENV, now=NOW)
    )
    found.register(
        "meet", GoogleMeet(CONFIG["providers"]["meet"], client=drive.client(), environ=ENV)
    )
    return found


# The role contract


def test_manifest_declares_the_transcripts_role():
    role = manifest()["roles"]["transcripts"]
    assert role == {"mandatory": ["list_since", "fetch"], "optional": []}


def test_fetch_response_needs_speakers_and_timestamps():
    base = {"id": "x", "title": "T", "start": "2026-11-10T15:00:00Z"}
    ok = validate_response(
        "fetch", {**base, "segments": [{"speaker": "A", "at": "0:00:01", "text": "hi"}]}
    )
    assert ok["segments"][0]["at"] == "0:00:01"
    with pytest.raises(ValueError):
        validate_response("fetch", {**base, "segments": []})
    with pytest.raises(ValueError):
        validate_response(
            "fetch", {**base, "segments": [{"speaker": "A", "at": "1s", "text": "x"}]}
        )


# Zoom


def test_zoom_lists_only_transcribed_meetings_since_the_time():
    fake = FakeZoom()
    zoom = Zoom(CONFIG["providers"]["zoom"], client=fake.client(), environ=ENV, now=NOW)
    listed = validate_response("list_since", zoom.list_since(SINCE))["items"]
    assert [item["id"] for item in listed] == ["/aB+c//dE==", "Qx9YzZalpha==", "lockedMeeting=="]
    assert listed[0]["participants"] == ["Ana", "Priya"]
    assert listed[1]["emails"] == ["ana@example.com", "bob@alpha.example"]
    assert listed[2]["participants"] == []  # no participant scope or record: speakers fill in
    window = fake.requests[0].url.params
    assert (window["from"], window["to"]) == ("2026-10-31", "2026-11-14")


def test_zoom_fetch_parses_vtt_and_double_encodes_the_uuid():
    fake = FakeZoom()
    zoom = Zoom(CONFIG["providers"]["zoom"], client=fake.client(), environ=ENV, now=NOW)
    transcript = validate_response("fetch", zoom.fetch("/aB+c//dE=="))
    assert transcript["segments"] == [
        {
            "speaker": "Ana",
            "at": "00:00:01",
            "text": "Let's pin the harness to r3 for the release.",
        },
        {
            "speaker": "Priya",
            "at": "00:00:05",
            "text": "Agreed. I'll update the lock and open the PR today.",
        },
        {"speaker": "Unknown", "at": "00:01:02", "text": "Release day stays Thursday."},
    ]
    paths = [r.url.raw_path.decode() for r in fake.requests]
    assert "/v2/meetings/%252FaB%252Bc%252F%252FdE%253D%253D/recordings" in paths


def test_zoom_unreadable_transcript_is_unavailable_without_leaking():
    fake = FakeZoom()
    zoom = Zoom(CONFIG["providers"]["zoom"], client=fake.client(), environ=ENV, now=NOW)
    with pytest.raises(TranscriptUnavailable) as caught:
        zoom.fetch("lockedMeeting==")
    assert "403" in str(caught.value) and TOKEN not in str(caught.value)


def test_vtt_without_speakers_keeps_the_text():
    assert vtt_segments("WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\nhello\n") == [
        {"speaker": "Unknown", "at": "00:00:01", "text": "hello"}
    ]


# Google Meet


def test_meet_export_parses_attendees_marks_and_speakers():
    text = (FIXTURES / "meet-design-review.txt").read_text(encoding="utf-8")
    attendees, segments = parse(text)
    assert attendees == ["Ana Ruiz", "Priya Rao", "Dana Lee"]
    assert segments[1] == {
        "speaker": "Priya Rao",
        "at": "00:00:00",
        "text": "Fine by me. It matches the GitHub app.",
    }
    assert segments[-1] == {"speaker": "Ana Ruiz", "at": "00:05:12", "text": "I will, by Friday."}


def test_meet_lists_transcript_docs_and_skips_unexportable_on_fetch():
    fake = FakeDrive()
    meet = GoogleMeet(CONFIG["providers"]["meet"], client=fake.client(), environ=ENV)
    listed = validate_response("list_since", meet.list_since(SINCE))["items"]
    assert [i["id"] for i in listed] == ["1DesignReviewDocId0001", "1SharedButLockedDoc003"]
    assert listed[0]["title"] == "Design review - 2026/11/10 10:00 EST"
    assert listed[0]["participants"] == ["Ana Ruiz", "Priya Rao", "Dana Lee"]
    with pytest.raises(TranscriptUnavailable):
        meet.fetch("1SharedButLockedDoc003")
    fetched = validate_response("fetch", meet.fetch("1DesignReviewDocId0001"))
    assert len(fetched["segments"]) == 4


# Credentials


@pytest.mark.parametrize("cls", [Zoom, GoogleMeet])
def test_credentials_are_named_never_guessed_and_never_shown(cls):
    with pytest.raises(TranscriptRefusal, match="auth_mode"):
        cls({"token_env": "T"}, environ={"T": TOKEN})
    with pytest.raises(TranscriptRefusal, match="token_env"):
        cls({"auth_mode": "oauth_bearer", "token": TOKEN}, environ={})
    with pytest.raises(TranscriptRefusal, match="not populated") as caught:
        cls({"auth_mode": "oauth_bearer", "token_env": "MISSING"}, environ={})
    assert TOKEN not in str(caught.value)


def test_a_refused_list_names_scopes_not_the_token():
    def handle(request):
        return httpx.Response(401, json={"message": "bad " + TOKEN})

    meet = GoogleMeet(
        CONFIG["providers"]["meet"],
        client=httpx.Client(transport=httpx.MockTransport(handle)),
        environ=ENV,
    )
    with pytest.raises(TranscriptRefusal, match="OAuth scopes") as caught:
        meet.list_since(SINCE)
    assert TOKEN not in str(caught.value)


# pull-transcripts


def md_files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md"))


def test_pull_writes_source_records_once_and_skips_unreadable(tmp_path):
    root = knowledge_repo(tmp_path)
    alpha, environ = customer_env(tmp_path)

    def run():
        reg = registry(FakeZoom(), FakeDrive())
        return TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=environ).pull(
            "2026-11-01"
        )

    first = run()
    assert first["status"] == "ok", first
    written = {entry["id"]: entry for entry in first["written"]}
    assert set(written) == {"/aB+c//dE==", "Qx9YzZalpha==", "1DesignReviewDocId0001"}
    assert {(e["provider"], e["id"]) for e in first["skipped"]} == {
        ("zoom", "lockedMeeting=="),
        ("meet", "1SharedButLockedDoc003"),
    }

    team = written["/aB+c//dE=="]
    assert team["repository"] == str(root) and team["project"] is None
    assert team["record"].startswith("inbox/transcripts/zoom-20261110-")
    record, _body = records.parse((root / team["record"]).read_text())
    assert record.type == "source" and record.status == "raw" and record.scope == "team"
    assert record.boundary is None and record.project is None
    assert record.participants == ["Ana", "Priya"]
    assert record.sources[0].id == "zoom:/aB+c//dE=="
    assert record.sources[0].resource == team["payload"]
    assert records.payload_expires(record)
    payload = (root / team["payload"]).read_text()
    assert "[00:00:05] Priya: Agreed. I'll update the lock and open the PR today." in payload
    assert record.sources[0].hash == "sha256:" + hashlib.sha256(payload.encode()).hexdigest()
    assert "ana@example.com" not in (root / team["record"]).read_text()

    # The customer transcript lands in the customer's own repository, top-level inbox.
    customer = written["Qx9YzZalpha=="]
    assert customer["repository"] == str(alpha) and customer["project"] == "alpha"
    assert customer["record"].startswith("inbox/transcripts/")
    customer_record, _ = records.parse((alpha / customer["record"]).read_text())
    assert customer_record.boundary == "customer" and customer_record.project == "alpha"
    assert customer_record.scope == "project"
    assert "bob@alpha.example" not in (alpha / customer["record"]).read_text()
    assert not list((root / "projects").rglob("*"))  # nothing enters projects/*
    team_files = [p.as_posix() for p in root.rglob("*") if p.is_file()]
    assert not any("Qx9YzZalpha" in (Path(f).read_text()) for f in team_files)

    again = run()
    assert again["written"] == [] and len(again["existing"]) == 3
    assert len(md_files(root)) == 2 and len(md_files(alpha)) == 1

    # Every output record passes knowledge check: the repositories' own (inbox is not a
    # root) and, for the team repository, with the inbox read as records.
    assert check_records(root)["status"] == "valid"
    assert check_records(alpha)["status"] == "valid"
    everything = root / "check-all.toml"
    everything.write_text("[format]\nversion = 1\n")
    checked = check_records(root, config=everything)
    assert checked["status"] == "valid" and checked["records"] == 2, checked["failures"]


def test_unconfigured_customer_repository_skips_and_never_falls_back(tmp_path):
    root = knowledge_repo(tmp_path)
    reg = registry(FakeZoom(), FakeDrive())
    result = TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=ENV).pull(
        "2026-11-01"
    )
    skipped = {entry["id"]: entry["reason"] for entry in result["skipped"]}
    assert "KNOWLEDGE_REPO_ALPHA" in skipped["Qx9YzZalpha=="]
    assert all(entry["id"] != "Qx9YzZalpha==" for entry in result["written"])
    assert not any("Qx9YzZalpha" in p.read_text() for p in root.rglob("*") if p.is_file())

    not_a_repo = tmp_path / "empty"
    not_a_repo.mkdir()
    environ = {**ENV, "KNOWLEDGE_REPO_ALPHA": str(not_a_repo)}
    reg = registry(FakeZoom(), FakeDrive())
    again = TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=environ).pull(
        "2026-11-01"
    )
    assert any("not name a knowledge repository" in e["reason"] for e in again["skipped"])


def test_retired_project_routes_are_refused(tmp_path):
    routes = '[[transcripts.projects]]\nname = "alpha"\ntitles = ["x"]\n'
    root = knowledge_repo(tmp_path, routes)
    reg = registry(FakeZoom(), FakeDrive())
    result = TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=ENV).pull(
        "2026-11-01"
    )
    assert result["status"] == "refused" and "retired" in result["reason"]


def test_dry_run_writes_nothing(tmp_path):
    root = knowledge_repo(tmp_path)
    alpha, environ = customer_env(tmp_path)
    reg = registry(FakeZoom(), FakeDrive())
    pull = TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=environ)
    result = pull.pull("2026-11-01T00:00:00+00:00", dry_run=True)
    assert result["written"] == [] and len(result["planned"]) == 5
    assert [e["project"] for e in result["planned"]].count("alpha") == 1
    assert not md_files(root) and not md_files(alpha)


def test_two_customers_matching_one_transcript_skip_it(tmp_path):
    routes = (
        '[[transcripts.customers]]\nproject = "alpha"\ntitles = ["review"]\n'
        '[[transcripts.customers]]\nproject = "beta"\ntitles = ["design"]\n'
    )
    root = knowledge_repo(tmp_path, routes)
    reg = registry(FakeZoom(), FakeDrive())
    result = TranscriptPull(
        tmp_path, CONFIG, providers=["meet"], into=root, registry=reg, environ=ENV
    ).pull("2026-11-01")
    assert result["written"] == []
    assert any("several customers" in entry["reason"] for entry in result["skipped"])


def test_route_matches_title_or_participant_email():
    customers = [
        {"project": "alpha", "titles": [], "participants": ["@alpha.example"]},
        {"project": "beta", "titles": ["beta sync"], "participants": []},
    ]
    item = {"title": "Sync", "participants": ["Bob"], "emails": ["bob@alpha.example"]}
    assert route(item, customers)["project"] == "alpha"
    assert route({"title": "Beta sync"}, customers)["project"] == "beta"
    assert route({"title": "other"}, customers) is None


def test_since_needs_an_offset_and_config_needs_an_owner(tmp_path):
    with pytest.raises(ValueError, match="offset"):
        parse_since("2026-11-01T09:00:00")
    root = tmp_path / "k"
    root.mkdir()
    (root / "knowledge.toml").write_text("[format]\nversion = 1\n")
    pull = TranscriptPull(tmp_path, CONFIG, into=root, registry=registry(FakeZoom(), FakeDrive()))
    assert pull.pull("2026-11-01") == {
        "status": "refused",
        "reason": "declare [transcripts] owner in knowledge.toml before pulling",
    }


def test_no_transcripts_provider_is_refused(tmp_path):
    with pytest.raises(ValueError, match="transcripts role"):
        TranscriptPull(tmp_path, {"roles": {}})


def test_cli_pulls_through_the_project_configuration(tmp_path, monkeypatch):
    fake = FakeDrive()
    real = httpx.Client
    monkeypatch.setattr(
        transcripts_common.httpx,
        "Client",
        lambda **kwargs: real(transport=httpx.MockTransport(fake.handle)),
    )
    monkeypatch.setenv("GOOGLE_MEET_TOKEN", TOKEN)
    knowledge = knowledge_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "ai-dlc.toml").write_text(
        'schema = 4\n[roles]\ntranscripts = "meet"\n'
        '[providers.meet]\nkind = "google-meet"\nauth_mode = "oauth_bearer"\n'
        'token_env = "GOOGLE_MEET_TOKEN"\n'
    )
    runner = CliRunner()
    arguments = [
        "knowledge",
        "pull-transcripts",
        "--since",
        "2026-11-01",
        "--into",
        str(knowledge),
        "--root",
        str(project),
    ]
    first = runner.invoke(app, arguments)
    assert first.exit_code == 0, first.output
    assert "skipped meet 1SharedButLockedDoc003" in first.stderr
    assert TOKEN not in first.output
    assert len(json.loads(first.stdout)["written"]) == 1
    second = runner.invoke(app, arguments)
    assert second.exit_code == 0 and json.loads(second.stdout)["written"] == []


def test_record_project_needs_the_customer_boundary():
    base = {
        "id": "x",
        "type": "lesson",
        "scope": "project",
        "status": "open",
        "date": "2026-11-13",
        "owner": "ana",
        "sources": [{"resource": "inbox/x.txt"}],
        "links": [],
    }
    assert records.errors({**base, "boundary": "customer", "project": "alpha"}) == []
    assert any("project" in e for e in records.errors({**base, "project": "alpha"}))
    assert records.errors({**base, "boundary": "customer", "project": "Not A Slug"})
