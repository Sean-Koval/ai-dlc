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
from ai_dlc.documentation.knowledge_transcripts import TranscriptPull, parse_since, route, routing
from ai_dlc.errors import RefusedError, UncertainError
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
        f'[transcripts]\nowner = "ana"\nscope = "team"\ninternal = ["@example.com", "Ana Ruiz", "Priya Rao", "Dana Lee"]\n{routes}'
    )
    return root


def customer_repo_dir(tmp_path: Path, project: str = "alpha") -> Path:
    """A customer repository as ``knowledge init --customer`` writes it (KAN-475)."""
    root = tmp_path / f"knowledge-{project}"
    for folder in (f"projects/{project}", "inbox"):
        (root / folder).mkdir(parents=True)
    (root / "knowledge.toml").write_text(
        f'[format]\nversion = 1\n[repo]\nboundary = "customer"\nproject = "{project}"\n'
        f'[check]\nroots = ["projects/{project}"]\n'
    )
    return root


def customer_env(tmp_path: Path) -> tuple[Path, dict]:
    alpha = customer_repo_dir(tmp_path)
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
    assert customer["project"] == "alpha"
    # Nothing in the result names the customer: no title, no local path (KAN-475).
    assert set(customer) == {"provider", "id", "project", "record"}
    assert str(alpha) not in json.dumps(first) and "Sync" not in json.dumps(first["written"])
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


def test_customer_variable_must_name_that_customers_declared_repository(tmp_path):
    # KAN-475: a variable pointing at the team repository, or at another customer's,
    # skips the transcript; it never lands there.
    root = knowledge_repo(tmp_path)
    beta = customer_repo_dir(tmp_path, project="beta")
    for wrong in (root, beta):
        environ = {**ENV, "KNOWLEDGE_REPO_ALPHA": str(wrong)}
        reg = registry(FakeZoom(), FakeDrive())
        result = TranscriptPull(tmp_path, CONFIG, into=root, registry=reg, environ=environ).pull(
            "2026-11-01"
        )
        skipped = {entry["id"]: entry["reason"] for entry in result["skipped"]}
        reason = skipped["Qx9YzZalpha=="]
        assert 'project = "alpha"' in reason or "team checkout" in reason
        for repo in (root, beta):
            assert not any("Qx9YzZalpha" in p.read_text() for p in repo.rglob("*") if p.is_file())


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
    # The two meetings with no readable participants cannot be proven internal (KAN-475).
    assert result["written"] == [] and len(result["planned"]) == 3
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
    internal = ["@example.com", "Dana Lee"]
    team = {"title": "other", "participants": ["Ana"], "emails": ["ana@example.com"]}
    assert route(team, customers, internal) is None
    assert route({"title": "other", "participants": ["Dana Lee"]}, customers, internal) is None
    # KAN-475: an unmapped meeting goes to the team only when everyone is internal.
    unmapped = (
        {"title": "Weekly sync", "participants": ["Ana", "Zed"], "emails": ["ana@example.com"]},
        {"title": "Weekly sync", "emails": ["ana@example.com", "zed@client.example"]},
        {"title": "Weekly sync", "participants": ["Zed Client"]},
        {"title": "Weekly sync"},
    )
    for item in unmapped:
        assert "not every participant is internal" in route(item, customers, internal)
    assert "not every participant" in route(team, customers)  # no internal list: deny
    # Look-alikes are not internal: exact domain or a subdomain, exact names.
    for domain in (["@corp.com"], ["corp.com"]):
        for email in ("bob@corp.com.attacker.io", "bob@notcorp.com", "bob@corp.co"):
            item = {"title": "x", "participants": ["Bob"], "emails": [email]}
            assert isinstance(route(item, customers, domain), str), (domain, email)
        ok = {"title": "x", "participants": ["Bob"], "emails": ["bob@eu.corp.com"]}
        assert route(ok, customers, domain) is None
    named = {"title": "x", "participants": ["Seana Smith"]}
    assert isinstance(route(named, customers, ["sean"]), str)
    assert route({"title": "x", "participants": ["Sean"]}, customers, ["Sean"]) is None
    exact = {"title": "x", "participants": ["A"], "emails": ["a@partner.io"]}
    assert route(exact, customers, ["a@partner.io"]) is None
    assert route({"title": "other"}, []) is None  # no customer rules: team only


