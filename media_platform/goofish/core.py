# -*- coding: utf-8 -*-

import asyncio
import os
from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import BrowserContext, BrowserType, Page, Playwright, async_playwright

import config
from base.base_crawler import AbstractCrawler
from model.m_goofish import GoofishCreator, GoofishItem
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import goofish as goofish_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .client import DETAIL_API, RECOMMEND_API, SEARCH_API, GoofishResponseClient
from .help import GoofishExtractor
from .login import GoofishLogin


class GoofishCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.goofish.com"
        self.cookie_urls = [self.index_url, "https://www.taobao.com"]
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None
        self.response_client = GoofishResponseClient()
        self._response_tasks: List[asyncio.Task] = []
        self._warned_comments_unavailable = False

    async def start(self) -> None:
        playwright_proxy_format = None
        if config.ENABLE_IP_PROXY:
            ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await ip_proxy_pool.get_proxy()
            playwright_proxy_format, _ = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[GoofishCrawler] Launching browser in CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=False,
                )
            else:
                utils.logger.warning(
                    "[GoofishCrawler] Standard/headless browser mode may be blocked by Goofish; CDP real Chrome is recommended"
                )
                self.browser_context = await self.launch_browser(
                    playwright.chromium,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.HEADLESS,
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            self._bind_response_listener()
            await self.context_page.goto(self.index_url, wait_until="domcontentloaded")
            login = GoofishLogin(
                login_type=config.LOGIN_TYPE,
                browser_context=self.browser_context,
                context_page=self.context_page,
                cookie_str=config.COOKIES,
            )
            await login.begin()

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_items()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_items()

            await self._drain_response_tasks()
            utils.logger.info("[GoofishCrawler.start] Goofish Crawler finished ...")

    def _bind_response_listener(self) -> None:
        self.context_page.on(
            "response",
            lambda response: self._response_tasks.append(
                asyncio.create_task(self.response_client.capture_response(response))
            ),
        )

    async def _drain_response_tasks(self) -> None:
        if not self._response_tasks:
            return
        tasks = self._response_tasks
        self._response_tasks = []
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _wait_for_responses(self) -> None:
        await self.context_page.wait_for_timeout(config.GOOFISH_RESPONSE_WAIT_MS)
        await self._drain_response_tasks()

    async def search(self) -> None:
        utils.logger.info("[GoofishCrawler.search] Begin search Goofish keywords")
        target_count = config.CRAWLER_MAX_NOTES_COUNT
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue
            source_keyword_var.set(keyword)
            self.response_client.clear(SEARCH_API)
            search_url = f"{self.index_url}/search?q={quote(keyword)}"
            await self.context_page.goto(search_url, wait_until="domcontentloaded")
            await self._wait_for_responses()

            seen_item_ids = set()
            search_items: List[GoofishItem] = []
            while len(search_items) < target_count:
                page_seen_count = len(seen_item_ids)
                no_new_scroll_count = 0
                for _ in range(config.GOOFISH_SEARCH_MAX_SCROLL_TIMES + 1):
                    new_items = self._extract_captured_search_items(seen_item_ids, target_count)
                    search_items.extend(new_items)
                    if len(search_items) >= target_count:
                        break

                    before_count = len(seen_item_ids)
                    await self.context_page.keyboard.press("End")
                    await self._wait_for_responses()
                    if len(seen_item_ids) == before_count:
                        no_new_scroll_count += 1
                        if no_new_scroll_count >= 3:
                            break
                    else:
                        no_new_scroll_count = 0
                    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

                if len(search_items) >= target_count:
                    break
                if len(seen_item_ids) == page_seen_count:
                    break
                self.response_client.clear(SEARCH_API)
                if not await self._click_next_search_page():
                    break
                await self._wait_for_responses()

            for item in search_items[:target_count]:
                await self.get_item_detail(item)

    async def _click_next_search_page(self) -> bool:
        selectors = [
            "button:has([class*='search-page-tiny-arrow-right'])",
            "button:has-text('下一页')",
            "a:has-text('下一页')",
            "[aria-label*='下一页']",
            "[aria-label*='Next']",
            "button:has-text('>')",
            "a:has-text('>')",
            "[class*='next']",
        ]
        for selector in selectors:
            try:
                locator = self.context_page.locator(selector)
                count = await locator.count()
            except Exception:
                continue

            for index in range(count):
                candidate = locator.nth(index)
                try:
                    if not await candidate.is_visible():
                        continue
                    disabled = await candidate.get_attribute("disabled")
                    aria_disabled = await candidate.get_attribute("aria-disabled")
                    class_name = (await candidate.get_attribute("class")) or ""
                    if disabled is not None or aria_disabled == "true" or "disabled" in class_name:
                        continue
                    if not await candidate.is_enabled():
                        continue

                    await candidate.click(timeout=5000)
                    try:
                        await self.context_page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    utils.logger.info("[GoofishCrawler.search] Clicked next search results page")
                    return True
                except Exception:
                    continue

        utils.logger.info("[GoofishCrawler.search] No next search results page found")
        return False

    def _extract_captured_search_items(self, seen_item_ids: set, target_count: int) -> List[GoofishItem]:
        new_items: List[GoofishItem] = []
        for payload in self.response_client.get_payloads(SEARCH_API):
            for item in GoofishExtractor.extract_search_items(payload):
                if item.item_id in seen_item_ids:
                    continue
                seen_item_ids.add(item.item_id)
                new_items.append(item)
                if len(seen_item_ids) >= target_count:
                    return new_items
        return new_items

    async def get_specified_items(self, item_id_list: Optional[List[str]] = None) -> None:
        item_id_list = item_id_list or config.GOOFISH_SPECIFIED_ID_LIST
        for item_id in item_id_list:
            await self.get_item_detail(GoofishItem(item_id=item_id, item_url=GoofishExtractor.item_url(item_id)))

    async def get_item_detail(self, search_item: GoofishItem) -> None:
        self.response_client.clear(DETAIL_API)
        await self.context_page.goto(search_item.item_url or GoofishExtractor.item_url(search_item.item_id), wait_until="domcontentloaded")
        await self._wait_for_responses()
        for _ in range(config.GOOFISH_COMMENT_MAX_SCROLL_TIMES if config.ENABLE_GET_COMMENTS else 0):
            await self.context_page.keyboard.press("End")
            await self._wait_for_responses()

        detail_payloads = self.response_client.get_payloads(DETAIL_API)
        if detail_payloads:
            detail = GoofishExtractor.extract_detail(detail_payloads[-1], fallback_item_id=search_item.item_id)
            item = detail.item
            comments = detail.comments
        else:
            utils.logger.warning(f"[GoofishCrawler.get_item_detail] Detail mtop response not captured for item: {search_item.item_id}")
            item = search_item
            comments = []

        await goofish_store.update_goofish_item(item)
        if config.ENABLE_GET_COMMENTS:
            if comments:
                await goofish_store.batch_update_goofish_comments(
                    item.item_id,
                    comments[: config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES],
                )
            elif not self._warned_comments_unavailable:
                utils.logger.info(
                    "[GoofishCrawler] No public Goofish comments/QA response was exposed on the PC detail page; comments will be skipped"
                )
                self._warned_comments_unavailable = True

    async def get_creators_and_items(self) -> None:
        for user_id in config.GOOFISH_CREATOR_ID_LIST:
            creator = GoofishCreator(
                user_id=user_id,
                seller_homepage_url=GoofishExtractor.seller_homepage_url(user_id),
            )
            self.response_client.clear(RECOMMEND_API)
            await self.context_page.goto(creator.seller_homepage_url, wait_until="domcontentloaded")
            await self._wait_for_responses()
            captured_payloads = [
                payload
                for payloads in self.response_client.payloads.values()
                for payload in payloads
            ]
            for payload in reversed(captured_payloads):
                extracted_creator = GoofishExtractor.extract_creator(
                    payload,
                    fallback_user_id=user_id,
                )
                if extracted_creator.nickname or extracted_creator.avatar:
                    creator = extracted_creator
                    break
            await goofish_store.save_creator(creator)

            seen_item_ids = set()
            items: List[GoofishItem] = []
            for payload in captured_payloads:
                for item in GoofishExtractor.extract_search_items(payload):
                    if item.item_id in seen_item_ids:
                        continue
                    seen_item_ids.add(item.item_id)
                    items.append(item)
            for item in items[: config.CRAWLER_MAX_NOTES_COUNT]:
                await self.get_item_detail(item)

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                channel="chrome",
            )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy, channel="chrome")
        return await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        self.cdp_manager = CDPBrowserManager()
        return await self.cdp_manager.launch_and_connect(
            playwright=playwright,
            playwright_proxy=playwright_proxy,
            user_agent=user_agent,
            headless=False,
        )
