# -*- coding: utf-8 -*-

from typing import Dict

import config
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class XStoreFactory:
    STORES = {
        "csv": XCsvStoreImplement,
        "json": XJsonStoreImplement,
        "jsonl": XJsonlStoreImplement,
        "excel": XExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = XStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                "[XStoreFactory.create_store] Invalid save option for X v1. "
                "Supported: csv, json, jsonl, excel"
            )
        return store_class()


async def update_x_note(note_item: Dict):
    if not note_item or not note_item.get("tweet_id"):
        return

    local_db_item = {
        "tweet_id": note_item.get("tweet_id", ""),
        "tweet_url": note_item.get("tweet_url", ""),
        "content": note_item.get("content", ""),
        "created_at": note_item.get("created_at", ""),
        "create_time": note_item.get("create_time", 0),
        "user_id": note_item.get("user_id", ""),
        "username": note_item.get("username", ""),
        "nickname": note_item.get("nickname", ""),
        "avatar": note_item.get("avatar", ""),
        "reply_count": note_item.get("reply_count", "0"),
        "retweet_count": note_item.get("retweet_count", "0"),
        "like_count": note_item.get("like_count", "0"),
        "quote_count": note_item.get("quote_count", "0"),
        "view_count": note_item.get("view_count", "0"),
        "image_list": note_item.get("image_list", ""),
        "source_keyword": note_item.get("source_keyword") or source_keyword_var.get(),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(
        f"[store.x.update_x_note] x tweet id:{local_db_item['tweet_id']}, "
        f"content:{local_db_item['content'][:24]} ..."
    )
    await XStoreFactory.create_store().store_content(local_db_item)


async def update_x_note_comment(tweet_id: str, comment_item: Dict, source_keyword: str = ""):
    if not comment_item or not comment_item.get("tweet_id"):
        return

    local_db_item = {
        "comment_id": comment_item.get("tweet_id", ""),
        "tweet_id": tweet_id,
        "parent_comment_id": comment_item.get("in_reply_to_status_id_str") or tweet_id,
        "comment_url": comment_item.get("tweet_url", ""),
        "content": comment_item.get("content", ""),
        "created_at": comment_item.get("created_at", ""),
        "create_time": comment_item.get("create_time", 0),
        "user_id": comment_item.get("user_id", ""),
        "username": comment_item.get("username", ""),
        "nickname": comment_item.get("nickname", ""),
        "avatar": comment_item.get("avatar", ""),
        "reply_count": comment_item.get("reply_count", "0"),
        "retweet_count": comment_item.get("retweet_count", "0"),
        "like_count": comment_item.get("like_count", "0"),
        "quote_count": comment_item.get("quote_count", "0"),
        "view_count": comment_item.get("view_count", "0"),
        "pictures": comment_item.get("pictures") or comment_item.get("image_list", ""),
        "source_keyword": source_keyword or comment_item.get("source_keyword") or source_keyword_var.get(),
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(
        f"[store.x.update_x_note_comment] x comment id:{local_db_item['comment_id']}, "
        f"tweet id:{local_db_item['tweet_id']}, content:{local_db_item['content'][:24]} ..."
    )
    await XStoreFactory.create_store().store_comment(local_db_item)
