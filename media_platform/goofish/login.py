# -*- coding: utf-8 -*-

from playwright.async_api import BrowserContext, Page

from base.base_crawler import AbstractLogin
from tools import utils


class GoofishLogin(AbstractLogin):
    def __init__(
        self,
        login_type: str,
        browser_context: BrowserContext,
        context_page: Page,
        cookie_str: str = "",
    ):
        self.login_type = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.cookie_str = cookie_str

    async def begin(self):
        if self.login_type == "cookie":
            await self.login_by_cookies()
            return
        utils.logger.info(
            "[GoofishLogin.begin] Goofish uses the real Chrome/CDP session. "
            "Please complete login manually in the opened browser if the page asks for it."
        )

    async def login_by_qrcode(self):
        await self.begin()

    async def login_by_mobile(self):
        await self.begin()

    async def login_by_cookies(self):
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies(
                [
                    {"name": key, "value": value, "domain": ".goofish.com", "path": "/"},
                    {"name": key, "value": value, "domain": ".taobao.com", "path": "/"},
                ]
            )
