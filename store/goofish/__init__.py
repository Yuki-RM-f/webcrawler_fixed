# -*- coding: utf-8 -*-

from typing import List

import config
from model.m_goofish import GoofishComment, GoofishCreator, GoofishItem
from tools import utils
from var import source_keyword_var

from ._store_impl import *


class GoofishStoreFactory:
    STORES = {
        "csv": GoofishCsvStoreImplement,
        "db": GoofishDbStoreImplement,
        "postgres": GoofishDbStoreImplement,
        "json": GoofishJsonStoreImplement,
        "jsonl": GoofishJsonlStoreImplement,
        "sqlite": GoofishSqliteStoreImplement,
        "mongodb": GoofishMongoStoreImplement,
        "excel": GoofishExcelStoreImplement,
    }

    @staticmethod
    def create_store() -> AbstractStore:
        store_class = GoofishStoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError("[GoofishStoreFactory.create_store] Invalid save option")
        return store_class()


async def update_goofish_item(item: GoofishItem):
    item.source_keyword = item.source_keyword or source_keyword_var.get()
    save_item = item.model_dump()
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.goofish.update_goofish_item] goofish item:{save_item}")
    await GoofishStoreFactory.create_store().store_content(save_item)


async def batch_update_goofish_comments(item_id: str, comments: List[GoofishComment]):
    if not comments:
        return
    for comment in comments:
        await update_goofish_comment(item_id, comment)


async def update_goofish_comment(item_id: str, comment: GoofishComment):
    save_item = comment.model_dump()
    save_item["item_id"] = item_id
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.goofish.update_goofish_comment] goofish item id:{item_id} comment:{save_item}")
    await GoofishStoreFactory.create_store().store_comment(save_item)


async def save_creator(creator: GoofishCreator):
    save_item = creator.model_dump()
    save_item["last_modify_ts"] = utils.get_current_timestamp()
    utils.logger.info(f"[store.goofish.save_creator] creator:{save_item}")
    await GoofishStoreFactory.create_store().store_creator(save_item)
