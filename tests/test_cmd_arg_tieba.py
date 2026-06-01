# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd
from model.m_baidu_tieba import TiebaNote
from media_platform.tieba import TieBaCrawler


@pytest.mark.asyncio
async def test_tieba_detail_cli_sets_specified_ids():
    await parse_cmd(
        [
            "--platform",
            "tieba",
            "--type",
            "detail",
            "--specified_id",
            "https://tieba.baidu.com/p/10451142633,9835114923",
        ]
    )

    assert config.TIEBA_SPECIFIED_ID_LIST == ["10451142633", "9835114923"]


@pytest.mark.asyncio
async def test_tieba_creator_cli_sets_creator_urls():
    await parse_cmd(
        [
            "--platform",
            "tieba",
            "--type",
            "creator",
            "--creator_id",
            "tb.1.example,https://tieba.baidu.com/home/main?id=tb.1.raw",
        ]
    )

    assert config.TIEBA_CREATOR_URL_LIST == [
        "https://tieba.baidu.com/home/main?id=tb.1.example",
        "https://tieba.baidu.com/home/main?id=tb.1.raw",
    ]


@pytest.mark.asyncio
async def test_tieba_detail_reads_runtime_specified_ids(monkeypatch):
    crawler = TieBaCrawler()
    seen_note_ids = []

    async def fake_get_note_detail(note_id, semaphore):
        seen_note_ids.append(note_id)
        return None

    async def fake_batch_get_comments(note_details):
        return None

    monkeypatch.setattr(config, "TIEBA_SPECIFIED_ID_LIST", ["10451142633"])
    monkeypatch.setattr(crawler, "get_note_detail_async_task", fake_get_note_detail)
    monkeypatch.setattr(crawler, "batch_get_note_comments", fake_batch_get_comments)

    await crawler.get_specified_notes()

    assert seen_note_ids == ["10451142633"]


@pytest.mark.asyncio
async def test_tieba_search_uses_actual_unique_note_count(monkeypatch):
    crawler = TieBaCrawler()
    requested_pages = []
    fetched_note_ids = []

    class FakeTiebaClient:
        async def get_notes_by_keyword(self, keyword, page, page_size, sort, note_type):
            requested_pages.append(page)
            if page == 1:
                note_ids = [str(1000 + index) for index in range(10)]
            elif page == 2:
                note_ids = ["1009", "1010", "1011", "1012"]
            else:
                note_ids = []
            return [
                TiebaNote(
                    note_id=note_id,
                    title="title",
                    note_url=f"https://tieba.baidu.com/p/{note_id}",
                    tieba_name="test",
                    tieba_link="https://tieba.baidu.com/f?kw=test",
                )
                for note_id in note_ids
            ]

    async def fake_get_specified_notes(note_id_list=None):
        fetched_note_ids.extend(note_id_list or [])

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(config, "KEYWORDS", "keyword")
    monkeypatch.setattr(config, "START_PAGE", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 12)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    crawler.tieba_client = FakeTiebaClient()
    monkeypatch.setattr(crawler, "get_specified_notes", fake_get_specified_notes)
    monkeypatch.setattr("media_platform.tieba.core.asyncio.sleep", fake_sleep)

    await crawler.search()

    assert requested_pages == [1, 2]
    assert fetched_note_ids == [str(1000 + index) for index in range(12)]
