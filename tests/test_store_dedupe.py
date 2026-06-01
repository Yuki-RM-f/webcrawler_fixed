# -*- coding: utf-8 -*-

import csv
import importlib
import json
from pathlib import Path

import pytest

import config


def load_dedupe_module():
    try:
        return importlib.import_module("tools.store_dedupe")
    except ModuleNotFoundError:
        pytest.fail("tools.store_dedupe module is missing")


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def read_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_jsonl_dedupe_keeps_latest_contents_and_comments(tmp_path, monkeypatch):
    dedupe = load_dedupe_module()
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(dedupe.utils, "get_current_date", lambda: "2026-05-30")

    write_jsonl(
        tmp_path / "xhs" / "jsonl" / "search_contents_2026-05-30.jsonl",
        [
            {"note_id": "n1", "title": "old"},
            {"note_id": "", "title": "no-key"},
            {"note_id": "n1", "title": "new"},
            {"note_id": None, "title": "none-key"},
        ],
    )
    write_jsonl(
        tmp_path / "xhs" / "jsonl" / "search_comments_2026-05-30.jsonl",
        [
            {"comment_id": "c1", "content": "old"},
            {"comment_id": "c2", "content": "middle"},
            {"comment_id": "c1", "content": "new"},
        ],
    )

    dedupe.dedupe_current_crawl_files(
        platform="xhs",
        crawler_type="search",
        save_data_option="jsonl",
    )

    assert read_jsonl(tmp_path / "xhs" / "jsonl" / "search_contents_2026-05-30.jsonl") == [
        {"note_id": "", "title": "no-key"},
        {"note_id": "n1", "title": "new"},
        {"note_id": None, "title": "none-key"},
    ]
    assert read_jsonl(tmp_path / "xhs" / "jsonl" / "search_comments_2026-05-30.jsonl") == [
        {"comment_id": "c2", "content": "middle"},
        {"comment_id": "c1", "content": "new"},
    ]


def test_json_dedupe_maps_cli_platform_to_storage_directory(tmp_path, monkeypatch):
    dedupe = load_dedupe_module()
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(dedupe.utils, "get_current_date", lambda: "2026-05-30")

    contents_path = tmp_path / "douyin" / "json" / "search_contents_2026-05-30.json"
    contents_path.parent.mkdir(parents=True, exist_ok=True)
    contents_path.write_text(
        json.dumps(
            [
                {"aweme_id": "a1", "title": "old"},
                {"aweme_id": "a2", "title": "middle"},
                {"aweme_id": "a1", "title": "new"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    dedupe.dedupe_current_crawl_files(
        platform="dy",
        crawler_type="search",
        save_data_option="json",
    )

    assert json.loads(contents_path.read_text(encoding="utf-8")) == [
        {"aweme_id": "a2", "title": "middle"},
        {"aweme_id": "a1", "title": "new"},
    ]


def test_csv_dedupe_uses_x_tweet_and_comment_ids(tmp_path, monkeypatch):
    dedupe = load_dedupe_module()
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(dedupe.utils, "get_current_date", lambda: "2026-05-30")

    contents_path = tmp_path / "x" / "csv" / "search_contents_2026-05-30.csv"
    comments_path = tmp_path / "x" / "csv" / "search_comments_2026-05-30.csv"
    contents_path.parent.mkdir(parents=True, exist_ok=True)

    with contents_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["tweet_id", "content"])
        writer.writeheader()
        writer.writerows(
            [
                {"tweet_id": "t1", "content": "old"},
                {"tweet_id": "t2", "content": "middle"},
                {"tweet_id": "t1", "content": "new"},
            ]
        )
    with comments_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["comment_id", "content"])
        writer.writeheader()
        writer.writerows(
            [
                {"comment_id": "c1", "content": "old"},
                {"comment_id": "c1", "content": "new"},
            ]
        )

    dedupe.dedupe_current_crawl_files(
        platform="x",
        crawler_type="search",
        save_data_option="csv",
    )

    with contents_path.open("r", newline="", encoding="utf-8-sig") as f:
        assert list(csv.DictReader(f)) == [
            {"tweet_id": "t2", "content": "middle"},
            {"tweet_id": "t1", "content": "new"},
        ]
    with comments_path.open("r", newline="", encoding="utf-8-sig") as f:
        assert list(csv.DictReader(f)) == [
            {"comment_id": "c1", "content": "new"},
        ]


def test_jsonl_dedupe_uses_goofish_item_and_comment_ids(tmp_path, monkeypatch):
    dedupe = load_dedupe_module()
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(dedupe.utils, "get_current_date", lambda: "2026-05-30")

    write_jsonl(
        tmp_path / "goofish" / "jsonl" / "search_contents_2026-05-30.jsonl",
        [
            {"item_id": "i1", "title": "old"},
            {"item_id": "i2", "title": "middle"},
            {"item_id": "i1", "title": "new"},
        ],
    )
    write_jsonl(
        tmp_path / "goofish" / "jsonl" / "search_comments_2026-05-30.jsonl",
        [
            {"comment_id": "c1", "content": "old"},
            {"comment_id": "c1", "content": "new"},
        ],
    )

    dedupe.dedupe_current_crawl_files(
        platform="goofish",
        crawler_type="search",
        save_data_option="jsonl",
    )

    assert read_jsonl(tmp_path / "goofish" / "jsonl" / "search_contents_2026-05-30.jsonl") == [
        {"item_id": "i2", "title": "middle"},
        {"item_id": "i1", "title": "new"},
    ]
    assert read_jsonl(tmp_path / "goofish" / "jsonl" / "search_comments_2026-05-30.jsonl") == [
        {"comment_id": "c1", "content": "new"},
    ]


def test_dedupe_skips_database_storage_options(tmp_path, monkeypatch):
    dedupe = load_dedupe_module()
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(dedupe.utils, "get_current_date", lambda: "2026-05-30")

    contents_path = tmp_path / "xhs" / "jsonl" / "search_contents_2026-05-30.jsonl"
    original = [
        {"note_id": "n1", "title": "old"},
        {"note_id": "n1", "title": "new"},
    ]
    write_jsonl(contents_path, original)

    dedupe.dedupe_current_crawl_files(
        platform="xhs",
        crawler_type="search",
        save_data_option="db",
    )

    assert read_jsonl(contents_path) == original
