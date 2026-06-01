# -*- coding: utf-8 -*-

import asyncio

import httpx
import pytest

import config
from media_platform.xhs.client import XiaoHongShuClient
from media_platform.xhs.core import XiaoHongShuCrawler
from media_platform.xhs.exception import DataFetchError, XHSVerificationError


class FakeAsyncClient:
    def __init__(self, responses, calls):
        self._responses = responses
        self._calls = calls

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method, url, timeout=None, **kwargs):
        self._calls.append((method, url))
        return self._responses.pop(0)


def make_client() -> XiaoHongShuClient:
    return XiaoHongShuClient(
        headers={},
        playwright_page=None,
        cookie_dict={},
    )


@pytest.mark.asyncio
async def test_xhs_request_pauses_and_retries_verify_response_without_headers(monkeypatch):
    calls = []
    sleeps = []
    responses = [
        httpx.Response(471, text="risk verification", request=httpx.Request("GET", "https://example.com/check")),
        httpx.Response(200, json={"success": True, "data": {"ok": True}}, request=httpx.Request("GET", "https://example.com/check")),
    ]

    monkeypatch.setattr(config, "XHS_VERIFY_PAUSE_SECONDS", 7, raising=False)
    monkeypatch.setattr(config, "XHS_VERIFY_MAX_RETRIES", 2, raising=False)
    monkeypatch.setattr("media_platform.xhs.client.make_async_client", lambda proxy=None: FakeAsyncClient(responses, calls))

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr("media_platform.xhs.client.asyncio.sleep", fake_sleep)

    result = await make_client().request("GET", "https://example.com/check")

    assert result == {"ok": True}
    assert calls == [("GET", "https://example.com/check"), ("GET", "https://example.com/check")]
    assert sleeps == [7]


@pytest.mark.asyncio
async def test_xhs_comment_batch_continues_after_comment_fetch_error(monkeypatch):
    calls = []
    crawler = XiaoHongShuCrawler()

    class FakeXhsClient:
        async def get_note_all_comments(self, note_id, **kwargs):
            calls.append(note_id)
            if note_id == "risk_note":
                raise DataFetchError("risk verification")

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "MAX_CONCURRENCY_NUM", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)
    monkeypatch.setattr("media_platform.xhs.core.asyncio.sleep", fake_sleep)
    crawler.xhs_client = FakeXhsClient()

    await crawler.batch_get_note_comments(["risk_note", "next_note"], ["token1", "token2"])

    assert calls == ["risk_note", "next_note"]


@pytest.mark.asyncio
async def test_xhs_comment_batch_stops_after_verification_retries_exhausted(monkeypatch):
    calls = []
    crawler = XiaoHongShuCrawler()

    class FakeXhsClient:
        async def get_note_all_comments(self, note_id, **kwargs):
            calls.append(note_id)
            raise XHSVerificationError("risk verification")

    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "MAX_CONCURRENCY_NUM", 1)
    crawler.xhs_client = FakeXhsClient()

    with pytest.raises(XHSVerificationError):
        await crawler.batch_get_note_comments(["risk_note", "next_note"], ["token1", "token2"])

    assert calls == ["risk_note"]


@pytest.mark.asyncio
async def test_xhs_note_detail_stops_after_verification_retries_exhausted(monkeypatch):
    crawler = XiaoHongShuCrawler()

    class FakeXhsClient:
        async def get_note_by_id(self, note_id, xsec_source, xsec_token):
            raise XHSVerificationError("risk verification")

        async def get_note_by_id_from_html(self, note_id, xsec_source, xsec_token, enable_cookie=True):
            raise AssertionError("should not fall back after verification failure")

    crawler.xhs_client = FakeXhsClient()

    with pytest.raises(XHSVerificationError):
        await crawler.get_note_detail_async_task(
            note_id="risk_note",
            xsec_source="source",
            xsec_token="token",
            semaphore=asyncio.Semaphore(1),
        )


@pytest.mark.asyncio
async def test_xhs_sub_comment_batch_stops_after_verification_retries_exhausted(monkeypatch):
    client = make_client()

    async def fake_get_note_sub_comments(**kwargs):
        raise XHSVerificationError("risk verification")

    monkeypatch.setattr(config, "ENABLE_GET_SUB_COMMENTS", True)
    monkeypatch.setattr(client, "get_note_sub_comments", fake_get_note_sub_comments)

    comments = [
        {
            "note_id": "risk_note",
            "id": "root_comment",
            "sub_comment_has_more": True,
            "sub_comment_cursor": "",
        }
    ]

    with pytest.raises(XHSVerificationError):
        await client.get_comments_all_sub_comments(comments=comments, xsec_token="token")


@pytest.mark.asyncio
async def test_xhs_search_stops_after_keyword_verification_retries_exhausted(monkeypatch):
    crawler = XiaoHongShuCrawler()

    class FakeXhsClient:
        async def get_note_by_keyword(self, **kwargs):
            raise XHSVerificationError("risk verification")

    monkeypatch.setattr(config, "KEYWORDS", "risk keyword")
    monkeypatch.setattr(config, "START_PAGE", 1)
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 20)
    crawler.xhs_client = FakeXhsClient()

    with pytest.raises(XHSVerificationError):
        await crawler.search()


@pytest.mark.asyncio
async def test_xhs_pong_stops_after_verification_retries_exhausted(monkeypatch):
    client = make_client()

    async def fake_query_self():
        raise XHSVerificationError("risk verification")

    monkeypatch.setattr(client, "query_self", fake_query_self)

    with pytest.raises(XHSVerificationError):
        await client.pong()