def test_customer_rules_match_whole_title_words_and_exact_participants():
    # KAN-490: a substring match sent "Alphabet" to the Alpha customer's repository.
    customers = [
        {"project": "alpha", "titles": ["alpha"], "participants": ["@alpha.example"]},
        {"project": "beta", "titles": ["beta corp"], "participants": ["dana lee", "x@b.io"]},
    ]

    def project(item):
        found = route(item, customers, ["@example.com"])
        return found["project"] if isinstance(found, dict) else None

    matching = ("Alpha sync", "alpha: weekly", "Weekly (ALPHA)", "Ａｌｐｈａ review", "Alpha_sync")
    for title in (*matching, "Al\u00adpha sync", "Alpha\u200b sync"):
        assert project({"title": title, "emails": ["ana@example.com"]}) == "alpha", title
    for title in ("Alphabet", "alphanumeric planning", "Alpha2 sync", "Betacorp"):
        assert project({"title": title, "emails": ["ana@example.com"]}) is None, title
    assert project({"title": "Beta  Corp kickoff", "emails": ["ana@example.com"]}) == "beta"

    def by_email(email):
        return project({"title": "Sync", "participants": ["Bob"], "emails": [email]})

    assert by_email("bob@eu.alpha.example") == "alpha"
    assert by_email("Bob@Alpha.Example") == "alpha"
    for email in ("bob@alpha.example.evil.io", "bob@notalpha.example", "alpha.example@x.io"):
        assert by_email(email) is None, email
    assert by_email("x@b.io") == "beta" and by_email("xx@b.io") is None
    assert project({"title": "Sync", "participants": ["Dana  Lee"]}) == "beta"
    assert project({"title": "Sync", "participants": ["Dana Leeds"]}) is None
    # A provider that gives the address as the participant name.
    assert project({"title": "Sync", "participants": ["bob@alpha.example"]}) == "alpha"
    # With emails given, a display name a guest chose cannot claim a customer.
    spoof = {"title": "Sync", "participants": ["Dana Lee"], "emails": ["dana@else.io"]}
    assert project(spoof) is None


def test_a_title_rule_in_a_script_without_spaces_matches_inside_words():
    # KAN-490 review: Japanese and Chinese titles have no spaces between words.
    customers = [{"project": "alpha", "titles": ["アルファ", "阿尔法"], "participants": []}]
    for title in ("アルファ定例", "週次アルファ会議", "阿尔法周会"):
        found = route({"title": title, "emails": ["ana@example.com"]}, customers, [])
        assert isinstance(found, dict) and found["project"] == "alpha", title


def test_a_customer_term_inside_a_longer_word_is_skipped_not_sent_to_the_team():
    # KAN-490 review: an internal prep meeting about a customer stays out of the team
    # repository until a rule says where it goes.
    customers = [
        {"project": "alpha", "titles": ["alpha"], "participants": []},
        {"project": "beta", "titles": ["beta"], "participants": []},
    ]
    internal = ["@corp.com"]
    for title in (
        "AlphaCorp renewal prep",
        "Alphas QBR prep",
        "Alpha2026 planning",
        "Alphabet sync",
    ):
        found = route({"title": title, "emails": ["sean@corp.com"]}, customers, internal)
        assert isinstance(found, str) and "inside a longer word" in found, title
        assert "alpha" in found and title.casefold() not in found.casefold()
    # A whole-word match for one customer and a near miss for another: skipped too.
    both = route({"title": "Alpha and Betamax", "emails": ["sean@corp.com"]}, customers, internal)
    assert isinstance(both, str) and "beta" in both
    # The term also as a whole word still routes.
    found = route(
        {"title": "Alpha: AlphaCorp renewal", "emails": ["sean@corp.com"]}, customers, internal
    )
    assert isinstance(found, dict) and found["project"] == "alpha"
    assert route({"title": "Team sync", "emails": ["sean@corp.com"]}, customers, internal) is None


def test_a_latin_title_term_next_to_chinese_or_japanese_text_matches():
    customers = [{"project": "alpha", "titles": ["alpha"], "participants": []}]
    for title in ("Alpha社定例", "定例Alpha", "週次アルファAlpha会議"):
        found = route({"title": title, "emails": ["ana@example.com"]}, customers, [])
        assert isinstance(found, dict) and found["project"] == "alpha", title


def test_accents_and_a_joined_multi_word_term_never_send_a_meeting_to_the_team():
    # KAN-490 re-review: accents fold away on both sides, however they are encoded.
    customers = [
        {"project": "alpha", "titles": ["alpha"], "participants": []},
        {"project": "beta", "titles": ["beta corp"], "participants": []},
        {"project": "gamma", "titles": ["Gämma"], "participants": []},
    ]
    internal = ["@corp.com"]

    def routed(title):
        return route({"title": title, "emails": ["sean@corp.com"]}, customers, internal)

    for title, project in (
        ("Alpha\u0301 weekly", "alpha"),
        ("Alphá weekly", "alpha"),
        ("gamma sync", "gamma"),
        ("Ga\u0308mma sync", "gamma"),
    ):
        found = routed(title)
        assert isinstance(found, dict) and found["project"] == project, title
    joined = routed("BetaCorp renewal")
    assert isinstance(joined, str) and "inside a longer word" in joined and "beta" in joined
    # Thai vowels and Japanese voicing marks stay part of the word.
    kana = [{"project": "ga", "titles": ["ガ"], "participants": []}]
    assert route({"title": "カ定例", "emails": ["sean@corp.com"]}, kana, internal) is None


