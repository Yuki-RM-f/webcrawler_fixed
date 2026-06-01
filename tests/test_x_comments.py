# -*- coding: utf-8 -*-

import config
import pytest

from media_platform.x.core import XBrowserCrawler
import store.x as x_store


@pytest.mark.asyncio
async def test_update_x_note_maps_image_list_to_file_store_fields(monkeypatch):
    stored_items = []

    class FakeStore:
        async def store_content(self, content_item):
            stored_items.append(content_item)

    monkeypatch.setattr("store.x.XStoreFactory.create_store", lambda: FakeStore())
    monkeypatch.setattr("store.x.utils.get_current_timestamp", lambda: 123456)

    await x_store.update_x_note(
        {
            "tweet_id": "tweet-1",
            "tweet_url": "https://x.com/alice/status/tweet-1",
            "content": "tweet with photo",
            "created_at": "Sat May 30 12:34:56 +0000 2026",
            "create_time": 1780144496,
            "user_id": "1001",
            "username": "alice",
            "nickname": "Alice",
            "avatar": "https://img.example/avatar.jpg",
            "image_list": "https://img.example/x-post.jpg",
            "source_keyword": "openai",
        }
    )

    assert stored_items == [
        {
            "tweet_id": "tweet-1",
            "tweet_url": "https://x.com/alice/status/tweet-1",
            "content": "tweet with photo",
            "created_at": "Sat May 30 12:34:56 +0000 2026",
            "create_time": 1780144496,
            "user_id": "1001",
            "username": "alice",
            "nickname": "Alice",
            "avatar": "https://img.example/avatar.jpg",
            "reply_count": "0",
            "retweet_count": "0",
            "like_count": "0",
            "quote_count": "0",
            "view_count": "0",
            "image_list": "https://img.example/x-post.jpg",
            "source_keyword": "openai",
            "last_modify_ts": 123456,
        }
    ]


@pytest.mark.asyncio
async def test_x_comment_search_saves_first_level_replies_with_limit(monkeypatch):
    crawler = XBrowserCrawler()
    saved_comments = []

    class FakeKeyboard:
        async def press(self, key):
            assert key == "End"

    class FakePage:
        def __init__(self):
            self.keyboard = FakeKeyboard()
            self.urls = []
            self.wait_count = 0

        async def goto(self, url, wait_until=None):
            self.urls.append(url)
            crawler._capture_comments(
                [
                    {
                        "tweet_id": "parent",
                        "content": "original",
                        "conversation_id_str": "parent",
                        "in_reply_to_status_id_str": "",
                    },
                    {
                        "tweet_id": "reply-1",
                        "content": "first reply",
                        "conversation_id_str": "parent",
                        "in_reply_to_status_id_str": "parent",
                    },
                    {
                        "tweet_id": "reply-1",
                        "content": "duplicate reply",
                        "conversation_id_str": "parent",
                        "in_reply_to_status_id_str": "parent",
                    },
                    {
                        "tweet_id": "nested",
                        "content": "nested reply",
                        "conversation_id_str": "parent",
                        "in_reply_to_status_id_str": "reply-1",
                    },
                ],
                "parent",
            )

        async def wait_for_timeout(self, timeout):
            self.wait_count += 1
            if self.wait_count == 1:
                crawler._capture_comments(
                    [
                        {
                            "tweet_id": "reply-2",
                            "content": "second reply",
                            "conversation_id_str": "parent",
                            "in_reply_to_status_id_str": "parent",
                        },
                        {
                            "tweet_id": "reply-3",
                            "content": "third reply",
                            "conversation_id_str": "parent",
                            "in_reply_to_status_id_str": "parent",
                        },
                    ],
                    "parent",
                )

    async def fake_store(tweet_id, comment, keyword):
        saved_comments.append((tweet_id, comment["tweet_id"], keyword))

    async def fake_sleep(_):
        return None

    monkeypatch.setattr(config, "CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", 2)
    monkeypatch.setattr(config, "X_COMMENT_SEARCH_MAX_SCROLL_TIMES", 5)
    monkeypatch.setattr(config, "X_COMMENT_SCROLL_WAIT_MS", 0)
    monkeypatch.setattr(config, "ENABLE_GET_SUB_COMMENTS", False)
    monkeypatch.setattr(crawler, "context_page", FakePage())
    monkeypatch.setattr("media_platform.x.core.x_store.update_x_note_comment", fake_store)
    monkeypatch.setattr("media_platform.x.core.asyncio.sleep", fake_sleep)

    await crawler.get_tweet_comments({"tweet_id": "parent"}, "openai")

    assert saved_comments == [
        ("parent", "reply-1", "openai"),
        ("parent", "reply-2", "openai"),
    ]
    assert crawler.context_page.urls == [
        "https://x.com/search?q=conversation_id%3Aparent&src=typed_query&f=live"
    ]


@pytest.mark.asyncio
async def test_update_x_note_comment_maps_file_store_fields(monkeypatch):
    stored_items = []

    class FakeStore:
        async def store_comment(self, comment_item):
            stored_items.append(comment_item)

    monkeypatch.setattr("store.x.XStoreFactory.create_store", lambda: FakeStore())
    monkeypatch.setattr("store.x.utils.get_current_timestamp", lambda: 123456)

    await x_store.update_x_note_comment(
        "parent",
        {
            "tweet_id": "reply-1",
            "tweet_url": "https://x.com/alice/status/reply-1",
            "content": "first reply",
            "created_at": "Sat May 30 12:34:56 +0000 2026",
            "create_time": 1780144496,
            "user_id": "1001",
            "username": "alice",
            "nickname": "Alice",
            "avatar": "https://img.example/avatar.jpg",
            "reply_count": "1",
            "retweet_count": "2",
            "like_count": "3",
            "quote_count": "4",
            "view_count": "42",
            "in_reply_to_status_id_str": "parent",
            "image_list": "https://img.example/x-reply.jpg",
        },
        "openai",
    )

    assert stored_items == [
        {
            "comment_id": "reply-1",
            "tweet_id": "parent",
            "parent_comment_id": "parent",
            "comment_url": "https://x.com/alice/status/reply-1",
            "content": "first reply",
            "created_at": "Sat May 30 12:34:56 +0000 2026",
            "create_time": 1780144496,
            "user_id": "1001",
            "username": "alice",
            "nickname": "Alice",
            "avatar": "https://img.example/avatar.jpg",
            "reply_count": "1",
            "retweet_count": "2",
            "like_count": "3",
            "quote_count": "4",
            "view_count": "42",
            "pictures": "https://img.example/x-reply.jpg",
            "source_keyword": "openai",
            "last_modify_ts": 123456,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("store_path", "writer_name"),
    [
        ("store.x.XCsvStoreImplement", "write_to_csv"),
        ("store.x.XJsonStoreImplement", "write_single_item_to_json"),
        ("store.x.XJsonlStoreImplement", "write_to_jsonl"),
    ],
)
async def test_x_file_stores_write_comments_to_comment_items(monkeypatch, store_path, writer_name):
    calls = []
    store_cls = __import__(store_path.rsplit(".", 1)[0], fromlist=[store_path.rsplit(".", 1)[1]])
    store = getattr(store_cls, store_path.rsplit(".", 1)[1])()

    async def fake_write(item_type, item):
        calls.append((item_type, item))

    monkeypatch.setattr(store.writer, writer_name, fake_write)

    await store.store_comment({"comment_id": "reply-1"})

    assert calls == [("comments", {"comment_id": "reply-1"})]
