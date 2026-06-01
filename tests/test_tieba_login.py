# -*- coding: utf-8 -*-

import pytest

from media_platform.tieba.login import BaiduTieBaLogin


class DummyPage:
    def __init__(self):
        self.visited_urls = []

    async def goto(self, url, wait_until=None):
        self.visited_urls.append((url, wait_until))

    def locator(self, selector):
        raise AssertionError(f"legacy login selector should not be used: {selector}")


@pytest.mark.asyncio
async def test_tieba_qrcode_login_falls_back_to_passport(monkeypatch):
    page = DummyPage()
    qrcode_calls = []

    async def fake_find_login_qrcode(context_page, selector):
        qrcode_calls.append((list(page.visited_urls), selector))
        return "base64-qrcode" if page.visited_urls else ""

    async def fake_check_login_state():
        return True

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(
        "media_platform.tieba.login.utils.find_login_qrcode",
        fake_find_login_qrcode,
    )
    monkeypatch.setattr("media_platform.tieba.login.utils.show_qrcode", lambda _: None)
    monkeypatch.setattr("media_platform.tieba.login.asyncio.sleep", fake_sleep)

    login = BaiduTieBaLogin(
        login_type="qrcode",
        browser_context=object(),
        context_page=page,
    )
    monkeypatch.setattr(login, "check_login_state", fake_check_login_state)

    await login.login_by_qrcode()

    assert page.visited_urls == [
        (
            "https://passport.baidu.com/v2/?login&tpl=tb&u=https%3A%2F%2Ftieba.baidu.com%2F",
            "domcontentloaded",
        )
    ]
    assert qrcode_calls[-1][1] == "xpath=//img[@class='tang-pass-qrcode-img']"
