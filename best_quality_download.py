"""
SaveTwitter ajaxSearch → 最高清媒体下载规则

解析入口（固定，无配置中心）:
  POST https://savetwitter.net/api/ajaxSearch
  form: q=<帖子链接>&lang=en&cftoken=

选质规则（写死）:
  图片:
    - 只保留 pbs.twimg.com/media/...
    - 丢掉 amplify_video_thumb（视频封面）
    - 下载 URL 统一加 ?name=orig（原图）
  视频:
    - 收集 video.twimg.com 下所有 mp4
    - 从路径 /WIDTHxHEIGHT/ 解析分辨率
    - 同一帖只保留像素面积最大的一档（如 1920x1080）
  下载:
    - 优先直连 twimg；失败再走 dl.snapcdn.app token 代理
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Any, Callable

API = "https://savetwitter.net/api/ajaxSearch"
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 "
    "Mobile/15E148 Safari/604.1"
)

RES_IN_PATH = re.compile(r"/(\d{2,4})x(\d{2,4})/")
TWIMG_MEDIA = re.compile(
    r"https://pbs\.twimg\.com/media/[A-Za-z0-9_\-]+(?:\.(?:jpg|jpeg|png|webp))?",
    re.I,
)
VIDEO_TWIMG = re.compile(r"https://video\.twimg\.com/[^\"'\s\\]+", re.I)
SNAPCDN = re.compile(r"https://dl\.snapcdn\.app/get\?token=[^\"'\s]+", re.I)
ANCHOR = re.compile(r'<a[^>]+href="(https://[^"]+)"[^>]*>(.*?)</a>', re.I | re.S)


@dataclass
class PhotoItem:
    media_id: str
    url: str  # always ?name=orig when possible
    proxy_url: str | None = None


@dataclass
class VideoItem:
    url: str
    width: int
    height: int
    pixels: int
    proxy_url: str | None = None
    label: str = ""


@dataclass
class ParseResult:
    post_url: str
    photos: list[PhotoItem]
    video: VideoItem | None  # 仅最高清一档；无视频则为 None
    skipped_thumbs: list[str]
    all_video_qualities: list[dict[str, Any]]  # 调试用：全部清晰度


def fetch(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 90,
) -> tuple[int | None, dict[str, str], bytes]:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()


def b64url_json(segment: str) -> dict[str, Any]:
    pad = "=" * (-len(segment) % 4)
    raw = base64.urlsafe_b64decode(segment + pad)
    return json.loads(raw.decode("utf-8"))


def decode_snapcdn(url: str) -> dict[str, Any] | None:
    try:
        token = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["token"][0]
        return b64url_json(token.split(".")[1])
    except Exception:
        return None


def media_id_from_url(url: str) -> str:
    m = re.search(r"/media/([A-Za-z0-9_\-]+)", url)
    return m.group(1) if m else url


def to_orig_photo_url(url: str) -> str:
    """最高清图片：Twitter media 原图参数 name=orig。"""
    if "pbs.twimg.com/media" not in url:
        return url
    base = url.split("?")[0]
    # 若无扩展名，补 .jpg（多数媒体如此；实际 ctype 以下载为准）
    if not re.search(r"\.(jpg|jpeg|png|webp)$", base, re.I):
        base = base + ".jpg"
    return base + "?name=orig"


def video_resolution(url: str) -> tuple[int, int, int]:
    m = RES_IN_PATH.search(url)
    if not m:
        return 0, 0, 0
    w, h = int(m.group(1)), int(m.group(2))
    return w, h, w * h


def is_video_thumb(url: str) -> bool:
    return "amplify_video_thumb" in url or "/ext_tw_video_thumb/" in url


def is_photo_url(url: str) -> bool:
    return "pbs.twimg.com/media" in url and not is_video_thumb(url)


def is_video_url(url: str) -> bool:
    return "video.twimg.com" in url and ".mp4" in url.split("?")[0].lower()


def ajax_search(post_url: str) -> str:
    form = urllib.parse.urlencode(
        {"q": post_url, "lang": "en", "cftoken": ""}
    ).encode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Origin": "https://savetwitter.net",
        "Referer": "https://savetwitter.net/en4",
        "X-Requested-With": "XMLHttpRequest",
    }
    status, _, body = fetch(API, method="POST", data=form, headers=headers)
    if status != 200:
        raise RuntimeError(f"ajaxSearch HTTP {status}: {body[:300]!r}")
    payload = json.loads(body.decode("utf-8", errors="replace"))
    if payload.get("status") != "ok":
        raise RuntimeError(f"ajaxSearch failed: {payload!r}")
    return unescape(payload.get("data") or "")


def parse_best_media(post_url: str, html: str | None = None) -> ParseResult:
    if html is None:
        html = ajax_search(post_url)

    # 1) 收集 snapcdn token → 真实 URL（主来源，带清晰度标签）
    snap_map: list[tuple[str, dict[str, Any], str]] = []
    # (proxy, meta, button_text)
    button_text_by_href: dict[str, str] = {}
    for m in ANCHOR.finditer(html):
        href = unescape(m.group(1))
        text = re.sub(r"<[^>]+>", " ", m.group(2))
        text = re.sub(r"\s+", " ", text).strip()
        button_text_by_href[href] = text

    for proxy in dict.fromkeys(SNAPCDN.findall(html)):
        meta = decode_snapcdn(proxy)
        if not meta or not meta.get("url"):
            continue
        label = button_text_by_href.get(proxy, "")
        snap_map.append((proxy, meta, label))

    # 2) 也扫 HTML 里的直链（兜底）
    direct_photos = TWIMG_MEDIA.findall(html)
    direct_videos = VIDEO_TWIMG.findall(html)

    photos: dict[str, PhotoItem] = {}
    skipped_thumbs: list[str] = []
    videos: list[VideoItem] = []

    def add_photo(url: str, proxy: str | None = None) -> None:
        url = unescape(url)
        if is_video_thumb(url):
            skipped_thumbs.append(url)
            return
        if not is_photo_url(url):
            return
        mid = media_id_from_url(url)
        item = PhotoItem(
            media_id=mid,
            url=to_orig_photo_url(url),
            proxy_url=proxy,
        )
        # 已有则保留已有（orig 相同）；若新的带 proxy 可补上
        if mid in photos:
            if proxy and not photos[mid].proxy_url:
                photos[mid].proxy_url = proxy
        else:
            photos[mid] = item

    def add_video(url: str, proxy: str | None = None, label: str = "") -> None:
        url = unescape(url).rstrip("\\")
        if not is_video_url(url):
            return
        w, h, px = video_resolution(url)
        # 从按钮文案补分辨率（极少路径无 /WxH/ 时）
        if px == 0 and label:
            m = re.search(r"(\d{3,4})p", label, re.I)
            if m:
                h = int(m.group(1))
                # 估算 16:9
                w = int(round(h * 16 / 9))
                px = w * h
        videos.append(
            VideoItem(
                url=url,
                width=w,
                height=h,
                pixels=px,
                proxy_url=proxy,
                label=label,
            )
        )

    for proxy, meta, label in snap_map:
        inner = meta["url"]
        if is_photo_url(inner) or is_video_thumb(inner):
            add_photo(inner, proxy=proxy)
        elif is_video_url(inner):
            add_video(inner, proxy=proxy, label=label)

    for u in direct_photos:
        add_photo(u)
    for u in direct_videos:
        add_video(u)

    # 3) 视频：只留像素面积最大的一档
    all_qualities = [
        {
            "url": v.url,
            "width": v.width,
            "height": v.height,
            "pixels": v.pixels,
            "label": v.label,
        }
        for v in videos
    ]
    # 去重同 URL
    uniq: dict[str, VideoItem] = {}
    for v in videos:
        prev = uniq.get(v.url)
        if not prev or (v.proxy_url and not prev.proxy_url):
            uniq[v.url] = v
    ranked = sorted(uniq.values(), key=lambda v: (v.pixels, v.width, v.height), reverse=True)
    best_video = ranked[0] if ranked else None

    return ParseResult(
        post_url=post_url,
        photos=list(photos.values()),
        video=best_video,
        skipped_thumbs=skipped_thumbs,
        all_video_qualities=sorted(
            all_qualities, key=lambda x: x["pixels"], reverse=True
        ),
    )


def guess_ext(url: str, ctype: str, default: str) -> str:
    ctype = (ctype or "").lower()
    path = urllib.parse.urlparse(url).path.lower()
    if "mp4" in ctype or path.endswith(".mp4"):
        return ".mp4"
    if "png" in ctype or path.endswith(".png"):
        return ".png"
    if "webp" in ctype or path.endswith(".webp"):
        return ".webp"
    if "jpeg" in ctype or "jpg" in ctype or path.endswith((".jpg", ".jpeg")):
        return ".jpg"
    return default


def _stream_download(
    url: str,
    dest: Path,
    progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    """Download directly to disk so desktop clients can report real progress."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            total_text = response.headers.get("Content-Length")
            total = int(total_text) if total_text and total_text.isdigit() else None
            ext = guess_ext(url, response.headers.get("Content-Type", ""), dest.suffix)
            path = dest.with_suffix(ext)
            temporary = path.with_suffix(path.suffix + ".part")
            downloaded = 0
            try:
                with temporary.open("wb") as file:
                    while chunk := response.read(1024 * 256):
                        file.write(chunk)
                        downloaded += len(chunk)
                        if progress:
                            progress(downloaded, total)
                if downloaded <= 1000:
                    raise RuntimeError("response was too small to be media")
                temporary.replace(path)
                return path
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"HTTP {error.code}") from error


