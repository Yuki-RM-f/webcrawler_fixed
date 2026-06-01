# -*- coding: utf-8 -*-

from media_platform.goofish.help import GoofishExtractor


def test_extract_search_items_from_mtop_payload_normalizes_item_cards():
    payload = {
        "data": {
            "resultList": [
                {
                    "cardData": {
                        "itemId": "1001",
                        "categoryId": "201",
                        "title": "iPhone 15",
                        "description": "国行在保",
                        "priceInfo": {"price": "4999"},
                        "area": "杭州",
                        "picInfo": {"picUrl": "https://img.example/a.jpg"},
                        "sellerInfo": {
                            "userId": "seller-1",
                            "nick": "卖家A",
                            "avatar": "https://img.example/avatar.jpg",
                        },
                    }
                },
                {
                    "data": {
                        "item": {
                            "id": "1002",
                            "categoryId": "202",
                            "title": "显卡",
                            "content": "自用拆机",
                            "price": "1200",
                            "imageInfos": [{"url": "https://img.example/b.jpg"}],
                            "seller": {"id": "seller-2", "nickname": "卖家B"},
                        }
                    }
                },
            ]
        }
    }

    items = GoofishExtractor.extract_search_items(payload)

    assert [item.item_id for item in items] == ["1001", "1002"]
    assert items[0].item_url == "https://www.goofish.com/item?id=1001&categoryId=201"
    assert items[0].price == "4999"
    assert items[0].seller_id == "seller-1"
    assert items[0].seller_nickname == "卖家A"
    assert items[0].image_list == "https://img.example/a.jpg"
    assert items[1].desc == "自用拆机"
    assert items[1].image_list == "https://img.example/b.jpg"


def test_extract_detail_from_mtop_payload_keeps_images_seller_and_comments():
    payload = {
        "data": {
            "item": {
                "itemId": "1001",
                "categoryId": "201",
                "title": "闲置手机",
                "desc": "九成新",
                "price": "888",
                "location": "上海",
                "publishTime": "2026-05-30 12:00:00",
                "imageList": [
                    {"url": "https://img.example/detail-a.jpg"},
                    "https://img.example/detail-b.jpg",
                ],
            },
            "seller": {
                "userId": "seller-1",
                "nickname": "卖家A",
                "avatar": "https://img.example/seller.jpg",
            },
            "comments": [
                {
                    "commentId": "c1",
                    "content": "还在吗",
                    "publishTime": "2026-05-30 13:00:00",
                    "likeCount": 3,
                    "user": {
                        "userId": "buyer-1",
                        "nickname": "买家A",
                        "avatar": "https://img.example/buyer.jpg",
                    },
                    "pictures": [{"url": "https://img.example/comment.jpg"}],
                }
            ],
        }
    }

    detail = GoofishExtractor.extract_detail(payload, fallback_item_id="1001")

    assert detail.item.item_id == "1001"
    assert detail.item.title == "闲置手机"
    assert detail.item.seller_homepage_url.endswith("%7B%22userId%22%3A%22seller-1%22%7D")
    assert detail.item.image_list == "https://img.example/detail-a.jpg,https://img.example/detail-b.jpg"
    assert len(detail.comments) == 1
    assert detail.comments[0].comment_id == "c1"
    assert detail.comments[0].item_id == "1001"
    assert detail.comments[0].pictures == "https://img.example/comment.jpg"


def test_extract_detail_without_public_comments_returns_empty_comment_list():
    payload = {
        "data": {
            "item": {
                "itemId": "1001",
                "title": "闲置手机",
            }
        }
    }

    detail = GoofishExtractor.extract_detail(payload, fallback_item_id="1001")

    assert detail.item.item_id == "1001"
    assert detail.comments == []


def test_extract_creator_from_public_payload():
    payload = {
        "data": {
            "seller": {
                "userId": "seller-1",
                "nickname": "卖家A",
                "avatar": "https://img.example/seller.jpg",
                "fansCount": 12,
                "creditLevel": "优秀",
            }
        }
    }

    creator = GoofishExtractor.extract_creator(payload, fallback_user_id="seller-1")

    assert creator.user_id == "seller-1"
    assert creator.nickname == "卖家A"
    assert creator.seller_homepage_url.endswith("%7B%22userId%22%3A%22seller-1%22%7D")
    assert creator.fans_count == "12"
    assert creator.credit_level == "优秀"
