# -*- coding: utf-8 -*-

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Query

router = APIRouter(prefix="/black-gray-intel", tags=["black-gray-intel"])

DATA_DIR = Path(__file__).parent.parent.parent / "data"

PLATFORM_DIRS = {
    "dy": "douyin",
    "tieba": "tieba",
    "xhs": "xhs",
    "x": "x",
    "goofish": "goofish",
    "xianyu": "goofish",
}

KIND_FILE_PARTS = {
    "contents": "contents",
    "comments": "comments",
}

LEGACY_IMAGE_TEXT_RESULTS_FIELD = "image" + "_ocr_results"


@router.get("/records")
async def list_black_gray_intel_records(
    platform: Literal["dy", "tieba", "xhs", "x", "goofish", "xianyu"],
    kind: Literal["contents", "comments", "all"] = "all",
    date: str = "latest",
    limit: int = Query(default=500, ge=1, le=50000),
    offset: int = Query(default=0, ge=0),
):
    platform = _canonical_platform(platform)
    selected_kinds = ["contents", "comments"] if kind == "all" else [kind]
    files = _select_source_files(platform, selected_kinds, date)
    warnings: list[str] = []
    records: list[dict[str, Any]] = []

    if not files:
        warnings.append("No MediaCrawler JSONL files found for the requested platform, kind, and date")

    for record_kind, file_path in files:
        records.extend(_read_records(platform, record_kind, file_path, warnings))

    return {
        "items": records[offset : offset + limit],
        "total": len(records),
        "source_files": [_relative_source_path(file_path) for _, file_path in files],
        "warnings": warnings,
    }


def _select_source_files(platform: str, kinds: list[str], date: str) -> list[tuple[str, Path]]:
    platform_dir = DATA_DIR / PLATFORM_DIRS[platform] / "jsonl"
    if date != "latest" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return []

    selected: list[tuple[str, Path]] = []
    for record_kind in kinds:
        if date == "latest":
            file_path = _latest_file(platform_dir, record_kind)
        else:
            file_path = platform_dir / f"search_{KIND_FILE_PARTS[record_kind]}_{date}.jsonl"
            if not file_path.exists():
                file_path = None
        if file_path:
            selected.append((record_kind, file_path))
    return selected


def _latest_file(platform_dir: Path, record_kind: str) -> Path | None:
    pattern = f"search_{KIND_FILE_PARTS[record_kind]}_*.jsonl"
    candidates = [path for path in platform_dir.glob(pattern) if _date_from_file(path)]
    if not candidates:
        return None
    return max(candidates, key=lambda path: _date_from_file(path) or "")


def _date_from_file(path: Path) -> str | None:
    match = re.search(r"_(\d{4}-\d{2}-\d{2})\.jsonl$", path.name)
    return match.group(1) if match else None


def _read_records(platform: str, record_kind: str, file_path: Path, warnings: list[str]) -> list[dict[str, Any]]:
    records = []
    with file_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                warnings.append(f"Skipped invalid JSON in {_relative_source_path(file_path)}:{line_number}: {exc.msg}")
                continue
            if not isinstance(item, dict):
                warnings.append(f"Skipped non-object JSON in {_relative_source_path(file_path)}:{line_number}")
                continue
            records.append(_map_record(platform, record_kind, item))
    return records


