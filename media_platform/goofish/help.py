# -*- coding: utf-8 -*-

import json
import re
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

from model.m_goofish import GoofishComment, GoofishCreator, GoofishDetail, GoofishItem

GOOFISH_URL = "https://www.goofish.com"


class GoofishExtractor:
    @classmethod
    def extract_search_items(cls, payload: Dict) -> List[GoofishItem]:
        items: List[GoofishItem] = []
        seen = set()
        for node in cls._iter_dicts(payload):
            item = cls._item_from_node(node)
            if not item or item.item_id in seen:
                continue
            seen.add(item.item_id)
            items.append(item)
        return items

    @classmethod
    def extract_detail(cls, payload: Dict, fallback_item_id: str = "") -> GoofishDetail:
        data = payload.get("data") if isinstance(payload, dict) else {}
        data = data if isinstance(data, dict) else {}
        item_node = cls._first_dict(
            data.get("item"),
            data.get("itemInfo"),
            data.get("itemDO"),
            data.get("detail"),
            data,
        )
        seller_node = cls._first_dict(
            data.get("seller"),
            data.get("sellerInfo"),
            item_node.get("seller") if item_node else None,
            item_node.get("sellerInfo") if item_node else None,
        )
        item = cls._item_from_node(item_node or data, seller_node=seller_node, fallback_item_id=fallback_item_id)
        if not item:
            item = GoofishItem(item_id=fallback_item_id, item_url=cls.item_url(fallback_item_id))
        comments = cls.extract_comments(payload, item.item_id)
        return GoofishDetail(item=item, comments=comments)

    @classmethod
    def extract_comments(cls, payload: Dict, item_id: str) -> List[GoofishComment]:
        comments: List[GoofishComment] = []
        seen = set()
        for comment_node in cls._iter_comment_nodes(payload):
            comment = cls._comment_from_node(comment_node, item_id)
            if not comment or comment.comment_id in seen:
                continue
            seen.add(comment.comment_id)
            comments.append(comment)
        return comments

    @classmethod
    def extract_creator(cls, payload: Dict, fallback_user_id: str = "") -> GoofishCreator:
        data = payload.get("data") if isinstance(payload, dict) else {}
        data = data if isinstance(data, dict) else {}
        creator_node = cls._first_dict(data.get("seller"), data.get("sellerInfo"), data.get("user"), data)
        if not creator_node:
            creator_node = {}

        user_id = cls._string(
            cls._first_value(
                creator_node,
                "user_id",
                "userId",
                "sellerId",
                "id",
                "userIdStr",
            )
        ) or fallback_user_id
        return GoofishCreator(
            user_id=user_id,
            nickname=cls._string(cls._first_value(creator_node, "nickname", "nick", "userNick", "userName", "name")),
            avatar=cls._string(cls._first_value(creator_node, "avatar", "avatarUrl", "headImg", "userAvatar")),
            seller_homepage_url=cls.seller_homepage_url(user_id),
            desc=cls._string(cls._first_value(creator_node, "desc", "description", "signature", "introduction")),
            location=cls._string(cls._first_value(creator_node, "location", "area", "city")),
            fans_count=cls._string(cls._first_value(creator_node, "fans_count", "fansCount", "fans", "fanCount")),
            follows_count=cls._string(cls._first_value(creator_node, "follows_count", "followsCount", "follows")),
            credit_level=cls._string(cls._first_value(creator_node, "credit_level", "creditLevel", "credit", "level")),
        )

    @staticmethod
    def item_url(item_id: str, category_id: str = "") -> str:
        if not item_id:
            return GOOFISH_URL
        url = f"{GOOFISH_URL}/item?id={item_id}"
        if category_id:
            url = f"{url}&categoryId={category_id}"
        return url

    @staticmethod
    def seller_homepage_url(user_id: str) -> str:
        if not user_id:
            return ""
        bfp = quote(json.dumps({"userId": str(user_id)}, ensure_ascii=False, separators=(",", ":")))
        return (
            "https://pages.goofish.com/sharexy?loadingVisible=false&bft=personal"
            f"&bfs=idlepc&bfp={bfp}"
        )

    @classmethod
    def _item_from_node(
        cls,
        node: Optional[Dict],
        *,
        seller_node: Optional[Dict] = None,
        fallback_item_id: str = "",
    ) -> Optional[GoofishItem]:
        if not isinstance(node, dict):
            return None

        item_id = cls._string(cls._first_value(node, "item_id", "itemId", "itemid", "itemID", "id")) or fallback_item_id
        title = cls._string(cls._first_value(node, "title", "itemTitle", "name", "subject", "shortTitle"))
        desc = cls._string(cls._first_value(node, "desc", "description", "content", "detail", "subtitle"))
        price = cls._extract_price(node)
        image_list = ",".join(cls._extract_item_images(node))
        if not item_id or not any([title, desc, price, image_list]):
            return None

        seller = seller_node or cls._first_dict(node.get("sellerInfo"), node.get("seller"), node.get("user"), node.get("owner")) or {}
        seller_id = cls._string(cls._first_value(seller, "user_id", "userId", "sellerId", "id", "ownerId"))
        category_id = cls._string(cls._first_value(node, "category_id", "categoryId", "cateId", "catId"))
        item_url = cls._string(cls._first_value(node, "item_url", "itemUrl", "detailUrl", "url")) or cls.item_url(item_id, category_id)

        return GoofishItem(
            item_id=item_id,
            item_url=item_url,
            category_id=category_id,
            title=title,
            desc=desc,
            price=price,
            location=cls._string(cls._first_value(node, "location", "area", "city", "ipLocation")),
            publish_time=cls._string(cls._first_value(node, "publish_time", "publishTime", "createTime", "createdAt", "gmtCreate")),
            seller_id=seller_id,
            seller_nickname=cls._string(cls._first_value(seller, "seller_nickname", "nickname", "nick", "userNick", "userName", "name")),
            seller_avatar=cls._string(cls._first_value(seller, "seller_avatar", "avatar", "avatarUrl", "headImg", "userAvatar")),
            seller_homepage_url=cls.seller_homepage_url(seller_id),
            image_list=image_list,
        )

    @classmethod
    def _comment_from_node(cls, node: Dict, item_id: str) -> Optional[GoofishComment]:
        comment_id = cls._string(cls._first_value(node, "comment_id", "commentId", "commentID", "replyId", "id"))
        content = cls._string(cls._first_value(node, "content", "text", "comment", "question", "answer", "message"))
        if not comment_id or not content:
            return None

        user = cls._first_dict(node.get("user"), node.get("userInfo"), node.get("buyer"), node.get("sender")) or {}
        return GoofishComment(
            comment_id=comment_id,
            item_id=item_id,
            parent_comment_id=cls._string(cls._first_value(node, "parent_comment_id", "parentCommentId", "parentId")),
            content=content,
            publish_time=cls._string(cls._first_value(node, "publish_time", "publishTime", "createTime", "createdAt", "gmtCreate")),
            user_id=cls._string(cls._first_value(user, "user_id", "userId", "id")),
            nickname=cls._string(cls._first_value(user, "nickname", "nick", "userNick", "userName", "name")),
            avatar=cls._string(cls._first_value(user, "avatar", "avatarUrl", "headImg", "userAvatar")),
            pictures=",".join(cls._extract_urls_from_value(cls._first_value(node, "pictures", "imageList", "imageInfos", "images"))),
            like_count=cls._string(cls._first_value(node, "like_count", "likeCount", "likedCount")) or "0",
        )

    @classmethod
    def _iter_comment_nodes(cls, payload: Any) -> Iterable[Dict]:
        comment_key_pattern = re.compile(r"(comment|reply|question|answer|message|qa|留言|问答)", re.I)
        for node in cls._iter_dicts(payload):
            for key, value in node.items():
                if not comment_key_pattern.search(str(key)):
                    continue
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            yield item
                elif isinstance(value, dict):
                    yield value

    @classmethod
    def _iter_dicts(cls, node: Any) -> Iterable[Dict]:
        if isinstance(node, dict):
            yield node
            for value in node.values():
                yield from cls._iter_dicts(value)
        elif isinstance(node, list):
            for value in node:
                yield from cls._iter_dicts(value)

    @staticmethod
    def _first_dict(*values: Any) -> Optional[Dict]:
        for value in values:
            if isinstance(value, dict):
                return value
        return None

    @staticmethod
    def _first_value(node: Dict, *keys: str) -> Any:
        for key in keys:
            value = node.get(key)
            if value not in (None, "", []):
                return value
        return ""

    @classmethod
    def _extract_price(cls, node: Dict) -> str:
        raw_price = cls._first_value(node, "price", "itemPrice", "soldPrice", "priceText")
        if raw_price:
            return cls._string(raw_price)
        price_info = cls._first_dict(node.get("priceInfo"), node.get("price_info")) or {}
        return cls._string(cls._first_value(price_info, "price", "priceText", "priceDesc", "text", "value"))

    @classmethod
    def _extract_item_images(cls, node: Dict) -> List[str]:
        urls: List[str] = []
        for key in (
            "image_list",
            "imageList",
            "imageInfos",
            "images",
            "picInfo",
            "mainPic",
            "mainPicUrl",
            "picUrl",
            "cover",
        ):
            urls.extend(cls._extract_urls_from_value(node.get(key)))
        return cls._dedupe(urls)

    @classmethod
    def _extract_urls_from_value(cls, value: Any) -> List[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            return [value] if value.startswith(("http://", "https://", "//")) else []
        if isinstance(value, list):
            urls: List[str] = []
            for item in value:
                urls.extend(cls._extract_urls_from_value(item))
            return cls._dedupe(urls)
        if isinstance(value, dict):
            urls: List[str] = []
            for key in ("url", "src", "picUrl", "imageUrl", "mainPicUrl", "originUrl", "file_url"):
                urls.extend(cls._extract_urls_from_value(value.get(key)))
            return cls._dedupe(urls)
        return []

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            normalized = value.strip()
            if normalized.startswith("//"):
                normalized = f"https:{normalized}"
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    @staticmethod
    def _string(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
