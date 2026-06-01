# -*- coding: utf-8 -*-

import json

import pytest
from fastapi.testclient import TestClient


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("platform", "kind", "filename", "row", "expected"),
    [
        (
            "dy",
            "contents",
            "search_contents_2026-05-30.jsonl",
            {
                "aweme_id": "7501",
                "title": "抖音刷粉",
                "desc": "刷赞接单",
                "create_time": "1748316965",
                "user_id": "u1",
                "sec_uid": "sec1",
                "nickname": "抖音作者",
                "aweme_url": "https://www.douyin.com/video/7501",
                "cover_url": "https://img.example/cover.jpg",
                "video_download_url": "https://video.example/7501.mp4",
                "source_keyword": "抖音 刷赞",
            },
            {
                "source_record_id": "douyin:aweme:7501",
                "source_type": "social_media",
                "source_name": "抖音",
                "source_url": "https://www.douyin.com/video/7501",
                "author_id": "u1",
                "author_name": "抖音作者",
                "author_homepage_url": "https://www.douyin.com/user/sec1",
                "publish_time": "2025-05-27T03:36:05+00:00",
                "raw_text": "抖音刷粉\n刷赞接单",
                "media_files": [
                    {"file_url": "https://img.example/cover.jpg", "file_type": "image", "source": "original_post"},
                    {"file_url": "https://video.example/7501.mp4", "file_type": "video", "source": "original_post"},
                ],
            },
        ),
        (
            "dy",
            "comments",
            "search_comments_2026-05-30.jsonl",
            {
                "comment_id": "c1",
                "aweme_id": "7501",
                "content": "全网最低，欢迎比价",
                "create_time": "1748316965000",
                "user_id": "u2",
                "sec_uid": "sec2",
                "nickname": "评论作者",
                "pictures": ["https://img.example/comment.jpg"],
            },
            {
                "source_record_id": "douyin:comment:c1",
                "source_type": "social_media",
                "source_name": "抖音",
                "source_url": "https://www.douyin.com/video/7501",
                "author_id": "u2",
                "author_name": "评论作者",
                "author_homepage_url": "https://www.douyin.com/user/sec2",
                "publish_time": "2025-05-27T03:36:05+00:00",
                "raw_text": "全网最低，欢迎比价",
                "media_files": [
                    {"file_url": "https://img.example/comment.jpg", "file_type": "image", "source": "comment"}
                ],
            },
        ),
        (
            "tieba",
            "contents",
            "search_contents_2026-05-30.jsonl",
            {
                "note_id": "9001",
                "title": "抖音刷赞",
                "desc": "接单渠道",
                "note_url": "https://tieba.baidu.com/p/9001",
                "publish_time": "2026-05-30T01:02:03Z",
                "user_link": "https://tieba.baidu.com/home/main?id=tb.u1",
                "user_nickname": "贴吧作者",
                "source_keyword": "抖音 刷赞",
            },
            {
                "source_record_id": "tieba:post:9001",
                "source_type": "forum",
                "source_name": "百度贴吧",
                "source_url": "https://tieba.baidu.com/p/9001",
                "author_id": "tb.u1",
                "author_name": "贴吧作者",
                "author_homepage_url": "https://tieba.baidu.com/home/main?id=tb.u1",
                "publish_time": "2026-05-30T01:02:03+00:00",
                "raw_text": "抖音刷赞\n接单渠道",
                "media_files": [],
            },
        ),
        (
            "tieba",
            "comments",
            "search_comments_2026-05-30.jsonl",
            {
                "comment_id": "tc1",
                "note_id": "9001",
                "content": "可以接单",
                "note_url": "https://tieba.baidu.com/p/9001",
                "publish_time": "2026-05-30T01:03:00Z",
                "user_link": "https://tieba.baidu.com/home/main?id=tb.u2",
                "user_nickname": "贴吧评论",
            },
            {
                "source_record_id": "tieba:comment:tc1",
                "source_type": "forum",
                "source_name": "百度贴吧",
                "source_url": "https://tieba.baidu.com/p/9001",
                "author_id": "tb.u2",
                "author_name": "贴吧评论",
                "author_homepage_url": "https://tieba.baidu.com/home/main?id=tb.u2",
                "publish_time": "2026-05-30T01:03:00+00:00",
                "raw_text": "可以接单",
                "media_files": [],
            },
        ),
        (
            "xhs",
            "contents",
            "search_contents_2026-05-30.jsonl",
            {
                "note_id": "x1",
                "title": "某音账号",
                "desc": "接码养号",
                "time": "1748316965000",
                "user_id": "xhs_u1",
                "nickname": "小红书作者",
                "note_url": "https://www.xiaohongshu.com/explore/x1",
                "image_list": ["https://img.example/xhs.jpg"],
                "video_url": "https://video.example/xhs.mp4",
                "source_keyword": "某音 接码",
            },
            {
                "source_record_id": "xhs:note:x1",
                "source_type": "social_media",
                "source_name": "小红书",
                "source_url": "https://www.xiaohongshu.com/explore/x1",
                "author_id": "xhs_u1",
                "author_name": "小红书作者",
                "author_homepage_url": "https://www.xiaohongshu.com/user/profile/xhs_u1",
                "publish_time": "2025-05-27T03:36:05+00:00",
                "raw_text": "某音账号\n接码养号",
                "media_files": [
                    {"file_url": "https://img.example/xhs.jpg", "file_type": "image", "source": "original_post"},
                    {"file_url": "https://video.example/xhs.mp4", "file_type": "video", "source": "original_post"},
                ],
            },
        ),
        (
            "xhs",
            "comments",
            "search_comments_2026-05-30.jsonl",
            {
                "comment_id": "xc1",
                "note_id": "x1",
                "content": "私聊报价",
                "create_time": "1748316965000",
                "user_id": "xhs_u2",
                "nickname": "小红书评论",
                "pictures": ["https://img.example/xhs-comment.jpg"],
            },
            {
                "source_record_id": "xhs:comment:xc1",
                "source_type": "social_media",
                "source_name": "小红书",
                "source_url": "https://www.xiaohongshu.com/explore/x1",
                "author_id": "xhs_u2",
                "author_name": "小红书评论",
                "author_homepage_url": "https://www.xiaohongshu.com/user/profile/xhs_u2",
                "publish_time": "2025-05-27T03:36:05+00:00",
                "raw_text": "私聊报价",
                "media_files": [
                    {"file_url": "https://img.example/xhs-comment.jpg", "file_type": "image", "source": "comment"}
                ],
            },
        ),
        (
            "x",
            "contents",
            "search_contents_2026-05-30.jsonl",
            {
                "tweet_id": "2060935199702253585",
                "tweet_url": "https://x.com/i/status/2060935199702253585",
                "content": "抖音涨粉刷赞接单，导航 https://t.co/a",
                "created_at": "Sun May 31 04:03:36 +0000 2026",
                "create_time": 1780200216,
                "user_id": "1573253756900110337",
                "username": "risk_ops",
                "nickname": "X 风控样本",
                "image_list": "https://img.example/x-post.jpg",
                "source_keyword": "抖音 刷赞",
            },
            {
                "source_record_id": "x:tweet:2060935199702253585",
                "source_type": "social_media",
                "source_name": "X",
                "source_url": "https://x.com/i/status/2060935199702253585",
                "author_id": "1573253756900110337",
                "author_name": "X 风控样本",
                "author_homepage_url": "https://x.com/risk_ops",
                "publish_time": "2026-05-31T04:03:36+00:00",
                "raw_text": "抖音涨粉刷赞接单，导航 https://t.co/a",
                "media_files": [
                    {"file_url": "https://img.example/x-post.jpg", "file_type": "image", "source": "original_post"}
                ],
            },
        ),
        (
            "x",
            "comments",
            "search_comments_2026-05-30.jsonl",
            {
                "comment_id": "2060935199702253001",
                "tweet_id": "2060935199702253585",
                "parent_comment_id": "2060935199702253585",
                "comment_url": "https://x.com/i/status/2060935199702253001",
                "content": "私聊报价",
                "create_time": 1780200220,
                "user_id": "1573253756900110338",
                "username": "reply_ops",
                "nickname": "X 回复样本",
                "pictures": "https://img.example/x-comment.jpg",
            },
            {
                "source_record_id": "x:comment:2060935199702253001",
                "source_type": "social_media",
                "source_name": "X",
                "source_url": "https://x.com/i/status/2060935199702253001",
                "author_id": "1573253756900110338",
                "author_name": "X 回复样本",
                "author_homepage_url": "https://x.com/reply_ops",
                "publish_time": "2026-05-31T04:03:40+00:00",
                "raw_text": "私聊报价",
                "media_files": [
                    {"file_url": "https://img.example/x-comment.jpg", "file_type": "image", "source": "comment"}
                ],
            },
        ),
        (
            "goofish",
            "contents",
            "search_contents_2026-05-30.jsonl",
            {
                "item_id": "1037584161596",
                "item_url": "https://www.goofish.com/item?id=1037584161596",
                "title": "闲鱼账号资源",
                "desc": "支持刷赞刷粉，联系私聊",
                "price": "88.00",
                "location": "上海",
                "publish_time": "1774564357000",
                "seller_id": "seller1",
                "seller_nickname": "闲鱼卖家",
                "seller_homepage_url": "https://www.goofish.com/personal?userId=seller1",
                "image_list": "https://img.example/goofish.jpg",
                "source_keyword": "tiktok 刷赞",
            },
            {
                "source_record_id": "goofish:item:1037584161596",
                "source_type": "vertical_site",
                "source_name": "闲鱼",
                "source_url": "https://www.goofish.com/item?id=1037584161596",
                "author_id": "seller1",
                "author_name": "闲鱼卖家",
                "author_homepage_url": "https://www.goofish.com/personal?userId=seller1",
                "publish_time": "2026-03-26T22:32:37+00:00",
                "raw_text": "闲鱼账号资源\n支持刷赞刷粉，联系私聊\n价格: 88.00\n位置: 上海",
                "media_files": [
                    {"file_url": "https://img.example/goofish.jpg", "file_type": "image", "source": "original_post"}
                ],
            },
        ),
        (
            "goofish",
            "comments",
            "search_comments_2026-05-30.jsonl",
            {
                "comment_id": "gf-c1",
                "item_id": "1037584161596",
                "parent_comment_id": "",
                "content": "还能便宜吗，私聊",
                "publish_time": "1774564360000",
                "user_id": "buyer1",
                "nickname": "闲鱼买家",
                "pictures": "https://img.example/goofish-comment.jpg",
            },
            {
                "source_record_id": "goofish:comment:gf-c1",
                "source_type": "vertical_site",
                "source_name": "闲鱼",
                "source_url": "https://www.goofish.com/item?id=1037584161596",
                "author_id": "buyer1",
                "author_name": "闲鱼买家",
                "author_homepage_url": "",
                "publish_time": "2026-03-26T22:32:40+00:00",
                "raw_text": "还能便宜吗，私聊",
                "media_files": [
                    {"file_url": "https://img.example/goofish-comment.jpg", "file_type": "image", "source": "comment"}
                ],
            },
        ),
    ],
)
def test_black_gray_intel_records_maps_media_crawler_jsonl(tmp_path, monkeypatch, platform, kind, filename, row, expected):
    from api.main import app
    from api.routers import black_gray_intel

    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)
    write_jsonl(tmp_path / platform_to_dir(platform) / "jsonl" / filename, [row])

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": platform, "kind": kind, "date": "2026-05-30"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["source_files"] == [f"{platform_to_dir(platform)}/jsonl/{filename}"]
    assert body["warnings"] == []
    item = body["items"][0]
    assert {key: item[key] for key in expected} == expected
    assert item["metadata"]["record_kind"] == kind
    assert item["metadata"]["media_crawler_platform"] == platform
    assert item["metadata"]["source_keyword"] == row.get("source_keyword", "")


