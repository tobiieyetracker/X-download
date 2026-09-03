"""
菜单模式下载（对齐原版分流思路，接口写死为公开地址）

模式:
  photo        图片
  gif          GIF
  single_video 单视频
  multi_video  多视频
  auto         默认：自动识别并下载对应最高清

公开接口（不经过疯果配置中心 / 私人域名）:
  ajaxSearch  https://savetwitter.net/api/ajaxSearch
  nichind     https://dwnld.nichind.dev/
              （download.nichind.dev 的公开 API）

已排除:
  fenguox.fenguo.icu  — 疯果私人地址，不用
  duox / duo2x        — 需作者快捷指令鉴权
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from download_security import (
    DEFAULT_MAX_FILE_MB,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_TOTAL_MB,
    PARSER_HOSTS,
    is_allowed_photo_url,
    is_x_post_url,
    mb_to_bytes,
    read_limited,
    safe_urlopen,
)

# Reuse quality helpers
from best_quality_download import (  # type: ignore
    API as AJAX_API,
    ParseResult,
    PhotoItem,
    VideoItem,
    ajax_search,
    SNAPCDN,
    decode_snapcdn,
    download_one,
    is_video_url,
    is_video_thumb,
    media_id_from_url,
    parse_best_media,
    to_orig_photo_url,
    video_resolution,
)

Mode = Literal["photo", "gif", "single_video", "multi_video", "auto"]

# Public API for https://download.nichind.dev/
NICHIND = "https://dwnld.nichind.dev/"
DEFAULT_OUT = Path(__file__).resolve().parent / "downloads" / "modes"
UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 "
    "Mobile/15E148 Safari/604.1"
)


@dataclass
class Plan:
    mode: Mode
    post_url: str
    photos: list[PhotoItem]
    videos: list[VideoItem]  # multi 可多个；single/auto 视频已是最高清
    note: str
    sources: list[str]


def fetch(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 90,
) -> tuple[int | None, bytes]:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with safe_urlopen(req, PARSER_HOSTS, timeout=timeout) as resp:
            return resp.status, read_limited(resp)
    except urllib.error.HTTPError as e:
        return e.code, read_limited(e)
    except Exception as e:
        return None, repr(e).encode()


def prefer_photo_url(url: str) -> str:
    """最高清图：优先 name=4096x4096（nichind），否则 name=orig。"""
    if "pbs.twimg.com/media" not in url:
        return url
    base = url.split("?")[0]
    if not re.search(r"\.(jpg|jpeg|png|webp)$", base, re.I):
        base += ".jpg"
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    name = (q.get("name") or [""])[0]
    if name == "4096x4096":
        return base + "?name=4096x4096"
    return base + "?name=orig"


def parse_nichind(post_url: str) -> tuple[list[PhotoItem], list[VideoItem]]:
    payload = json.dumps({"url": post_url}).encode()
    status, body = fetch(
        NICHIND,
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    if status != 200:
        return [], []
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except Exception:
        return [], []

    photos: list[PhotoItem] = []
    videos: list[VideoItem] = []
    seen_photo: set[str] = set()
    seen_video: set[str] = set()

    def consume(item: dict[str, Any]) -> None:
        typ = (item.get("type") or "").lower()
        u = item.get("url") or item.get("videoURL") or ""
        if not u:
            return
        if is_allowed_photo_url(u) and not is_video_thumb(u):
            if is_video_thumb(u):
                return
            mid = media_id_from_url(u)
            if mid in seen_photo:
                return
            seen_photo.add(mid)
            photos.append(
                PhotoItem(media_id=mid, url=prefer_photo_url(u), proxy_url=None)
            )
        elif (typ in {"video", "gif"} or is_video_url(u)) and is_video_url(u):
            if u in seen_video:
                return
            seen_video.add(u)
            w, h, px = video_resolution(u)
            videos.append(
                VideoItem(url=u, width=w, height=h, pixels=px, label=typ or "video")
            )

    if data.get("status") == "picker":
        for it in data.get("picker") or []:
            consume(it)
    elif data.get("status") == "redirect" and data.get("url"):
        consume({"type": "video", "url": data["url"]})
    # cobalt-like variants
    for key in ("url", "video_url"):
        if isinstance(data.get(key), str):
            consume({"type": "video", "url": data[key]})

    return photos, videos


def best_per_video_group(videos: list[VideoItem]) -> list[VideoItem]:
    """多视频：按路径去掉 /WxH/ 后分组，每组只留最高清。"""
    groups: dict[str, VideoItem] = {}
    for v in videos:
        key = re.sub(r"/\d+x\d+/", "/WxH/", v.url)
        # amplify id 更稳
        m = re.search(r"/(?:amplify_video|ext_tw_video)/(\d+)/", v.url)
        if m:
            key = m.group(1)
        prev = groups.get(key)
        if not prev or v.pixels > prev.pixels:
            groups[key] = v
    return list(groups.values())


def from_ajax(post_url: str) -> ParseResult:
    return parse_best_media(post_url)


def ajax_all_videos(post_url: str) -> list[VideoItem]:
    """Keep the best quality for every distinct X video, not one per post."""
    html = ajax_search(post_url)
    videos: list[VideoItem] = []
    for proxy in dict.fromkeys(SNAPCDN.findall(html)):
        meta = decode_snapcdn(proxy) or {}
        url = meta.get("url") or ""
        if not is_video_url(url):
            continue
        width, height, pixels = video_resolution(url)
        videos.append(
            VideoItem(
                url=url,
                width=width,
                height=height,
                pixels=pixels,
                proxy_url=proxy,
                label="ajaxSearch",
            )
        )
    return best_per_video_group(videos)


def is_gif_url(url: str) -> bool:
    u = url.lower()
    return "tweet_video" in u or ".gif" in u.split("?")[0] or "/gif/" in u


def build_plan(post_url: str, mode: Mode) -> Plan:
    if not is_x_post_url(post_url):
        raise ValueError("请提供有效的 X/Twitter 帖子链接。")
    sources: list[str] = []

    if mode == "single_video":
        _, videos = parse_nichind(post_url)
        sources.append("nichind")
        videos = best_per_video_group(videos)
        # 单视频：只取像素面积最大的一条
        videos = sorted(videos, key=lambda v: v.pixels, reverse=True)[:1]
        if not videos:
            sources.append("ajaxSearch(fallback)")
            videos = ajax_all_videos(post_url)
        return Plan(
            mode,
            post_url,
            [],
            videos,
            "单视频：nichind 最高清（失败则 ajaxSearch）",
            sources,
        )

    if mode == "photo":
        photos, _ = parse_nichind(post_url)
        sources.append("nichind")
        if not photos:
            sources.append("ajaxSearch(fallback)")
            r = from_ajax(post_url)
            photos = r.photos
            # normalize urls
            photos = [
                PhotoItem(p.media_id, prefer_photo_url(p.url), p.proxy_url) for p in photos
            ]
        else:
            photos = [
                PhotoItem(p.media_id, prefer_photo_url(p.url), p.proxy_url) for p in photos
            ]
        return Plan(mode, post_url, photos, [], "图片：只下照片，最高清", sources)

    if mode == "gif":
        sources.append("ajaxSearch")
        r = from_ajax(post_url)
        # GIF 在 X 上常是 mp4（tweet_video）；也收集 ajax 全部 video 里像 gif 的
        html_videos = []
        # re-parse all qualities for gif-like
        from best_quality_download import ajax_search as _as, SNAPCDN, decode_snapcdn, is_video_url

        html = _as(post_url)
        gifs: list[VideoItem] = []
        for proxy in dict.fromkeys(SNAPCDN.findall(html)):
            meta = decode_snapcdn(proxy) or {}
            inner = meta.get("url") or ""
            if is_gif_url(inner) or (
                is_video_url(inner) and "tweet_video" in inner
            ):
                w, h, px = video_resolution(inner)
                gifs.append(
                    VideoItem(url=inner, width=w, height=h, pixels=px, proxy_url=proxy, label="gif")
                )
        gifs = best_per_video_group(gifs) if gifs else []
        # 若没识别到，不误下普通图
        return Plan(
            mode,
            post_url,
            [],
            gifs,
            "GIF：ajaxSearch 中 tweet_video / gif 最高清",
            sources,
        )

    if mode == "multi_video":
        _, videos = parse_nichind(post_url)
        sources.append("nichind")
        videos = [v for v in videos if not is_gif_url(v.url) or "amplify_video" in v.url or "ext_tw_video" in v.url]
        videos = best_per_video_group(videos)
        if not videos:
            sources.append("ajaxSearch(fallback)")
            videos = ajax_all_videos(post_url)
        return Plan(
            mode,
            post_url,
            [],
            videos,
            "多视频：nichind picker 中每个视频保留最高清",
            sources,
        )

    # auto
    photos, videos = parse_nichind(post_url)
    sources.append("nichind")
    photos = [PhotoItem(p.media_id, prefer_photo_url(p.url), p.proxy_url) for p in photos]
    videos = best_per_video_group(videos)

    if not photos and not videos:
        sources.append("ajaxSearch(fallback)")
        r = from_ajax(post_url)
        photos = [
            PhotoItem(p.media_id, prefer_photo_url(p.url), p.proxy_url) for p in r.photos
        ]
        videos = ajax_all_videos(post_url)

    kinds = []
    if photos:
        kinds.append(f"{len(photos)} 图")
    if videos:
        kinds.append(f"{len(videos)} 视频")
    note = "默认自动识别：" + (" + ".join(kinds) if kinds else "无媒体") + "（均最高清）"
    return Plan(mode, post_url, photos, videos, note, sources)


def execute_plan(
    plan: Plan,
    out_dir: Path,
    progress: Callable[[dict[str, Any]], None] | None = None,
    max_file_bytes: int | None = None,
    max_total_bytes: int | None = None,
    max_files: int | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    print(f"mode={plan.mode}")
    print(f"note={plan.note}")
    print(f"sources={plan.sources}")

    media: list[tuple[str, PhotoItem | VideoItem]] = [
        ("photo", photo) for photo in plan.photos
    ] + [("video", video) for video in plan.videos]
    total_files = len(media)
    if max_files is not None and total_files > max_files:
        raise RuntimeError(f"媒体数量 {total_files} 超过 {max_files} 个文件限制")
    if progress:
        progress({"type": "queue", "total_files": total_files})

    total_downloaded = 0
    for index, (kind, item) in enumerate(media, start=1):
        if kind == "photo":
            p = item
            assert isinstance(p, PhotoItem)
            filename = f"photo_{p.media_id}.jpg"
            url, proxy = p.url, p.proxy_url
        else:
            v = item
            assert isinstance(v, VideoItem)
            tag = f"{v.width}x{v.height}" if v.pixels else f"{index - 1}"
            media_match = re.search(r"/(?:amplify_video|ext_tw_video)/(\d+)/", v.url)
            media_id = media_match.group(1) if media_match else str(index - 1)
            filename = f"video_{media_id}_{tag}.mp4"
            url, proxy = v.url, v.proxy_url

        if progress:
            progress({
                "type": "file-start",
                "index": index,
                "total_files": total_files,
                "name": filename,
            })

        def report_bytes(downloaded: int, total: int | None) -> None:
            if progress:
                progress({
                    "type": "bytes",
                    "index": index,
                    "total_files": total_files,
                    "name": filename,
                    "downloaded": downloaded,
                    "total": total,
                })

        limit = max_file_bytes
        if max_total_bytes is not None:
            remaining = max_total_bytes - total_downloaded
            if remaining <= 0:
                raise RuntimeError("任务超过总下载大小限制")
            limit = remaining if limit is None else min(limit, remaining)
        path = download_one(
            url,
            proxy,
            out_dir / filename,
            report_bytes,
            max_bytes=limit,
        )
        saved.append(str(path))
        total_downloaded += path.stat().st_size
        print(f"  {kind} {path.name} ({path.stat().st_size:,} bytes)")
        if progress:
            progress({"type": "file-complete", "index": index, "total_files": total_files, "name": path.name})

    if not plan.photos and not plan.videos:
        print("  (nothing to download)")

    result = {
        "mode": plan.mode,
        "post_url": plan.post_url,
        "note": plan.note,
        "sources": plan.sources,
        "photos": [{k: v for k, v in asdict(p).items() if k != "proxy_url"} for p in plan.photos],
        "videos": [{k: v for k, v in asdict(v).items() if k != "proxy_url"} for v in plan.videos],
        "saved": saved,
        "endpoints": {
            "ajaxSearch": AJAX_API,
            "nichind": NICHIND,
            "nichind_site": "https://download.nichind.dev/",
        },
    }
    (out_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Mode-based X media downloader")
    ap.add_argument("url")
    ap.add_argument(
        "-m",
        "--mode",
        choices=["photo", "gif", "single_video", "multi_video", "auto"],
        default="auto",
    )
    ap.add_argument(
        "--progress-json",
        action="store_true",
        help="emit desktop progress events as PROGRESS_JSON lines",
    )
    ap.add_argument(
        "-o",
        "--out",
        default=str(DEFAULT_OUT),
    )
    ap.add_argument("--max-file-mb", type=int, default=DEFAULT_MAX_FILE_MB)
    ap.add_argument("--max-total-mb", type=int, default=DEFAULT_MAX_TOTAL_MB)
    ap.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    args = ap.parse_args()
    plan = build_plan(args.url, args.mode)
    out = Path(args.out) / args.mode
    def emit_progress(event: dict[str, Any]) -> None:
        print("PROGRESS_JSON:" + json.dumps(event, ensure_ascii=False), flush=True)

    execute_plan(
        plan,
        out,
        emit_progress if args.progress_json else None,
        max_file_bytes=mb_to_bytes(args.max_file_mb, "--max-file-mb"),
        max_total_bytes=mb_to_bytes(args.max_total_mb, "--max-total-mb"),
        max_files=args.max_files,
    )


if __name__ == "__main__":
    main()
