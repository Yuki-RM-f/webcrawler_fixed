# -*- coding: utf-8 -*-

import asyncio
import os
from typing import Dict, List, Optional
from urllib.parse import quote

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    Response,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import x as x_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from var import crawler_type_var, source_keyword_var

from .help import extract_tweets_from_graphql


class XBrowserCrawler(AbstractCrawler):
    context_page: Page
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://x.com"
        self.cookie_urls = [self.index_url]
        self.user_agent = utils.get_user_agent()
        self.cdp_manager = None
        self.ip_proxy_pool = None
        self.context_page = None
        self._captured_tweets: Dict[str, Dict] = {}
        self._captured_comments: Dict[str, Dict] = {}
        self._response_tasks: List[asyncio.Task] = []
        self._response_capture_mode = "search"
        self._active_comment_tweet_id: Optional[str] = None
        self._saved_comment_ids = set()
        self._warned_sub_comments = False

    async def start(self) -> None:
        playwright_proxy_format = None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(
                config.IP_PROXY_POOL_COUNT, enable_validate_ip=True
            )
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, _ = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[XBrowserCrawler] Launching browser with CDP mode")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[XBrowserCrawler] Launching browser with standard mode")
                self.browser_context = await self.launch_browser(
                    playwright.chromium,
                    playwright_proxy_format,
                    self.user_agent,
                    headless=config.HEADLESS,
                )
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self._ensure_login()
            self._bind_response_listener()

            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE in ("detail", "creator"):
                utils.logger.warning(
                    f"[XBrowserCrawler.start] X {config.CRAWLER_TYPE} mode is not supported in v1"
                )

            await self._drain_response_tasks()
            utils.logger.info("[XBrowserCrawler.start] X Crawler finished ...")

    async def _ensure_login(self) -> None:
        if await self._has_auth_cookie():
            return

        utils.logger.info(
            "[XBrowserCrawler] X auth cookie not found. Opening login page for manual login ..."
        )
        await self.context_page.goto(f"{self.index_url}/login", wait_until="domcontentloaded")
        for _ in range(config.X_LOGIN_WAIT_SECONDS):
            if await self._has_auth_cookie():
                utils.logger.info("[XBrowserCrawler] X login detected")
                return
            await asyncio.sleep(1)

        utils.logger.warning(
            "[XBrowserCrawler] X login was not detected before timeout; continuing and relying on page responses"
        )

    async def _has_auth_cookie(self) -> bool:
        cookies = await self.browser_context.cookies(self.cookie_urls)
        return any(cookie.get("name") == "auth_token" for cookie in cookies)

    def _bind_response_listener(self) -> None:
        self.context_page.on(
            "response",
            lambda response: self._response_tasks.append(
                asyncio.create_task(self._handle_response(response))
            ),
        )

    @staticmethod
    def _is_search_graphql_response(url: str) -> bool:
        return "x.com/i/api/graphql" in url and (
            "SearchTimeline" in url
            or "search" in url.lower()
            or "Search" in url
        )

    async def _handle_response(self, response: Response) -> None:
        url = response.url
        if not self._is_search_graphql_response(url):
            return
        try:
            payload = await response.json()
        except Exception:
            return
        tweets = extract_tweets_from_graphql(payload)
        if self._response_capture_mode == "comments" and self._active_comment_tweet_id:
            self._capture_comments(tweets, self._active_comment_tweet_id)
        else:
            self._capture_tweets(tweets)

    def _capture_tweets(self, tweets: List[Dict]) -> int:
        new_count = 0
        for tweet in tweets:
            tweet_id = tweet.get("tweet_id")
            if not tweet_id or tweet_id in self._captured_tweets:
                continue
            self._captured_tweets[tweet_id] = tweet
            new_count += 1
        return new_count

    def _capture_comments(self, tweets: List[Dict], parent_tweet_id: str) -> int:
        new_count = 0
        for tweet in tweets:
            if not self._is_first_level_reply(tweet, parent_tweet_id):
                continue
            comment_id = tweet.get("tweet_id")
            if not comment_id or comment_id in self._captured_comments:
                continue
            self._captured_comments[comment_id] = tweet
            new_count += 1
        return new_count

    @staticmethod
    def _is_first_level_reply(tweet: Dict, parent_tweet_id: str) -> bool:
        tweet_id = str(tweet.get("tweet_id") or "")
        if not tweet_id or tweet_id == parent_tweet_id:
            return False

        reply_to_tweet_id = str(tweet.get("in_reply_to_status_id_str") or "")
        if reply_to_tweet_id != parent_tweet_id:
            return False

        conversation_id = str(tweet.get("conversation_id_str") or "")
        return not conversation_id or conversation_id == parent_tweet_id

    async def _drain_response_tasks(self) -> None:
        if not self._response_tasks:
            return
        tasks = self._response_tasks
        self._response_tasks = []
        await asyncio.gather(*tasks, return_exceptions=True)

    async def search(self) -> None:
        utils.logger.info("[XBrowserCrawler.search] Begin search X keywords")
        target_count = config.CRAWLER_MAX_NOTES_COUNT
        self._saved_comment_ids = set()
        for keyword in config.KEYWORDS.split(","):
            keyword = keyword.strip()
            if not keyword:
                continue

            source_keyword_var.set(keyword)
            self._response_capture_mode = "search"
            self._captured_tweets = {}
            keyword_saved_tweets: List[Dict] = []
            saved_tweet_ids = set()
            no_new_scroll_count = 0
            search_url = (
                f"{self.index_url}/search?q={quote(keyword)}"
                f"&src=typed_query&f={config.X_SEARCH_FILTER}"
            )
            utils.logger.info(f"[XBrowserCrawler.search] Search X keyword: {keyword}")
            await self.context_page.goto(search_url, wait_until="domcontentloaded")
            await self._wait_for_x_response_window()

            for _ in range(config.X_SEARCH_MAX_SCROLL_TIMES + 1):
                keyword_saved_tweets.extend(
                    await self._save_new_tweets(saved_tweet_ids, target_count, keyword)
                )
                if len(saved_tweet_ids) >= target_count:
                    break

                before_count = len(self._captured_tweets)
                await self.context_page.keyboard.press("End")
                await self.context_page.wait_for_timeout(config.X_SEARCH_SCROLL_WAIT_MS)
                await self._drain_response_tasks()

                if len(self._captured_tweets) == before_count:
                    no_new_scroll_count += 1
                    if no_new_scroll_count >= 3:
                        utils.logger.info(
                            "[XBrowserCrawler.search] Stop search because consecutive scrolls have no new tweets"
                        )
                        break
                else:
                    no_new_scroll_count = 0

                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            keyword_saved_tweets.extend(
                await self._save_new_tweets(saved_tweet_ids, target_count, keyword)
            )
            await self._get_comments_for_tweets(keyword_saved_tweets, keyword)

    async def _wait_for_x_response_window(self) -> None:
        await self.context_page.wait_for_timeout(config.X_SEARCH_SCROLL_WAIT_MS)
        await self._drain_response_tasks()

    async def _save_new_tweets(
        self,
        saved_tweet_ids: set,
        target_count: int,
        keyword: str,
    ) -> List[Dict]:
        new_tweets: List[Dict] = []
        for tweet in list(self._captured_tweets.values()):
            tweet_id = tweet.get("tweet_id")
            if not tweet_id or tweet_id in saved_tweet_ids:
                continue
            if len(saved_tweet_ids) >= target_count:
                break
            tweet["source_keyword"] = keyword
            await x_store.update_x_note(tweet)
            saved_tweet_ids.add(tweet_id)
            new_tweets.append(tweet)
        return new_tweets

    async def _get_comments_for_tweets(self, tweets: List[Dict], keyword: str) -> None:
        if not config.ENABLE_GET_COMMENTS:
            return

        if config.ENABLE_GET_SUB_COMMENTS and not self._warned_sub_comments:
            utils.logger.warning(
                "[XBrowserCrawler.search] X sub comments are not supported; only one-level replies will be saved"
            )
            self._warned_sub_comments = True

        for tweet in tweets:
            await self.get_tweet_comments(tweet, keyword)

    async def get_tweet_comments(self, tweet: Dict, keyword: str) -> None:
        parent_tweet_id = str(tweet.get("tweet_id") or "")
        if not parent_tweet_id:
            return

        utils.logger.info(
            f"[XBrowserCrawler.get_tweet_comments] Begin get replies for tweet: {parent_tweet_id}"
        )
        self._captured_comments = {}
        saved_count = 0
        no_new_scroll_count = 0
        previous_mode = self._response_capture_mode
        previous_parent_tweet_id = self._active_comment_tweet_id
        self._response_capture_mode = "comments"
        self._active_comment_tweet_id = parent_tweet_id

        try:
            query = f"conversation_id:{parent_tweet_id}"
            comment_search_url = (
                f"{self.index_url}/search?q={quote(query)}"
                f"&src=typed_query&f={config.X_SEARCH_FILTER}"
            )
            await self.context_page.goto(comment_search_url, wait_until="domcontentloaded")
            await self._wait_for_x_comment_response_window()

            for _ in range(config.X_COMMENT_SEARCH_MAX_SCROLL_TIMES + 1):
                saved_count += await self._save_new_comments(
                    parent_tweet_id, saved_count, keyword
                )
                if saved_count >= config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES:
                    break

                before_count = len(self._captured_comments)
                await self.context_page.keyboard.press("End")
                await self.context_page.wait_for_timeout(config.X_COMMENT_SCROLL_WAIT_MS)
                await self._drain_response_tasks()

                if len(self._captured_comments) == before_count:
                    no_new_scroll_count += 1
                    if no_new_scroll_count >= 3:
                        utils.logger.info(
                            "[XBrowserCrawler.get_tweet_comments] Stop replies because consecutive scrolls have no new comments"
                        )
                        break
                else:
                    no_new_scroll_count = 0

                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)

            saved_count += await self._save_new_comments(parent_tweet_id, saved_count, keyword)
        finally:
            await self._drain_response_tasks()
            self._response_capture_mode = previous_mode
            self._active_comment_tweet_id = previous_parent_tweet_id

    async def _wait_for_x_comment_response_window(self) -> None:
        await self.context_page.wait_for_timeout(config.X_COMMENT_SCROLL_WAIT_MS)
        await self._drain_response_tasks()

    async def _save_new_comments(
        self,
        parent_tweet_id: str,
        saved_count: int,
        keyword: str,
    ) -> int:
        new_saved_count = 0
        target_count = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES
        for comment in list(self._captured_comments.values()):
            comment_id = comment.get("tweet_id")
            if not comment_id or comment_id in self._saved_comment_ids:
                continue
            if saved_count + new_saved_count >= target_count:
                break
            comment["source_keyword"] = keyword
            await x_store.update_x_note_comment(parent_tweet_id, comment, keyword)
            self._saved_comment_ids.add(comment_id)
            new_saved_count += 1
        return new_saved_count

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        utils.logger.info("[XBrowserCrawler.launch_browser] Begin create browser context ...")
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM
            )
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
                channel="chrome",
            )

        browser = await chromium.launch(
            headless=headless, proxy=playwright_proxy, channel="chrome"
        )
        return await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent,
        )

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[XBrowserCrawler] CDP browser info: {browser_info}")
            return browser_context
        except Exception as e:
            utils.logger.error(
                f"[XBrowserCrawler] CDP mode launch failed, falling back to standard mode: {e}"
            )
            return await self.launch_browser(
                playwright.chromium, playwright_proxy, user_agent, headless
            )

    async def close(self):
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[XBrowserCrawler.close] Browser context closed ...")
