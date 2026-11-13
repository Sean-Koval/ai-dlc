"""The ``confluence-cloud`` provider for the ``wiki`` role (KAN-430, ADR 0004).

The wiki is a rendered view of the knowledge repository; ``knowledge render`` is its
only writer. The provider never reads a page body. It finds a page by a key label,
keeps the page's key, properties and the version it last wrote in one ``ai-dlc``
content property, and refuses an upsert whose ``expected_version`` is stale.

Credentials follow the ``jira-cloud`` adapter's rules: configuration names environment
variables, never values; requests go through the ``api.atlassian.com`` gateway with a
scoped token; and every error message is fixed, so no transport payload leaks::

    [providers.team-wiki]
    kind = "confluence-cloud"
    site_url = "https://example.atlassian.net"  # the only site this provider writes
    cloud_id = "<cloud UUID>"
    space = "ENG"                    # space key
    parent_id = "123456"             # page id under which rendered pages live
    auth_mode = "oauth_bearer"       # or personal_scoped_token_basic
    token_env = "CONFLUENCE_TOKEN"
    email_env = "ATLASSIAN_EMAIL"    # personal_scoped_token_basic only
"""

import base64
import html
import os
import re
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from ai_dlc.errors import RefusedError, UncertainError

GATEWAY = "https://api.atlassian.com/ex/confluence/"
PROPERTY = "ai-dlc"
KEY_LABEL = "ai-dlc-key-"
MAX_REQUESTS = 300
MAX_PAGES = 50
MAX_BYTES = 8 * 1024 * 1024
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LABEL = re.compile(r"[^a-z0-9._-]+")


class ConfluenceRefusal(RefusedError):
    """A fixed, sanitized refusal."""


class ConfluenceUncertain(UncertainError):
    """A fixed, sanitized remote failure; no transport payload is kept."""


def settings(config: Mapping[str, Any]) -> dict:
    """The validated provider configuration; raises a fixed refusal on any problem."""
    config = dict(config)
    site = urlsplit(str(config.get("site_url") or ""))
    if (
        site.scheme != "https"
        or not site.hostname
        or not re.fullmatch(r"[a-z0-9-]+\.atlassian\.net", site.hostname)
        or site.netloc != site.hostname
        or site.path not in {"", "/"}
        or site.query
        or site.fragment
    ):
        raise ConfluenceRefusal("Confluence site must be a bare HTTPS atlassian.net Cloud site")
    config["site_url"] = f"https://{site.hostname}"
    config["site"] = site.hostname
    try:
        if str(uuid.UUID(str(config.get("cloud_id")))) != config.get("cloud_id"):
            raise ValueError
    except ValueError:
        raise ConfluenceRefusal("Confluence requires an explicit canonical Cloud UUID") from None
    if not isinstance(config.get("space"), str) or not re.fullmatch(
        r"[A-Za-z0-9~][A-Za-z0-9_~]*", config["space"]
    ):
        raise ConfluenceRefusal("Confluence requires the reviewed space key")
    if not isinstance(config.get("parent_id"), str) or not config["parent_id"].isdigit():
        raise ConfluenceRefusal("Confluence requires the numeric parent page ID")
    if config.get("auth_mode") not in {"oauth_bearer", "personal_scoped_token_basic"}:
        raise ConfluenceRefusal(
            "Select supported Confluence auth_mode explicitly; credentials are never guessed"
        )
    names = ["token_env"]
    if config["auth_mode"] == "personal_scoped_token_basic":
        names.append("email_env")
    for name in names:
        if not isinstance(config.get(name), str) or not _ENV_NAME.fullmatch(config[name]):
            raise ConfluenceRefusal(f"Confluence requires a named {name} environment reference")
    return config


def key_label(key: str) -> str:
    return KEY_LABEL + _LABEL.sub("-", key.lower())


def _label(value: str) -> str:
    return _LABEL.sub("-", value.lower()).strip("-")


def _inline(text: str) -> str:
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", out)
    return re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(html.unescape(m.group(2)))}">{m.group(1)}</a>',
        out,
    )