def _map_record(platform: str, record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    if platform == "dy":
        return _map_douyin(record_kind, item)
    if platform == "tieba":
        return _map_tieba(record_kind, item)
    if platform == "xhs":
        return _map_xhs(record_kind, item)
    if platform == "x":
        return _map_x(record_kind, item)
    return _map_goofish(record_kind, item)


def _map_douyin(record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    aweme_id = _string(item.get("aweme_id"))
    is_comment = record_kind == "comments"
    record_id = _string(item.get("comment_id")) if is_comment else aweme_id
    source_url = _string(item.get("aweme_url")) or (f"https://www.douyin.com/video/{aweme_id}" if aweme_id else "")
    sec_uid = _string(item.get("sec_uid"))
    return _record(
        source_record_id=f"douyin:{'comment' if is_comment else 'aweme'}:{record_id}",
        source_type="social_media",
        source_name="抖音",
        source_url=source_url,
        author_id=_string(item.get("user_id")),
        author_name=_string(item.get("nickname")),
        author_homepage_url=f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "",
        publish_time=_normalize_time(item.get("create_time")),
        crawl_time=_normalize_time(item.get("last_modify_ts")),
        raw_text=_join_text([item.get("content")] if is_comment else [item.get("title"), item.get("desc")]),
        media_files=(
            _media_files(item.get("pictures"), "image", "comment")
            if is_comment
            else [
                *_media_files(item.get("cover_url"), "image", "original_post"),
                *_media_files(item.get("video_download_url"), "video", "original_post"),
                *_media_files(item.get("note_download_url"), "attachment", "original_post"),
            ]
        ),
        metadata=_metadata(item, "dy", record_kind, aweme_id),
    )


def _map_tieba(record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    note_id = _string(item.get("note_id"))
    is_comment = record_kind == "comments"
    record_id = _string(item.get("comment_id")) if is_comment else note_id
    source_url = _string(item.get("note_url")) or (f"https://tieba.baidu.com/p/{note_id}" if note_id else "")
    author_homepage_url = _string(item.get("user_link"))
    return _record(
        source_record_id=f"tieba:{'comment' if is_comment else 'post'}:{record_id}",
        source_type="forum",
        source_name="百度贴吧",
        source_url=source_url,
        author_id=_tieba_author_id(author_homepage_url),
        author_name=_string(item.get("user_nickname")),
        author_homepage_url=author_homepage_url,
        publish_time=_normalize_time(item.get("publish_time")),
        crawl_time=_normalize_time(item.get("last_modify_ts")),
        raw_text=_join_text([item.get("content")] if is_comment else [item.get("title"), item.get("desc")]),
        media_files=(
            _media_files(item.get("pictures"), "image", "comment")
            if is_comment
            else _media_files(item.get("image_list"), "image", "original_post")
        ),
        metadata=_metadata(item, "tieba", record_kind, note_id),
    )


def _map_xhs(record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    note_id = _string(item.get("note_id"))
    is_comment = record_kind == "comments"
    record_id = _string(item.get("comment_id")) if is_comment else note_id
    source_url = _string(item.get("note_url")) or (f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "")
    author_id = _string(item.get("user_id"))
    return _record(
        source_record_id=f"xhs:{'comment' if is_comment else 'note'}:{record_id}",
        source_type="social_media",
        source_name="小红书",
        source_url=source_url,
        author_id=author_id,
        author_name=_string(item.get("nickname")),
        author_homepage_url=f"https://www.xiaohongshu.com/user/profile/{author_id}" if author_id else "",
        publish_time=_normalize_time(item.get("create_time") if is_comment else item.get("time")),
        crawl_time=_normalize_time(item.get("last_modify_ts") or item.get("last_update_time")),
        raw_text=_join_text([item.get("content")] if is_comment else [item.get("title"), item.get("desc")]),
        media_files=(
            _media_files(item.get("pictures"), "image", "comment")
            if is_comment
            else [
                *_media_files(item.get("image_list"), "image", "original_post"),
                *_media_files(item.get("video_url"), "video", "original_post"),
            ]
        ),
        metadata=_metadata(item, "xhs", record_kind, note_id),
    )


def _map_x(record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    tweet_id = _string(item.get("tweet_id"))
    is_comment = record_kind == "comments"
    record_id = _string(item.get("comment_id")) if is_comment else tweet_id
    username = _string(item.get("username"))
    source_url = _string(item.get("comment_url") if is_comment else item.get("tweet_url"))
    if not source_url and record_id:
        source_url = f"https://x.com/i/status/{record_id}"
    return _record(
        source_record_id=f"x:{'comment' if is_comment else 'tweet'}:{record_id}",
        source_type="social_media",
        source_name="X",
        source_url=source_url,
        author_id=_string(item.get("user_id")),
        author_name=_string(item.get("nickname")) or username,
        author_homepage_url=f"https://x.com/{username}" if username else "",
        publish_time=_normalize_time(item.get("created_at") or item.get("create_time")),
        crawl_time=_normalize_time(item.get("last_modify_ts")),
        raw_text=_string(item.get("content")),
        media_files=_media_files(item.get("pictures") if is_comment else item.get("image_list"), "image", "comment" if is_comment else "original_post"),
        metadata=_metadata(item, "x", record_kind, tweet_id),
    )


def _map_goofish(record_kind: str, item: dict[str, Any]) -> dict[str, Any]:
    item_id = _string(item.get("item_id"))
    is_comment = record_kind == "comments"
    record_id = _string(item.get("comment_id")) if is_comment else item_id
    source_url = _string(item.get("item_url")) or (f"https://www.goofish.com/item?id={item_id}" if item_id else "")
    return _record(
        source_record_id=f"goofish:{'comment' if is_comment else 'item'}:{record_id}",
        source_type="vertical_site",
        source_name="闲鱼",
        source_url=source_url,
        author_id=_string(item.get("user_id") if is_comment else item.get("seller_id")),
        author_name=_string(item.get("nickname") if is_comment else item.get("seller_nickname")),
        author_homepage_url="" if is_comment else _string(item.get("seller_homepage_url")),
        publish_time=_normalize_time(item.get("publish_time")),
        crawl_time=_normalize_time(item.get("last_modify_ts")),
        raw_text=(
            _string(item.get("content"))
            if is_comment
            else _join_text(
                [
                    item.get("title"),
                    item.get("desc"),
                    f"价格: {item.get('price')}" if _string(item.get("price")) else "",
                    f"位置: {item.get('location')}" if _string(item.get("location")) else "",
                ]
            )
        ),
        media_files=(
            _media_files(item.get("pictures"), "image", "comment")
            if is_comment
            else _media_files_with_goofish_ocr(item.get("image_list"), item)
        ),
        metadata=_metadata(item, "goofish", record_kind, item_id),
    )


def _record(
    *,
    source_record_id: str,
    source_type: str,
    source_name: str,
    source_url: str,
    author_id: str,
    author_name: str,
    author_homepage_url: str,
    publish_time: str | None,
    crawl_time: str | None,
    raw_text: str,
    media_files: list[dict[str, str]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_record_id": source_record_id,
        "source_type": source_type,
        "source_name": source_name,
        "source_url": source_url,
        "author_id": author_id,
        "author_name": author_name,
        "author_homepage_url": author_homepage_url,
        "publish_time": publish_time,
        "crawl_time": crawl_time,
        "raw_text": raw_text,
        "media_files": media_files,
        "metadata": metadata,
    }


def _metadata(item: dict[str, Any], platform: str, record_kind: str, parent_content_id: str) -> dict[str, Any]:
    metadata = dict(item)
    if platform != "goofish":
        metadata.pop(LEGACY_IMAGE_TEXT_RESULTS_FIELD, None)
    metadata["record_kind"] = record_kind
    metadata["media_crawler_platform"] = platform
    metadata["source_keyword"] = _string(item.get("source_keyword"))
    metadata["parent_content_id"] = parent_content_id
    return metadata


def _normalize_time(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or re.fullmatch(r"\d+(\.\d+)?", str(value)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")
        except ValueError:
            return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _join_text(values: list[Any]) -> str:
    return "\n".join(_string(value).strip() for value in values if _string(value).strip())


def _media_files(value: Any, file_type: str, source: str) -> list[dict[str, str]]:
    return [
        {"file_url": url, "file_type": file_type, "source": source}
        for url in _urls(value)
        if url
    ]


def _media_files_with_goofish_ocr(value: Any, item: dict[str, Any]) -> list[dict[str, str]]:
    media_files = _media_files(value, "image", "original_post")
    ocr_by_url = {
        _string(result.get("image_url")): result
        for result in item.get(LEGACY_IMAGE_TEXT_RESULTS_FIELD, []) or []
        if isinstance(result, dict)
    }
    for media in media_files:
        result = ocr_by_url.get(media["file_url"])
        if not result:
            continue
        media["ocr_source"] = "media_crawler_image_ocr"
        media["ocr_provider"] = "mediacrawler"
        text = _string(result.get("text"))
        error = _string(result.get("error"))
        status = _string(result.get("status"))
        if text:
            media["ocr_text"] = text
        if error:
            media["ocr_error"] = error
        elif status and status != "done":
            media["ocr_error"] = status
    return media_files


def _urls(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, dict):
        return [_string(value.get("file_url") or value.get("url") or value.get("src"))]
    if isinstance(value, list):
        urls: list[str] = []
        for item in value:
            urls.extend(_urls(item))
        return urls
    text = _string(value).strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            return _urls(json.loads(text))
        except json.JSONDecodeError:
            pass
    return [part.strip() for part in text.split(",") if part.strip()]


def _tieba_author_id(author_homepage_url: str) -> str:
    if not author_homepage_url:
        return ""
    values = parse_qs(urlparse(author_homepage_url).query).get("id")
    return values[0] if values else author_homepage_url.rstrip("/").split("/")[-1]


def _canonical_platform(platform: str) -> str:
    return "goofish" if platform == "xianyu" else platform


def _string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _relative_source_path(path: Path) -> str:
    try:
        return path.relative_to(DATA_DIR).as_posix()
    except ValueError:
        return path.as_posix()
