"""The ``google-meet`` provider for the ``transcripts`` role: transcripts in Drive.

Meet saves a transcript as a Google Doc named ``<meeting> - Transcript`` in the
organiser's Drive. The provider finds those Docs with the Drive API, exports each
as plain text and parses the ``Attendees`` line, ``HH:MM:SS`` marks and
``Name: text`` lines. The transcript id is the Drive file id. A Doc shared with the
caller is found too; one the caller cannot export is skipped::

    [providers.meet]
    kind = "google-meet"
    auth_mode = "oauth_bearer"
    token_env = "GOOGLE_MEET_TOKEN"  # a variable name, never a value
    folder_id = "<Drive folder id>"  # optional: only this folder (Meet Recordings)

Scope: ``https://www.googleapis.com/auth/drive.meet.readonly`` (files Meet created),
or ``drive.readonly`` to read Docs other organisers shared. The token is issued and
renewed outside ai-dlc. Live qualification is still pending (KAN-450).
"""

import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from ai_dlc.providers.transcripts_common import (
    TranscriptRefusal,
    TranscriptUnavailable,
    TranscriptUncertain,
    Transport,
    bearer,
    speaker_line,
    unique,
)

API = "https://www.googleapis.com/drive/v3/"
HOSTS = ("www.googleapis.com",)
DOC = "application/vnd.google-apps.document"
FIELDS = "id,name,createdTime,webViewLink,mimeType"
MAX_PAGES = 50
_FOLDER = re.compile(r"^[A-Za-z0-9_-]{10,128}$")
_MARK = re.compile(r"^(\d{1,3}):([0-5]\d):([0-5]\d)$")
_SUFFIX = re.compile(r"\s+-\s+Transcript\s*$", re.IGNORECASE)
_FOOTERS = ("meeting ended after", "this editable transcript was computer generated")


def parse(text: str) -> tuple[list[str], list[dict]]:
    """``(attendees, segments)`` of an exported Meet transcript."""
    lines = [line.strip() for line in text.lstrip("﻿").replace("\r\n", "\n").split("\n")]
    attendees: list[str] = []
    segments: list[dict] = []
    at: str | None = None
    section = None
    for line in lines:
        lowered = line.casefold()
        if lowered in {"attendees", "transcript"} and at is None:
            section = lowered
            continue
        if section == "attendees" and line:
            attendees.extend(name for name in line.split(","))
            section = None
            continue
        mark = _MARK.match(line)
        if mark:
            at = ":".join(f"{int(part):02d}" for part in mark.groups())
            continue
        if not line or at is None or lowered.startswith(_FOOTERS):
            continue
        said = speaker_line(line)
        if said:
            segments.append({"speaker": said[0], "at": at, "text": said[1]})
        elif segments:
            segments[-1]["text"] += " " + line
    return unique(attendees), segments


def _created(value: object) -> datetime:
    try:
        created = datetime.fromisoformat(str(value))
    except ValueError:
        raise TranscriptUncertain("Drive file creation time is incomplete") from None
    return created if created.tzinfo else created.replace(tzinfo=UTC)


class GoogleMeet:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        self.config = dict(config)
        folder = self.config.get("folder_id")
        if folder is not None and (not isinstance(folder, str) or not _FOLDER.fullmatch(folder)):
            raise TranscriptRefusal("Google Meet folder_id must be a Drive folder id")
        self.folder = folder
        env = os.environ if environ is None else environ
        self.http = Transport("Google Meet", bearer(self.config, env, "Google Meet"), HOSTS, client)
        self._text: dict[str, str] = {}

    def close(self) -> None:
        self.http.close()

    def _export(self, file_id: str) -> str:
        if file_id not in self._text:
            response = self.http.get(
                API + f"files/{quote(file_id, safe='')}/export",
                params={"mimeType": "text/plain"},
                item=True,
            )
            self._text[file_id] = response.text
        return self._text[file_id]

    def _summary(self, row: Mapping[str, Any], attendees: list[str]) -> dict:
        title = _SUFFIX.sub("", str(row.get("name") or "")).strip() or "Google Meet meeting"
        link = row.get("webViewLink")
        return {
            "id": str(row["id"]),
            "title": title,
            "start": _created(row.get("createdTime")),
            "participants": attendees,
            "url": link if isinstance(link, str) else None,
        }

    def list_since(self, since: datetime) -> dict:
        stamp = since.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")
        query = (
            f"mimeType = '{DOC}' and name contains 'Transcript' and trashed = false "
            f"and createdTime >= '{stamp}'"
        )
        if self.folder:
            query += f" and '{self.folder}' in parents"
        params: dict[str, Any] = {
            "q": query,
            "fields": f"nextPageToken,files({FIELDS})",
            "pageSize": 100,
            "orderBy": "createdTime",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        items = []
        for _ in range(MAX_PAGES):
            data = self.http.json(API + "files", params=params)
            for row in data.get("files") or []:
                if not isinstance(row, dict) or not row.get("id") or row.get("mimeType") != DOC:
                    continue
                if not _SUFFIX.search(str(row.get("name") or "")):
                    continue
                try:
                    attendees, _segments = parse(self._export(str(row["id"])))
                except TranscriptUnavailable:
                    attendees = []  # listed but not exportable; fetch skips it
                items.append(self._summary(row, attendees))
            token = data.get("nextPageToken")
            if not token:
                return {"items": items}
            params = {**params, "pageToken": token}
        raise TranscriptUncertain("Drive pagination budget exhausted")

    def fetch(self, id: str) -> dict:
        row = self.http.json(
            API + f"files/{quote(id, safe='')}",
            params={"fields": FIELDS, "supportsAllDrives": "true"},
            item=True,
        )
        if row.get("mimeType") != DOC:
            raise TranscriptUnavailable("Drive file is not a Meet transcript Doc")
        attendees, segments = parse(self._export(id))
        if not segments:
            raise TranscriptUnavailable("Meet transcript is empty")
        speakers = [segment["speaker"] for segment in segments]
        summary = self._summary({**row, "id": id}, unique([*attendees, *speakers]))
        return {**summary, "segments": segments}
