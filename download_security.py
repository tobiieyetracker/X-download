"""Shared network and download-safety helpers."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
import re
from typing import Iterable


MEDIA_HOSTS = frozenset({"pbs.twimg.com", "video.twimg.com"})
PROXY_HOSTS = frozenset({"dl.snapcdn.app"})
PARSER_HOSTS = frozenset({"dwnld.nichind.dev", "savetwitter.net"})
DOWNLOAD_HOSTS = MEDIA_HOSTS | PROXY_HOSTS

DEFAULT_MAX_FILE_MB = 1024
DEFAULT_MAX_TOTAL_MB = 4096
DEFAULT_MAX_FILES = 50
MAX_API_RESPONSE_BYTES = 16 * 1024 * 1024


def _hostname(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    return parsed.hostname.lower().rstrip(".")


def is_https_host(url: str, allowed_hosts: Iterable[str]) -> bool:
    host = _hostname(url)
    return host is not None and host in set(allowed_hosts)


def is_x_post_url(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value.strip())
    except ValueError:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme.lower() == "https"
        and host in {"x.com", "twitter.com", "www.x.com", "www.twitter.com"}
        and re.search(r"/status/\d+(?:/|$)", parsed.path)
        is not None
    )


def is_allowed_photo_url(url: str) -> bool:
    if not is_https_host(url, {"pbs.twimg.com"}):
        return False
    path = urllib.parse.urlsplit(url).path.lower()
    return path.startswith("/media/") and len(path) > len("/media/")


def is_allowed_video_url(url: str) -> bool:
    if not is_https_host(url, {"video.twimg.com"}):
        return False
    return urllib.parse.urlsplit(url).path.lower().endswith(".mp4")


def is_allowed_proxy_url(url: str) -> bool:
    if not is_https_host(url, PROXY_HOSTS):
        return False
    parsed = urllib.parse.urlsplit(url)
    if parsed.path.rstrip("/") != "/get":
        return False
    return bool(urllib.parse.parse_qs(parsed.query).get("token"))


def is_allowed_media_url(url: str) -> bool:
    return is_allowed_photo_url(url) or is_allowed_video_url(url)


def is_allowed_download_url(url: str) -> bool:
    return is_allowed_media_url(url) or is_allowed_proxy_url(url)


def redact_url(value: object) -> str:
    """Remove signed URL tokens before putting a URL in logs or JSON."""
    text = str(value)
    try:
        parsed = urllib.parse.urlsplit(text)
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        redacted = []
        for key, item in pairs:
            if key.lower() in {"token", "signature", "sig", "cftoken"}:
                item = "[redacted]"
            redacted.append((key, item))
        return urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(redacted), parsed.fragment)
        )
    except ValueError:
        return text


class AllowlistRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Reject redirects to hosts outside the request's explicit allowlist."""

    def __init__(self, allowed_hosts: Iterable[str]):
        super().__init__()
        self.allowed_hosts = frozenset(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urljoin(req.full_url, newurl)
        if not is_https_host(target, self.allowed_hosts):
            raise urllib.error.URLError(
                f"redirect target is outside the allowlist: {redact_url(target)}"
            )
        return super().redirect_request(req, fp, code, msg, headers, target)


def safe_urlopen(request: urllib.request.Request, allowed_hosts: Iterable[str], timeout: int):
    allowed = frozenset(allowed_hosts)
    if not is_https_host(request.full_url, allowed):
        raise urllib.error.URLError(
            f"request target is outside the allowlist: {redact_url(request.full_url)}"
        )
    opener = urllib.request.build_opener(AllowlistRedirectHandler(allowed))
    return opener.open(request, timeout=timeout)


def read_limited(response, limit: int = MAX_API_RESPONSE_BYTES) -> bytes:
    body = response.read(limit + 1)
    if len(body) > limit:
        raise RuntimeError(f"解析服务响应超过 {limit // (1024 * 1024)} MiB 限制")
    return body


def mb_to_bytes(value: int, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} 必须是正整数 MiB。")
    return value * 1024 * 1024
