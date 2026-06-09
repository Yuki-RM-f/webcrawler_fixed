# -*- coding: utf-8 -*-

import json

import pytest


@pytest.mark.asyncio
async def test_jsonl_writer_preserves_image_urls_without_image_text_enrichment(tmp_path, monkeypatch):
    import config
    from tools.async_file_writer import AsyncFileWriter

    legacy_image_text_field = "image" + "_ocr_results"
    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(
        "tools.async_file_writer.utils.get_current_date",
        lambda: "2026-05-30",
    )

    writer = AsyncFileWriter(platform="xhs", crawler_type="search")
    await writer.write_to_jsonl(
        {"note_id": "x1", "image_list": "https://img.example/a.jpg"},
        "contents",
    )

    output_path = tmp_path / "xhs" / "jsonl" / "search_contents_2026-05-30.jsonl"
    row = json.loads(output_path.read_text(encoding="utf-8").strip())

    assert row["image_list"] == "https://img.example/a.jpg"
    assert legacy_image_text_field not in row


@pytest.mark.asyncio
async def test_jsonl_writer_escapes_raw_line_breaks_from_serialized_record(tmp_path, monkeypatch):
    import config
    from tools.async_file_writer import AsyncFileWriter

    monkeypatch.setattr(config, "SAVE_DATA_PATH", str(tmp_path))
    monkeypatch.setattr(
        "tools.async_file_writer.utils.get_current_date",
        lambda: "2026-05-31",
    )
    monkeypatch.setattr(
        "tools.async_file_writer.json.dumps",
        lambda item, ensure_ascii=False: '{"content":"first\r\nsecond\u0085third"}',
    )

    writer = AsyncFileWriter(platform="x", crawler_type="search")
    await writer.write_to_jsonl({"tweet_id": "x1"}, "contents")

    output_path = tmp_path / "x" / "jsonl" / "search_contents_2026-05-31.jsonl"
    raw = output_path.read_text(encoding="utf-8")
    record = raw.removesuffix("\n")

    assert "\r" not in record
    assert "\n" not in record
    assert record == '{"content":"first\\nsecond\\nthird"}'
