# -*- coding: utf-8 -*-

import pytest

import config
from media_platform.goofish.core import GoofishCrawler
from model.m_goofish import GoofishItem


class FakeKeyboard:
    def __init__(self, page):
        self.page = page

    async def press(self, key):
        self.page.pressed_keys.append(key)


class FakeNextLocator:
    def __init__(self, page):
        self.page = page

    async def count(self):
        return 1

    def nth(self, index):
        return self

    async def is_visible(self):
        return True

    async def is_enabled(self):
        return self.page.page_number < 2

    async def get_attribute(self, name):
        if name in {"aria-disabled", "disabled"} and self.page.page_number >= 2:
            return "true"
        return None

    async def click(self, timeout=None):
        self.page.events.append("click_next")
        self.page.page_number += 1
        self.page.next_clicks += 1


class FakeEmptyLocator:
    async def count(self):
        return 0

    def nth(self, index):
        return self


class FakePage:
    def __init__(self):
        self.page_number = 1
        self.next_clicks = 0
        self.events = []
        self.visited_urls = []
        self.pressed_keys = []
        self.keyboard = FakeKeyboard(self)

    async def goto(self, url, wait_until=None):
        self.events.append("goto")
        self.visited_urls.append(url)

    async def wait_for_timeout(self, timeout):
        return None

    async def wait_for_load_state(self, state=None, timeout=None):
        return None

    def locator(self, selector):
        if "search-page-tiny-arrow-right" in selector:
            return FakeNextLocator(self)
        return FakeEmptyLocator()


class FakeResponseClient:
    def __init__(self, events):
        self.events = events

    def clear(self, *api_names):
        self.events.append("clear_search")
        return None


def make_item(item_id):
    return GoofishItem(item_id=str(item_id), item_url=f"https://example.test/{item_id}")


@pytest.mark.asyncio
async def test_goofish_search_clicks_next_page_after_first_page_stops(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", "抖音 自动化")
    monkeypatch.setattr(config, "CRAWLER_MAX_NOTES_COUNT", 35)
    monkeypatch.setattr(config, "GOOFISH_SEARCH_MAX_SCROLL_TIMES", 10)
    monkeypatch.setattr(config, "CRAWLER_MAX_SLEEP_SEC", 0)

    crawler = GoofishCrawler()
    crawler.context_page = FakePage()
    crawler.response_client = FakeResponseClient(crawler.context_page.events)
    detailed_item_ids = []

    async def fake_get_item_detail(item):
        detailed_item_ids.append(item.item_id)

    def fake_extract_captured_search_items(seen_item_ids, target_count):
        if crawler.context_page.page_number == 1:
            candidates = [make_item(index) for index in range(30)]
        else:
            candidates = [make_item(index) for index in range(30, 40)]

        new_items = []
        for item in candidates:
            if item.item_id in seen_item_ids:
                continue
            seen_item_ids.add(item.item_id)
            new_items.append(item)
            if len(seen_item_ids) >= target_count:
                break
        return new_items

    monkeypatch.setattr(crawler, "get_item_detail", fake_get_item_detail)
    monkeypatch.setattr(
        crawler,
        "_extract_captured_search_items",
        fake_extract_captured_search_items,
    )

    await crawler.search()

    assert crawler.context_page.next_clicks == 1
    click_index = crawler.context_page.events.index("click_next")
    assert crawler.context_page.events[click_index - 1] == "clear_search"
    assert len(detailed_item_ids) == 35
    assert detailed_item_ids[-1] == "34"
