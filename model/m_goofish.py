# -*- coding: utf-8 -*-

from typing import List

from pydantic import BaseModel, Field


class GoofishItem(BaseModel):
    item_id: str = Field(..., description="Goofish item ID")
    item_url: str = Field(default="", description="Item detail URL")
    category_id: str = Field(default="", description="Item category ID")
    title: str = Field(default="", description="Item title")
    desc: str = Field(default="", description="Item description")
    price: str = Field(default="", description="Item price")
    location: str = Field(default="", description="Item location")
    publish_time: str = Field(default="", description="Publish time")
    seller_id: str = Field(default="", description="Seller user ID")
    seller_nickname: str = Field(default="", description="Seller nickname")
    seller_avatar: str = Field(default="", description="Seller avatar URL")
    seller_homepage_url: str = Field(default="", description="Seller homepage URL")
    image_list: str = Field(default="", description="Item image URLs")
    source_keyword: str = Field(default="", description="Source search keyword")


class GoofishComment(BaseModel):
    comment_id: str = Field(..., description="Comment ID")
    item_id: str = Field(..., description="Goofish item ID")
    parent_comment_id: str = Field(default="", description="Parent comment ID")
    content: str = Field(default="", description="Comment content")
    publish_time: str = Field(default="", description="Publish time")
    user_id: str = Field(default="", description="Comment user ID")
    nickname: str = Field(default="", description="Comment user nickname")
    avatar: str = Field(default="", description="Comment user avatar")
    pictures: str = Field(default="", description="Comment image URLs")
    like_count: str = Field(default="0", description="Like count")


class GoofishCreator(BaseModel):
    user_id: str = Field(..., description="Seller user ID")
    nickname: str = Field(default="", description="Seller nickname")
    avatar: str = Field(default="", description="Seller avatar URL")
    seller_homepage_url: str = Field(default="", description="Seller homepage URL")
    desc: str = Field(default="", description="Seller profile description")
    location: str = Field(default="", description="Seller location")
    fans_count: str = Field(default="", description="Fans count")
    follows_count: str = Field(default="", description="Follows count")
    credit_level: str = Field(default="", description="Credit level")


class GoofishDetail(BaseModel):
    item: GoofishItem
    comments: List[GoofishComment] = Field(default_factory=list)