def test_black_gray_intel_records_uses_latest_files_and_paginates(tmp_path, monkeypatch):
    from api.main import app
    from api.routers import black_gray_intel

    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)
    write_jsonl(tmp_path / "douyin" / "jsonl" / "search_contents_2026-05-29.jsonl", [{"aweme_id": "old", "title": "old"}])
    write_jsonl(
        tmp_path / "douyin" / "jsonl" / "search_contents_2026-05-30.jsonl",
        [{"aweme_id": "new1", "title": "new1"}, {"aweme_id": "new2", "title": "new2"}],
    )
    write_jsonl(
        tmp_path / "douyin" / "jsonl" / "search_comments_2026-05-30.jsonl",
        [{"comment_id": "c1", "aweme_id": "new1", "content": "comment1"}],
    )

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": "dy", "kind": "all", "date": "latest", "offset": 1, "limit": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [item["source_record_id"] for item in body["items"]] == [
        "douyin:aweme:new2",
        "douyin:comment:c1",
    ]
    assert body["source_files"] == [
        "douyin/jsonl/search_contents_2026-05-30.jsonl",
        "douyin/jsonl/search_comments_2026-05-30.jsonl",
    ]


def test_black_gray_intel_records_maps_tieba_image_fields_to_media_files(tmp_path, monkeypatch):
    from api.main import app
    from api.routers import black_gray_intel

    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)
    write_jsonl(
        tmp_path / "tieba" / "jsonl" / "search_contents_2026-05-30.jsonl",
        [
            {
                "note_id": "9001",
                "title": "title",
                "note_url": "https://tieba.baidu.com/p/9001",
                "image_list": "https://img.example/post-a.jpg,https://img.example/post-b.jpg",
            }
        ],
    )

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": "tieba", "kind": "contents", "date": "2026-05-30"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["media_files"] == [
        {"file_url": "https://img.example/post-a.jpg", "file_type": "image", "source": "original_post"},
        {"file_url": "https://img.example/post-b.jpg", "file_type": "image", "source": "original_post"},
    ]


