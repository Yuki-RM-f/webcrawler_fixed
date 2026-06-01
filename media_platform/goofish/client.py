# -*- coding: utf-8 -*-

import json
import re
from collections import defaultdict
from typing import Any, Dict, List
from urllib.parse import parse_qs, unquote, urlparse

from playwright.async_api import Response

from tools import utils


SEARCH_API = "mtop.taobao.idlemtopsearch.pc.search"
DETAIL_API = "mtop.taobao.idle.pc.detail"
RECOMMEND_API = "mtop.taobao.idle.item.web.recommend.list"


class GoofishResponseClient:
    def __init__(self) -> None:
        self.payloads: Dict[str, List[Dict]] = defaultdict(list)

    def clear(self, *api_names: str) -> None:
        if not api_names:
            self.payloads.clear()
            return
        for api_name in api_names:
            self.payloads.pop(api_name, None)

    def get_payloads(self, api_name: str) -> List[Dict]:
        return list(self.payloads.get(api_name, []))

    async def capture_response(self, response: Response) -> None:
        api_name = self._api_name_from_url(response.url)
        if not api_name:
            return
        try:
            text = await response.text()
            payload = self._parse_payload(text)
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        self.payloads[api_name].append(payload)
        utils.logger.info(f"[GoofishResponseClient] Captured Goofish mtop response: {api_name}")

    @staticmethod
    def _api_name_from_url(url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        api_name = query.get("api", [""])[0].lower()
        if api_name:
            return api_name

        lowered_url = unquote(url).lower()
        for name in (SEARCH_API, DETAIL_API, RECOMMEND_API):
            if name in lowered_url:
                return name
        return ""

    @staticmethod
    def _parse_payload(text: str) -> Any:
        text = text.strip()
        if not text:
            return {}
        if text.startswith("{"):
            return json.loads(text)
        match = re.search(r"^[\w.$]+\((.*)\)\s*;?$", text, re.S)
        if match:
            return json.loads(match.group(1))
        return {}
