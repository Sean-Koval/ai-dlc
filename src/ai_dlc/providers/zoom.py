"""The ``zoom`` provider for the ``transcripts`` role: cloud recording transcripts.

It lists the user's cloud recordings, keeps meetings with a completed ``TRANSCRIPT``
file, and downloads that WebVTT file. The transcript id is the meeting UUID.
Configuration names a variable; the token is a user-level OAuth access token from a
scoped Zoom OAuth app, issued and renewed outside ai-dlc::

    [providers.zoom]
    kind = "zoom"
    auth_mode = "oauth_bearer"
    token_env = "ZOOM_TOKEN"   # a variable name, never a value
    user = "me"                # default

Scopes, granular names: ``cloud_recording:read:list_user_recordings``,
``cloud_recording:read:list_recording_files`` and, for participant names,
``meeting:read:list_past_participants``. Without the last one, participants are the
transcript's speakers. Live qualification is still pending (KAN-450).
"""

import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from ai_dlc.providers.transcripts_common import (
    TranscriptRefusal,
    TranscriptUnavailable,
    TranscriptUncertain,
    Transport,
    bearer,
    unique,
    vtt_segments,
)

API = "https://api.zoom.us/v2/"
HOSTS = ("zoom.us",)
WINDOW_DAYS = 30  # Zoom lists at most one month of recordings per request
MAX_WINDOWS = 25
MAX_PAGES = 50
_USER = re.compile(r"^(?:me|[A-Za-z0-9_.@+-]{1,128})$")


def meeting_path(uuid: str) -> str:
    """A meeting UUID as a path segment; Zoom wants one starting with / or holding // twice encoded."""
    once = quote(uuid, safe="")
    return quote(once, safe="") if uuid.startswith("/") or "//" in uuid else once


def _start(value: object) -> datetime:
    try:
        start = datetime.fromisoformat(str(value))
    except ValueError:
        raise TranscriptUncertain("Zoom recording start time is incomplete") from None
    if start.tzinfo is None:
        raise TranscriptUncertain("Zoom recording start time has no offset")
    return start


def _transcript_file(meeting: Mapping[str, Any]) -> dict | None:
    for item in meeting.get("recording_files") or []:
        if (
            isinstance(item, dict)
            and str(item.get("file_type", "")).upper() == "TRANSCRIPT"
            and str(item.get("status", "completed")).lower() == "completed"
            and isinstance(item.get("download_url"), str)
        ):
            return item
    return None


class Zoom:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
        now: datetime | None = None,
    ):
        self.config = dict(config)
        user = str(self.config.get("user") or "me")
        if not _USER.fullmatch(user):
            raise TranscriptRefusal("Zoom user must be me or a Zoom user id or email")
        self.user = user
        env = os.environ if environ is None else environ
        self.http = Transport("Zoom", bearer(self.config, env, "Zoom"), HOSTS, client)
        self.now = now

    def close(self) -> None:
        self.http.close()

    def _participants(self, uuid: str) -> tuple[list[str], list[str]]:
        """Display names and emails; empty when the scope is missing (speakers fill in)."""
        names: list[str] = []
        emails: list[str] = []
        params: dict[str, Any] = {"page_size": 300}
        for _ in range(MAX_PAGES):
            try:
                data = self.http.json(
                    API + f"past_meetings/{meeting_path(uuid)}/participants",
                    params=params,
                    item=True,
                )
            except (TranscriptUnavailable, TranscriptRefusal):
                return [], []
            for row in data.get("participants") or []:
                if isinstance(row, dict):
                    names.append(str(row.get("name") or ""))
                    emails.append(str(row.get("user_email") or ""))
            token = data.get("next_page_token")
            if not token:
                return unique(names), unique(emails)
            params = {"page_size": 300, "next_page_token": token}
        raise TranscriptUncertain("Zoom participant pagination budget exhausted")

    def _summary(self, meeting: Mapping[str, Any]) -> dict:
        uuid = str(meeting.get("uuid") or "")
        if not uuid:
            raise TranscriptUncertain("Zoom recording has no meeting UUID")
        names, emails = self._participants(uuid)
        return {
            "id": uuid,
            "title": str(meeting.get("topic") or "Zoom meeting").strip() or "Zoom meeting",
            "start": _start(meeting.get("start_time")),
            "participants": names,
            "emails": emails,
            "url": meeting.get("share_url") if isinstance(meeting.get("share_url"), str) else None,
        }

    def list_since(self, since: datetime) -> dict:
        now = self.now or datetime.now(UTC)
        first = (since - timedelta(days=1)).date()
        last = (now + timedelta(days=1)).date()
        windows = []
        while first <= last:
            end = min(first + timedelta(days=WINDOW_DAYS - 1), last)
            windows.append((first, end))
            first = end + timedelta(days=1)
        if len(windows) > MAX_WINDOWS:
            raise TranscriptRefusal("Zoom since is too far back; pull at most two years at once")
        items: dict[str, dict] = {}
        for start, end in windows:
            params: dict[str, Any] = {"from": start.isoformat(), "to": end.isoformat()}
            for _ in range(MAX_PAGES):
                data = self.http.json(
                    API + f"users/{quote(self.user, safe='@')}/recordings",
                    params={**params, "page_size": 300},
                )
                for meeting in data.get("meetings") or []:
                    if not isinstance(meeting, dict) or not _transcript_file(meeting):
                        continue
                    uuid = str(meeting.get("uuid") or "")
                    if uuid in items or _start(meeting.get("start_time")) < since:
                        continue
                    items[uuid] = self._summary(meeting)
                token = data.get("next_page_token")
                if not token:
                    break
                params = {**params, "next_page_token": token}
            else:
                raise TranscriptUncertain("Zoom recording pagination budget exhausted")
        return {"items": sorted(items.values(), key=lambda item: item["start"])}

    def fetch(self, id: str) -> dict:
        meeting = self.http.json(API + f"meetings/{meeting_path(id)}/recordings", item=True)
        found = _transcript_file(meeting)
        if found is None:
            raise TranscriptUnavailable("Zoom meeting has no completed transcript")
        text = self.http.get(found["download_url"], item=True).text
        segments = vtt_segments(text)
        if not segments:
            raise TranscriptUnavailable("Zoom transcript is empty")
        summary = self._summary({**meeting, "uuid": meeting.get("uuid") or id})
        speakers = [segment["speaker"] for segment in segments if segment["speaker"] != "Unknown"]
        summary["participants"] = unique([*summary["participants"], *speakers])
        return {**summary, "segments": segments}