def test_black_gray_intel_records_omits_legacy_image_text_metadata(tmp_path, monkeypatch):
    from api.main import app
    from api.routers import black_gray_intel

    legacy_image_text_field = "image" + "_ocr_results"
    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)
    write_jsonl(
        tmp_path / "xhs" / "jsonl" / "search_contents_2026-05-30.jsonl",
        [
            {
                "note_id": "x1",
                "title": "title",
                "image_list": "https://img.example/xhs-a.jpg",
                legacy_image_text_field: [
                    {
                        "image_url": "https://img.example/xhs-a.jpg",
                        "text": "legacy OCR text",
                    }
                ],
            }
        ],
    )

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": "xhs", "kind": "contents", "date": "2026-05-30"},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["media_files"] == [
        {"file_url": "https://img.example/xhs-a.jpg", "file_type": "image", "source": "original_post"}
    ]
    assert legacy_image_text_field not in item["metadata"]


def test_black_gray_intel_records_maps_goofish_image_ocr_results_to_media_files(tmp_path, monkeypatch):
    from api.main import app
    from api.routers import black_gray_intel

    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)
    write_jsonl(
        tmp_path / "goofish" / "jsonl" / "search_contents_2026-05-31.jsonl",
        [
            {
                "item_id": "1037584161596",
                "title": "闲鱼刷赞服务",
                "image_list": "https://img.example/a.jpg,https://img.example/b.jpg",
                "image_ocr_results": [
                    {
                        "image_url": "https://img.example/a.jpg",
                        "text": "图片里写着刷赞接单",
                        "status": "done",
                        "error": "",
                    },
                    {
                        "image_url": "https://img.example/b.jpg",
                        "text": "",
                        "status": "failed",
                        "error": "download timeout",
                    },
                ],
            }
        ],
    )

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": "goofish", "kind": "contents", "date": "2026-05-31"},
    )

    assert response.status_code == 200
    media_files = response.json()["items"][0]["media_files"]
    assert media_files == [
        {
            "file_url": "https://img.example/a.jpg",
            "file_type": "image",
            "source": "original_post",
            "ocr_text": "图片里写着刷赞接单",
            "ocr_source": "media_crawler_image_ocr",
            "ocr_provider": "mediacrawler",
        },
        {
            "file_url": "https://img.example/b.jpg",
            "file_type": "image",
            "source": "original_post",
            "ocr_error": "download timeout",
            "ocr_source": "media_crawler_image_ocr",
            "ocr_provider": "mediacrawler",
        },
    ]
    assert response.json()["items"][0]["metadata"]["image_ocr_results"][0]["text"] == "图片里写着刷赞接单"


def test_black_gray_intel_records_returns_empty_for_missing_files(tmp_path, monkeypatch):
    from api.main import app
    from api.routers import black_gray_intel

    monkeypatch.setattr(black_gray_intel, "DATA_DIR", tmp_path)

    response = TestClient(app).get(
        "/api/black-gray-intel/records",
        params={"platform": "xhs", "kind": "all", "date": "2026-05-30"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["source_files"] == []
    assert "No MediaCrawler JSONL files found" in body["warnings"][0]


def platform_to_dir(platform):
    return {"dy": "douyin", "tieba": "tieba", "xhs": "xhs", "x": "x", "goofish": "goofish"}[platform]
