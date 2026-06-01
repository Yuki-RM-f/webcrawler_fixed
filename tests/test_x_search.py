# -*- coding: utf-8 -*-

import config
import pytest

from media_platform.x.core import XBrowserCrawler


@pytest.mark.asyncio
async def test_x_search_scrolls_until_target_count_and_deduplicates(monkeypatch):
    crawler = XBrowserCrawler()
    saved_items = []

    class FakeKeyboard:
        async def press(self, key):
            assert key == "End"

    class FakePage:
        def __init__(self):
            self.keyboard = FakeKeyboard()
            self.urls = []
            self.scroll_count = 0

        async def goto(self, url, wait_until=None):
            self.urls.append(url)
            crawler._capture_tweets(
                [
                    {"tweet_id": "1", "content": "first"},
                    {"tweet_id": "2", "content": "second"},
                    {"tweet_id": "2", "content": "duplicate"},
                ]
            )

        async def wait_for_timeout(self, timeout):
            self.scroll_count += 1
            if self.scroll_count == 1:
                crawler._capture_tweets([{"tweet_id": "3", "content": "third"}])
            elif self.scroll_count == 2:
                crawler._capture_tweets([{"tweet_id": "4", "content": "fourth"}])

    async def fake_store(item):
        saved_items.append(item)

    async def fail_get_tweet_comments(tweet, keyword):
        raise AssertionError("comments should not be fetched when ENABLE_GET_COMMENTS is false")

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(config, "KEYWORDS", "openai")
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 3)
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", False)
    monkeypatch.setattr(config, "X_SEARCH_MAX_SCROLL_TIMES", 5)
    monkeypatch.setattr(config, "X_SEARCH_SCROLL_WAIT_MS", 0)
    monkeypatch.setattr(crawler, "context_page", FakePage())
    monkeypatch.setattr(crawler, "get_tweet_comments", fail_get_tweet_comments)
    monkeypatch.setattr("media_platform.x.core.x_store.update_x_note", fake_store)
    monkeypatch.setattr("media_platform.x.core.asyncio.sleep", fake_sleep)

    await crawler.search()

    assert [item["tweet_id"] for item in saved_items] == ["1", "2", "3"]
    assert saved_items[0]["source_keyword"] == "openai"
    assert crawler.context_page.urls == [
        "https://x.com/search?q=openai&src=typed_query&f=live"
    ]


@pytest.mark.asyncio
async def test_x_search_fetches_comments_when_enabled(monkeypatch):
    crawler = XBrowserCrawler()
    saved_items = []
    comment_calls = []

    class FakeKeyboard:
        async def press(self, key):
            assert key == "End"

    class FakePage:
        def __init__(self):
            self.keyboard = FakeKeyboard()

        async def goto(self, url, wait_until=None):
            crawler._capture_tweets(
                [
                    {"tweet_id": "1", "content": "first"},
                    {"tweet_id": "2", "content": "second"},
                ]
            )

        async def wait_for_timeout(self, timeout):
            return None

    async def fake_store(item):
        saved_items.append(item)

    async def fake_get_tweet_comments(tweet, keyword):
        comment_calls.append((tweet["tweet_id"], keyword))

    monkeypatch.setattr(config, "KEYWORDS", "openai")
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 2)
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "X_SEARCH_MAX_SCROLL_TIMES", 0)
    monkeypatch.setattr(config, "X_SEARCH_SCROLL_WAIT_MS", 0)
    monkeypatch.setattr(crawler, "context_page", FakePage())
    monkeypatch.setattr(crawler, "get_tweet_comments", fake_get_tweet_comments)
    monkeypatch.setattr("media_platform.x.core.x_store.update_x_note", fake_store)

    await crawler.search()

    assert [item["tweet_id"] for item in saved_items] == ["1", "2"]
    assert comment_calls == [("1", "openai"), ("2", "openai")]