def storage(markdown: str) -> str:
    """Confluence storage format for the markdown ``knowledge render`` writes.

    Covers headings, paragraphs, block quotes, bullet and numbered lists, pipe tables,
    fenced code, inline code, emphasis and links. Anything else is kept as escaped text.
    """
    lines = markdown.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    index = 0

    def flush() -> None:
        if paragraph:
            out.append("<p>" + _inline(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            language = stripped[3:].strip()
            code: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            parameter = (
                f'<ac:parameter ac:name="language">{html.escape(language)}</ac:parameter>'
                if language
                else ""
            )
            body = "\n".join(code).replace("]]>", "]]]]><![CDATA[>")
            out.append(
                f'<ac:structured-macro ac:name="code">{parameter}'
                f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>"
                "</ac:structured-macro>"
            )
            index += 1
            continue
        heading = re.match(r"(#{1,6})\s+(.*)", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
        elif stripped.startswith(">"):
            flush()
            quoted = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quoted.append(lines[index].strip()[1:].strip())
                index += 1
            out.append("<blockquote><p>" + _inline(" ".join(quoted)) + "</p></blockquote>")
            continue
        elif stripped.startswith("|"):
            flush()
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    tag = "th" if not rows else "td"
                    rows.append(
                        "<tr>" + "".join(f"<{tag}>{_inline(c)}</{tag}>" for c in cells) + "</tr>"
                    )
                index += 1
            out.append("<table><tbody>" + "".join(rows) + "</tbody></table>")
            continue
        elif re.match(r"([-*+]|\d+[.)])\s+", stripped):
            flush()
            ordered = bool(re.match(r"\d", stripped))
            items = []
            while index < len(lines) and re.match(r"([-*+]|\d+[.)])\s+", lines[index].strip()):
                item = re.sub(r"^([-*+]|\d+[.)])\s+", "", lines[index].strip())
                items.append(f"<li>{_inline(item)}</li>")
                index += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        elif not stripped:
            flush()
        else:
            paragraph.append(stripped)
        index += 1
    flush()
    return "".join(out)


class ConfluenceCloud:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        client: httpx.Client | None = None,
        environ: Mapping[str, str] | None = None,
    ):
        self.config = settings(config)
        env = os.environ if environ is None else environ
        token = env.get(self.config["token_env"])
        if not token:
            raise ConfluenceRefusal("Confluence credential environment reference is not populated")
        if self.config["auth_mode"] == "oauth_bearer":
            self.authorization = "Bearer " + token
        else:
            email = env.get(self.config["email_env"])
            if not email or any(c in email for c in ":\r\n"):
                raise ConfluenceRefusal(
                    "Confluence email environment reference is not populated or invalid"
                )
            self.authorization = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.client = client or httpx.Client(timeout=30, follow_redirects=False)
        self.owned_client = client is None
        self.root = GATEWAY + self.config["cloud_id"] + "/wiki/"
        self.requests_used = 0
        self._space_id: str | None = None

    @property
    def site(self) -> str:
        return self.config["site"]

    def close(self) -> None:
        if self.owned_client:
            self.client.close()

    # Transport

    def _request(self, method: str, path: str, *, params=None, body=None, missing=False):
        self.requests_used += 1
        if self.requests_used > MAX_REQUESTS:
            raise ConfluenceUncertain("Confluence request budget exhausted")
        try:
            response = self.client.request(
                method,
                self.root + path,
                params=params,
                json=body,
                headers={"Authorization": self.authorization, "Accept": "application/json"},
                timeout=30,
                follow_redirects=False,
            )
        except (httpx.HTTPError, ValueError, UnicodeError):
            raise ConfluenceUncertain(
                "Confluence request outcome is uncertain; rerun the render"
            ) from None
        if response.status_code == 404 and missing:
            return None
        if response.status_code == 409:
            raise ConfluenceRefusal("version conflict: the page changed during the render")
        if not 200 <= response.status_code < 300:
            raise ConfluenceUncertain(
                f"Confluence request refused (HTTP {response.status_code}); "
                "verify the token's scopes and the space permissions"
            )
        if response.status_code == 204:
            return None
        if len(response.content) > MAX_BYTES:
            raise ConfluenceUncertain("Confluence response exceeds the response budget")
        try:
            return response.json()
        except ValueError:
            raise ConfluenceUncertain("Confluence response is not complete JSON") from None

    def _pages(self, path: str, params: dict) -> list[dict]:
        rows: list[dict] = []
        params = dict(params)
        for _ in range(MAX_PAGES):
            data = self._request("GET", path, params=params) or {}
            rows.extend(data.get("results") or [])
            following = (data.get("_links") or {}).get("next")
            if not following:
                return rows
            cursor = parse_qs(urlsplit(following).query).get("cursor")
            if not cursor:
                raise ConfluenceUncertain("Confluence pagination is incomplete")
            params["cursor"] = cursor[0]
        raise ConfluenceUncertain("Confluence pagination budget exhausted")

    # Lookups

    def space_id(self) -> str:
        if self._space_id is None:
            rows = self._pages("api/v2/spaces", {"keys": self.config["space"]})
            if len(rows) != 1 or not str(rows[0].get("id", "")).isdigit():
                raise ConfluenceRefusal("Confluence space is not visible to this token")
            self._space_id = str(rows[0]["id"])
        return self._space_id

    def _property(self, page_id: str) -> dict | None:
        rows = self._pages(f"api/v2/pages/{page_id}/properties", {"key": PROPERTY})
        return rows[0] if rows else None

    def _labels(self, page_id: str) -> list[str]:
        rows = self._pages(f"api/v2/pages/{page_id}/labels", {"limit": 250})
        return sorted(str(row["name"]) for row in rows if row.get("name"))

    def _page(self, page_id: str, prop: dict | None = None) -> dict | None:
        """The page's metadata (never its body), or None when it is not an ai-dlc page."""
        prop = prop if prop is not None else self._property(page_id)
        value = (prop or {}).get("value")
        if not isinstance(value, dict) or not isinstance(value.get("key"), str):
            return None
        page = self._request("GET", f"api/v2/pages/{page_id}", missing=True)
        if not page:
            return None
        version = (page.get("version") or {}).get("number")
        if type(version) is not int:
            raise ConfluenceUncertain("Confluence page version is incomplete")
        webui = (page.get("_links") or {}).get("webui") or f"/pages/{page_id}"
        rendered = value.get("rendered_version")
        return {
            "key": value["key"],
            "page_id": str(page_id),
            "title": page.get("title") or value["key"],
            "version": version,
            "rendered_version": rendered if type(rendered) is int else None,
            "properties": {str(k): str(v) for k, v in (value.get("properties") or {}).items()},
            "labels": [
                label for label in self._labels(str(page_id)) if label != key_label(value["key"])
            ],
            "url": self.config["site_url"] + "/wiki" + webui,
        }

    def _find(self, key: str) -> dict | None:
        cql = f'type=page and space="{self.config["space"]}" and label="{key_label(key)}"'
        data = self._request("GET", "rest/api/content/search", params={"cql": cql, "limit": 5})
        ids = [str(row["id"]) for row in (data or {}).get("results") or [] if row.get("id")]
        pages = [page for page in (self._page(i) for i in ids) if page and page["key"] == key]
        if len(pages) > 1:
            raise ConfluenceRefusal("several Confluence pages carry one render key")
        return pages[0] if pages else None

    # Role operations

    def get_page_by_key(self, key: str) -> dict:
        return {"page": self._find(key)}

    def list_children(self, parent: str | None = None) -> dict:
        parent_id = self._parent_id(parent)
        rows = self._pages(f"api/v2/pages/{parent_id}/children", {"limit": 250})
        pages = [self._page(str(row["id"])) for row in rows if row.get("id")]
        return {"pages": [page for page in pages if page]}

    def _parent_id(self, parent: str | None) -> str:
        if parent is None:
            return self.config["parent_id"]
        found = self._find(parent)
        if not found:
            raise ConfluenceRefusal("parent page is not rendered yet")
        return found["page_id"]

    def upsert_page(
        self,
        key: str,
        title: str,
        body: str,
        properties: dict[str, str] | None = None,
        labels: list[str] | None = None,
        parent: str | None = None,
        expected_version: int | None = None,
        operation_id: str = "",
    ) -> dict:
        current = self._find(key)
        if current is None and expected_version is not None:
            raise ConfluenceRefusal("version conflict: the page no longer exists")
        if current is not None and current["version"] != expected_version:
            raise ConfluenceRefusal("version conflict: the page changed since it was read")
        parent_id = self._parent_id(parent)
        content = {"representation": "storage", "value": storage(body)}
        if current is None:
            created = self._request(
                "POST",
                "api/v2/pages",
                body={
                    "spaceId": self.space_id(),
                    "status": "current",
                    "title": title,
                    "parentId": parent_id,
                    "body": content,
                },
            )
            page_id = str((created or {}).get("id") or "")
            version = ((created or {}).get("version") or {}).get("number")
        else:
            page_id = current["page_id"]
            updated = self._request(
                "PUT",
                f"api/v2/pages/{page_id}",
                body={
                    "id": page_id,
                    "status": "current",
                    "title": title,
                    "parentId": parent_id,
                    "body": content,
                    "version": {
                        "number": current["version"] + 1,
                        "message": f"ai-dlc knowledge render {operation_id}".strip(),
                    },
                },
            )
            version = ((updated or {}).get("version") or {}).get("number")
        if not page_id.isdigit() or type(version) is not int:
            raise ConfluenceUncertain("Confluence write read-back is incomplete; rerun the render")
        wanted = sorted({key_label(key), *(_label(label) for label in labels or [] if label)})
        have = set(self._labels(page_id))
        missing = [{"prefix": "global", "name": name} for name in wanted if name not in have]
        if missing:
            self._request("POST", f"rest/api/content/{page_id}/label", body=missing)
        value = {"key": key, "rendered_version": version, "properties": dict(properties or {})}
        prop = self._property(page_id)
        if prop is None:
            self._request(
                "POST", f"api/v2/pages/{page_id}/properties", body={"key": PROPERTY, "value": value}
            )
        else:
            number = (prop.get("version") or {}).get("number")
            if type(number) is not int:
                raise ConfluenceUncertain("Confluence property version is incomplete")
            self._request(
                "PUT",
                f"api/v2/pages/{page_id}/properties/{prop['id']}",
                body={"key": PROPERTY, "value": value, "version": {"number": number + 1}},
            )
        page = self._page(page_id)
        if page is None:
            raise ConfluenceUncertain("Confluence write read-back is incomplete; rerun the render")
        return page
