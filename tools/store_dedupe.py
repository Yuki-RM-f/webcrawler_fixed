# -*- coding: utf-8 -*-

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from tools import utils


FILE_SAVE_OPTIONS = {"csv", "json", "jsonl"}
ITEM_TYPES = ("contents", "comments")

PLATFORM_STORAGE_DIRS = {
    "dy": "douyin",
    "douyin": "douyin",
    "ks": "kuaishou",
    "kuaishou": "kuaishou",
    "wb": "weibo",
    "weibo": "weibo",
    "bili": "bili",
    "bilibili": "bili",
    "xhs": "xhs",
    "tieba": "tieba",
    "zhihu": "zhihu",
    "x": "x",
    "goofish": "goofish",
}

CONTENT_ID_FIELDS = {
    "xhs": "note_id",
    "tieba": "note_id",
    "wb": "note_id",
    "weibo": "note_id",
    "dy": "aweme_id",
    "douyin": "aweme_id",
    "ks": "video_id",
    "kuaishou": "video_id",
    "bili": "video_id",
    "bilibili": "video_id",
    "zhihu": "content_id",
    "x": "tweet_id",
    "goofish": "item_id",
}
CONTENT_ID_FIELD_CANDIDATES = ("note_id", "aweme_id", "video_id", "content_id", "tweet_id", "item_id")


@dataclass(frozen=True)
class DedupeResult:
    path: Path
    item_type: str
    key_field: str
    original_count: int
    deduped_count: int

    @property
    def removed_count(self) -> int:
        return self.original_count - self.deduped_count


def get_storage_platform(platform: str) -> str:
    return PLATFORM_STORAGE_DIRS.get(platform, platform)


def get_dedupe_key_field(platform: str, item_type: str) -> Optional[str]:
    if item_type == "comments":
        return "comment_id"
    if item_type != "contents":
        return None
    return CONTENT_ID_FIELDS.get(platform) or CONTENT_ID_FIELDS.get(get_storage_platform(platform))


def get_dedupe_key_field_from_headers(
    platform: str,
    item_type: str,
    headers: List[str],
) -> Optional[str]:
    key_field = get_dedupe_key_field(platform, item_type)
    if key_field in headers:
        return key_field
    if item_type == "contents":
        return next((field for field in CONTENT_ID_FIELD_CANDIDATES if field in headers), None)
    return None


def dedupe_records_by_key(records: List[Dict[str, Any]], key_field: str) -> List[Dict[str, Any]]:
    latest_index_by_key: Dict[str, int] = {}
    for index, record in enumerate(records):
        key = _record_key(record, key_field)
        if key is not None:
            latest_index_by_key[key] = index

    deduped: List[Dict[str, Any]] = []
    for index, record in enumerate(records):
        key = _record_key(record, key_field)
        if key is None or latest_index_by_key.get(key) == index:
            deduped.append(record)
    return deduped


def dedupe_current_crawl_files(
    platform: str,
    crawler_type: str,
    save_data_option: str,
    *,
    base_data_path: Optional[str] = None,
    current_date: Optional[str] = None,
) -> List[DedupeResult]:
    if save_data_option not in FILE_SAVE_OPTIONS:
        return []

    storage_platform = get_storage_platform(platform)
    data_root = Path(base_data_path or config.SAVE_DATA_PATH or "data")
    date_text = current_date or utils.get_current_date()
    results: List[DedupeResult] = []

    for item_type in ITEM_TYPES:
        key_field = get_dedupe_key_field(platform, item_type)
        if not key_field:
            continue
        path = (
            data_root
            / storage_platform
            / save_data_option
            / f"{crawler_type}_{item_type}_{date_text}.{save_data_option}"
        )
        if not path.exists():
            continue

        result = _dedupe_file(path, save_data_option, item_type, key_field)
        if result:
            results.append(result)

    return results


def _record_key(record: Dict[str, Any], key_field: str) -> Optional[str]:
    value = record.get(key_field)
    if value is None:
        return None
    key = str(value).strip()
    return key or None


def _dedupe_file(
    path: Path,
    save_data_option: str,
    item_type: str,
    key_field: str,
) -> Optional[DedupeResult]:
    if save_data_option == "jsonl":
        return _dedupe_jsonl(path, item_type, key_field)
    if save_data_option == "json":
        return _dedupe_json(path, item_type, key_field)
    if save_data_option == "csv":
        return _dedupe_csv(path, item_type, key_field)
    return None


def _dedupe_jsonl(path: Path, item_type: str, key_field: str) -> DedupeResult:
    entries: List[Dict[str, Any]] = []
    raw_entries: List[Optional[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            entries.append({})
            raw_entries.append(line)
            continue
        if isinstance(item, dict):
            entries.append(item)
            raw_entries.append(None)

    parsed_indexes = [index for index, raw in enumerate(raw_entries) if raw is None]
    parsed_records = [entries[index] for index in parsed_indexes]
    deduped_records = dedupe_records_by_key(parsed_records, key_field)
    if len(deduped_records) == len(parsed_records):
        return DedupeResult(path, item_type, key_field, len(parsed_records), len(deduped_records))

    keep_ids = {id(record) for record in deduped_records}
    output_lines: List[str] = []
    for entry, raw in zip(entries, raw_entries):
        if raw is not None:
            output_lines.append(raw)
        elif id(entry) in keep_ids:
            output_lines.append(json.dumps(entry, ensure_ascii=False))

    path.write_text("\n".join(output_lines) + ("\n" if output_lines else ""), encoding="utf-8")
    return DedupeResult(path, item_type, key_field, len(parsed_records), len(deduped_records))


def _dedupe_json(path: Path, item_type: str, key_field: str) -> DedupeResult:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return DedupeResult(path, item_type, key_field, 0, 0)

    records = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
    records = [record for record in records if isinstance(record, dict)]
    deduped = dedupe_records_by_key(records, key_field)
    if len(deduped) != len(records):
        path.write_text(json.dumps(deduped, ensure_ascii=False, indent=4), encoding="utf-8")
    return DedupeResult(path, item_type, key_field, len(records), len(deduped))


def _dedupe_csv(path: Path, item_type: str, key_field: str) -> DedupeResult:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        records = list(reader)

    deduped = dedupe_records_by_key(records, key_field)
    if len(deduped) != len(records):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(deduped)

    return DedupeResult(path, item_type, key_field, len(records), len(deduped))