def download_one(
    url: str,
    proxy: str | None,
    dest: Path,
    progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    try:
        return _stream_download(url, dest, progress)
    except Exception as direct_error:
        if proxy:
            try:
                return _stream_download(proxy, dest, progress)
            except Exception as proxy_error:
                raise RuntimeError(
                    f"download failed: {url} (proxy={proxy}); {direct_error}; {proxy_error}"
                ) from proxy_error
        raise RuntimeError(f"download failed: {url}; {direct_error}") from direct_error


def download_best(post_url: str, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = ajax_search(post_url)
    (out_dir / "ajaxSearch_data.html").write_text(html, encoding="utf-8")
    result = parse_best_media(post_url, html=html)

    saved: list[str] = []
    for p in result.photos:
        path = download_one(
            p.url, p.proxy_url, out_dir / f"photo_{p.media_id}.jpg"
        )
        saved.append(str(path))
        print(f"photo {p.media_id}: {path.name} ({path.stat().st_size:,} bytes)")

    if result.video:
        v = result.video
        tag = f"{v.width}x{v.height}" if v.pixels else "best"
        path = download_one(v.url, v.proxy_url, out_dir / f"video_{tag}.mp4")
        saved.append(str(path))
        print(
            f"video {tag}: {path.name} ({path.stat().st_size:,} bytes) "
            f"[picked max of {len(result.all_video_qualities)} qualities]"
        )
    else:
        print("video: (none)")

    if result.skipped_thumbs:
        print(f"skipped thumbs: {len(result.skipped_thumbs)}")

    summary = {
        "post_url": post_url,
        "rules": {
            "photos": "pbs.twimg.com/media only, ?name=orig, skip video thumbs",
            "videos": "single highest WxH by pixel area",
            "api": API,
        },
        "photos": [asdict(p) for p in result.photos],
        "video_selected": asdict(result.video) if result.video else None,
        "video_all_qualities": result.all_video_qualities,
        "skipped_thumbs": result.skipped_thumbs,
        "saved": saved,
    }
    (out_dir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Parse X post via ajaxSearch; keep best quality only")
    ap.add_argument("url", help="X/Twitter post URL")
    ap.add_argument(
        "-o",
        "--out",
        default=r"project\sim_download\best",
        help="output directory",
    )
    args = ap.parse_args()
    summary = download_best(args.url, Path(args.out))
    print("\n=== selected ===")
    print(f"photos: {len(summary['photos'])}")
    if summary["video_selected"]:
        v = summary["video_selected"]
        print(f"video: {v['width']}x{v['height']}  {v['url']}")
    else:
        print("video: none")
    print("saved:", *summary["saved"], sep="\n  ")


if __name__ == "__main__":
    main()
