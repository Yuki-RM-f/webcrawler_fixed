# -*- coding: utf-8 -*-

from typing import Dict

from sqlalchemy import select

import config
from base.base_crawler import AbstractStore
from database.db_session import get_session
from database.models import GoofishComment, GoofishCreator, GoofishItem
from database.mongodb_store_base import MongoDBStoreBase
from tools import utils
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


def _filter_model_columns(model, item: Dict) -> Dict:
    columns = {column.name for column in model.__table__.columns}
    return {key: value for key, value in item.items() if key in columns}


class GoofishCsvStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_csv(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        await self.writer.write_to_csv(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        await self.writer.write_to_csv(item_type="creators", item=creator)


class GoofishJsonStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_single_item_to_json(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        await self.writer.write_single_item_to_json(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        await self.writer.write_single_item_to_json(item_type="creators", item=creator)


class GoofishJsonlStoreImplement(AbstractStore):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.writer = AsyncFileWriter(platform="goofish", crawler_type=crawler_type_var.get())

    async def store_content(self, content_item: Dict):
        await self.writer.write_to_jsonl(item_type="contents", item=content_item)

    async def store_comment(self, comment_item: Dict):
        await self.writer.write_to_jsonl(item_type="comments", item=comment_item)

    async def store_creator(self, creator: Dict):
        await self.writer.write_to_jsonl(item_type="creators", item=creator)


class GoofishDbStoreImplement(AbstractStore):
    async def store_content(self, content_item: Dict):
        item_id = content_item.get("item_id")
        content_item = _filter_model_columns(GoofishItem, content_item)
        async with get_session() as session:
            stmt = select(GoofishItem).where(GoofishItem.item_id == item_id)
            res = await session.execute(stmt)
            db_item = res.scalar_one_or_none()
            if db_item:
                for key, value in content_item.items():
                    setattr(db_item, key, value)
            else:
                session.add(GoofishItem(**content_item))
            await session.commit()

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        comment_item = _filter_model_columns(GoofishComment, comment_item)
        async with get_session() as session:
            stmt = select(GoofishComment).where(GoofishComment.comment_id == comment_id)
            res = await session.execute(stmt)
            db_item = res.scalar_one_or_none()
            if db_item:
                for key, value in comment_item.items():
                    setattr(db_item, key, value)
            else:
                session.add(GoofishComment(**comment_item))
            await session.commit()

    async def store_creator(self, creator: Dict):
        user_id = creator.get("user_id")
        creator = _filter_model_columns(GoofishCreator, creator)
        async with get_session() as session:
            stmt = select(GoofishCreator).where(GoofishCreator.user_id == user_id)
            res = await session.execute(stmt)
            db_item = res.scalar_one_or_none()
            if db_item:
                for key, value in creator.items():
                    setattr(db_item, key, value)
            else:
                session.add(GoofishCreator(**creator))
            await session.commit()


class GoofishSqliteStoreImplement(GoofishDbStoreImplement):
    pass


class GoofishMongoStoreImplement(AbstractStore):
    def __init__(self):
        self.mongo_store = MongoDBStoreBase(collection_prefix="goofish")

    async def store_content(self, content_item: Dict):
        item_id = content_item.get("item_id")
        if not item_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="contents",
            query={"item_id": item_id},
            data=content_item,
        )
        utils.logger.info(f"[GoofishMongoStoreImplement.store_content] Saved item {item_id} to MongoDB")

    async def store_comment(self, comment_item: Dict):
        comment_id = comment_item.get("comment_id")
        if not comment_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="comments",
            query={"comment_id": comment_id},
            data=comment_item,
        )
        utils.logger.info(f"[GoofishMongoStoreImplement.store_comment] Saved comment {comment_id} to MongoDB")

    async def store_creator(self, creator: Dict):
        user_id = creator.get("user_id")
        if not user_id:
            return
        await self.mongo_store.save_or_update(
            collection_suffix="creators",
            query={"user_id": user_id},
            data=creator,
        )
        utils.logger.info(f"[GoofishMongoStoreImplement.store_creator] Saved creator {user_id} to MongoDB")


class GoofishExcelStoreImplement:
    def __new__(cls, *args, **kwargs):
        from store.excel_store_base import ExcelStoreBase

        return ExcelStoreBase.get_instance(
            platform="goofish",
            crawler_type=crawler_type_var.get(),
        )