def test_a_one_word_participant_rule_warns_that_it_is_a_name(tmp_path):
    rule = '[[transcripts.customers]]\nproject = "alpha"\nparticipants = ["alpha", "Dana Lee"]\n'
    warnings = routing(knowledge_repo(tmp_path, rule))["warnings"]
    assert len(warnings) == 1 and "'alpha'" in warnings[0] and "@alpha.example" in warnings[0]
    assert routing(knowledge_repo(tmp_path, ALPHA, name="k2"))["warnings"] == []
    dotted = '[[transcripts.customers]]\nproject = "alpha"\nparticipants = ["alpha.example"]\n'
    assert routing(knowledge_repo(tmp_path, dotted, name="k3"))["warnings"] == []


def test_a_rule_naming_a_whole_top_level_domain_is_refused(tmp_path):
    for number, domain in enumerate(("@io", "@co.uk", "@com.au", "@co.jp")):
        bare = f'[[transcripts.customers]]\nproject = "alpha"\nparticipants = ["{domain}"]\n'
        with pytest.raises(RefusedError, match=f"participants '{domain}'"):
            routing(knowledge_repo(tmp_path, bare, name=f"k{number}"))
    allowed = '[[transcripts.customers]]\nproject = "alpha"\nparticipants = ["@alpha.co.uk"]\n'
    assert routing(knowledge_repo(tmp_path, allowed, name="ok"))["customers"]
    root = tmp_path / "bare-internal"
    root.mkdir()
    (root / "knowledge.toml").write_text(
        '[format]\nversion = 1\n[transcripts]\nowner = "ana"\ninternal = ["@example"]\n'
    )
    with pytest.raises(RefusedError, match="internal '@example'"):
        routing(root)
    (root / "knowledge.toml").write_text(
        '[format]\nversion = 1\n[transcripts]\nowner = "ana"\ninternal = ["@CO.UK"]\n'
    )
    with pytest.raises(RefusedError, match="internal '@co.uk'"):
        routing(root)


def test_title_rules_from_knowledge_toml_route_any_case_and_width(tmp_path):
    rule = '[[transcripts.customers]]\nproject = "alpha"\ntitles = ["ＡＬＰＨＡ Weekly"]\n'
    rules = routing(knowledge_repo(tmp_path, rule))
    for title, expected in (("alpha  weekly: notes", "alpha"), ("Alphaweekly", None)):
        found = route({"title": title, "emails": ["ana@example.com"]}, rules["customers"], [])
        assert (found["project"] if isinstance(found, dict) else None) == expected, title


def test_a_customer_transcript_reaches_only_its_own_repository(tmp_path):
    beta_rule = '[[transcripts.customers]]\nproject = "beta"\nparticipants = ["@beta.example"]\n'
    root = knowledge_repo(tmp_path, ALPHA + beta_rule)
    alpha, environ = customer_env(tmp_path)
    beta = customer_repo_dir(tmp_path, project="beta")
    environ = {**environ, "KNOWLEDGE_REPO_BETA": str(beta)}
    reg = registry(FakeZoom(), FakeDrive())
    result = TranscriptPull(
        tmp_path, CONFIG, providers=["zoom"], into=root, registry=reg, environ=environ
    ).pull("2026-11-01")
    written = {entry["id"]: entry for entry in result["written"]}
    assert (alpha / written["Qx9YzZalpha=="]["record"]).is_file()
    assert result["warnings"] == []
    for repo in (root, beta):
        assert not any("Qx9YzZalpha" in p.read_text() for p in repo.rglob("*") if p.is_file())


@pytest.mark.parametrize("error", [TranscriptUnavailable, UncertainError])
def test_a_provider_message_about_a_customer_meeting_is_not_repeated(tmp_path, error):
    root = knowledge_repo(tmp_path, ALPHA)
    _alpha, environ = customer_env(tmp_path)
    reg = registry(FakeZoom(), FakeDrive())
    invoke = reg.invoke

    def failing(provider, operation, arguments):
        if operation == "fetch" and "alpha" in arguments["id"]:
            raise error("Alpha cutover sync: transcript gone")
        return invoke(provider, operation, arguments)

    reg.invoke = failing
    result = TranscriptPull(
        tmp_path, CONFIG, providers=["zoom"], into=root, registry=reg, environ=environ
    ).pull("2026-11-01")
    assert "cutover" not in json.dumps(result)
    assert any(e["id"] == "Qx9YzZalpha==" for e in result["skipped"] + result["errors"])


def test_unmapped_customer_meeting_goes_to_no_repository(tmp_path):
    routes = ALPHA.replace('"@alpha.example"', '"@nobody.example"')
    root = knowledge_repo(tmp_path, routes)
    alpha, environ = customer_env(tmp_path)
    reg = registry(FakeZoom(), FakeDrive())
    result = TranscriptPull(
        tmp_path, CONFIG, providers=["zoom"], into=root, registry=reg, environ=environ
    ).pull("2026-11-01")
    skipped = {entry["id"]: entry["reason"] for entry in result["skipped"]}
    assert "not every participant is internal" in skipped["Qx9YzZalpha=="]
    for repo in (root, alpha):
        assert not any("Qx9YzZalpha" in p.read_text() for p in repo.rglob("*") if p.is_file())


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
