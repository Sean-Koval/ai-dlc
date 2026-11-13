"""Shared parts of the ``transcripts`` role providers (``zoom`` and ``google-meet``).

Credentials follow the ``jira-cloud`` rules. Configuration names an environment
variable, never a value; the token is an externally managed OAuth bearer token, so
issuance and renewal stay in approved tooling (a keychain or a secrets manager that
fills the variable). Every error message is fixed, so no token or transport payload
leaks into output.

A transcript the token cannot read raises :class:`TranscriptUnavailable`. The pull
service skips it and logs its id; it is not an error.
"""

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

from ai_dlc.errors import RefusedError, UncertainError

MAX_REQUESTS = 500
MAX_BYTES = 16 * 1024 * 1024
MAX_REDIRECTS = 3
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CUE = re.compile(r"^(\d{1,3}):([0-5]\d):([0-5]\d)(?:[.,]\d+)?\s+-->")
_SPEAKER = re.compile(r"^([^:\n]{1,80}?):\s+(.+)$")


class TranscriptRefusal(RefusedError):
    """A fixed, sanitized refusal: configuration, credentials or scopes."""


class TranscriptUncertain(UncertainError):
    """A fixed, sanitized remote failure; rerun the pull."""


class TranscriptUnavailable(RefusedError):
    """This caller cannot read this one transcript; it is skipped, not an error."""


def bearer(config: Mapping[str, Any], environ: Mapping[str, str], label: str) -> str:
    """The ``Authorization`` header value, read from the named variable."""
    if config.get("auth_mode") != "oauth_bearer":
        raise TranscriptRefusal(
            f'Select {label} auth_mode = "oauth_bearer" explicitly; credentials are never guessed'
        )
    name = config.get("token_env")
    if not isinstance(name, str) or not _ENV_NAME.fullmatch(name):
        raise TranscriptRefusal(f"{label} requires a named token_env environment reference")
    token = environ.get(name, "").strip()
    if not token or any(c in token for c in "\r\n "):
        raise TranscriptRefusal(f"{label} credential environment reference is not populated")
    return "Bearer " + token


def host_allowed(url: str, hosts: tuple[str, ...]) -> bool:
    parts = urlsplit(url)
    host = parts.hostname or ""
    return (
        parts.scheme == "https"
        and parts.username is None
        and parts.password is None
        and any(host == allowed or host.endswith("." + allowed) for allowed in hosts)
    )


class Transport:
    """Bounded HTTPS requests to a fixed set of hosts, with fixed error messages."""

    def __init__(
        self,
        label: str,
        authorization: str,
        hosts: tuple[str, ...],
        client: httpx.Client | None = None,
    ):
        self.label = label
        self.authorization = authorization
        self.hosts = hosts
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.owned_client = client is None
        self.requests_used = 0

    def close(self) -> None:
        if self.owned_client:
            self.client.close()

    def get(self, url: str, *, params=None, item: bool = False) -> httpx.Response:
        """GET ``url``; follow redirects only to allowed hosts, without the token off-host.

        With ``item``, 401, 403 and 404 mean this one transcript is unavailable.
        """
        origin = urlsplit(url).hostname
        for _ in range(MAX_REDIRECTS + 1):
            if not host_allowed(url, self.hosts):
                raise TranscriptUncertain(f"{self.label} sent a link outside its service")
            self.requests_used += 1
            if self.requests_used > MAX_REQUESTS:
                raise TranscriptUncertain(f"{self.label} request budget exhausted")
            headers = {"Accept": "application/json, text/plain, text/vtt"}
            if urlsplit(url).hostname == origin:
                headers["Authorization"] = self.authorization
            try:
                response = self.client.get(
                    url, params=params, headers=headers, timeout=30, follow_redirects=False
                )
            except (httpx.HTTPError, ValueError, UnicodeError):
                raise TranscriptUncertain(
                    f"{self.label} request outcome is uncertain; rerun the pull"
                ) from None
            if response.is_redirect and response.headers.get("location"):
                url = urljoin(url, response.headers["location"])
                params = None
                continue
            if item and response.status_code in {401, 403, 404}:
                raise TranscriptUnavailable(
                    f"{self.label} transcript not readable (HTTP {response.status_code})"
                )
            if response.status_code in {401, 403}:
                raise TranscriptRefusal(
                    f"{self.label} request refused (HTTP {response.status_code}); "
                    "verify the token's OAuth scopes"
                )
            if not 200 <= response.status_code < 300:
                raise TranscriptUncertain(
                    f"{self.label} request failed (HTTP {response.status_code}); rerun the pull"
                )
            if len(response.content) > MAX_BYTES:
                raise TranscriptUncertain(f"{self.label} response exceeds the response budget")
            return response
        raise TranscriptUncertain(f"{self.label} redirect budget exhausted")

    def json(self, url: str, *, params=None, item: bool = False) -> dict:
        response = self.get(url, params=params, item=item)
        try:
            data = response.json()
        except ValueError:
            raise TranscriptUncertain(f"{self.label} response is not complete JSON") from None
        if not isinstance(data, dict):
            raise TranscriptUncertain(f"{self.label} response is not a JSON object")
        return data


def clock(hours: int | str, minutes: int | str, seconds: int | str) -> str:
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def speaker_line(line: str) -> tuple[str, str] | None:
    """``("Name", "text")`` for a ``Name: text`` line, else None."""
    found = _SPEAKER.match(line.strip())
    if not found or "://" in found.group(1):
        return None
    return found.group(1).strip(), found.group(2).strip()


def vtt_segments(text: str) -> list[dict]:
    """Segments of a WebVTT transcript; a cue without ``Name:`` has speaker ``Unknown``."""
    segments: list[dict] = []
    at: str | None = None  # the open cue's start; a blank line closes the cue
    started = False  # whether the open cue has produced a segment yet
    for raw in text.lstrip("﻿").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        cue = _CUE.match(line)
        if cue:
            at, started = clock(*cue.groups()), False
            continue
        if not line:
            at = None
            continue
        if at is None:  # header, cue number or NOTE block
            continue
        said = speaker_line(line)
        if said:
            segments.append({"speaker": said[0], "at": at, "text": said[1]})
        elif started:
            segments[-1]["text"] += " " + line
        else:
            segments.append({"speaker": "Unknown", "at": at, "text": line})
        started = True
    return segments


def unique(values: list[str]) -> list[str]:
    seen: dict[str, str] = {}
    for value in values:
        value = value.strip()
        if value and value.casefold() not in seen:
            seen[value.casefold()] = value
    return list(seen.values())
