# -*- coding: utf-8 -*-

import config
import pytest
import typer
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_goofish_search_cli_sets_platform_and_keywords():
    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--keywords",
            "iphone,显卡",
        ]
    )

    assert config.PLATFORM == "goofish"
    assert config.CRAWLER_TYPE == "search"
    assert config.KEYWORDS == "iphone,显卡"


@pytest.mark.asyncio
async def test_goofish_cli_disables_public_comments_even_when_requested():
    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--get_comment",
            "true",
            "--get_sub_comment",
            "true",
        ]
    )

    assert config.ENABLE_GET_COMMENTS is False
    assert config.ENABLE_GET_SUB_COMMENTS is False


@pytest.mark.asyncio
async def test_goofish_search_cli_recovers_windows_question_mark_keywords(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", "抖音 刷赞,tiktok 刷赞,抖音 买号")

    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--keywords",
            "tiktok ??",
        ]
    )

    assert config.KEYWORDS == "tiktok 刷赞"


@pytest.mark.asyncio
async def test_goofish_search_cli_recovers_full_windows_question_mark_keyword_list(monkeypatch):
    default_keywords = "抖音 刷赞,tiktok 刷赞,抖音 买号"
    monkeypatch.setattr(config, "KEYWORDS", default_keywords)

    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--keywords",
            "?? ??,tiktok ??,?? ??",
        ]
    )

    assert config.KEYWORDS == default_keywords


@pytest.mark.asyncio
async def test_goofish_search_cli_rejects_unrecoverable_question_mark_keywords(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", "抖音 刷赞,tiktok 刷赞,抖音 买号")

    with pytest.raises(typer.BadParameter, match="Chinese keyword characters were replaced"):
        await parse_cmd(
            [
                "--platform",
                "goofish",
                "--type",
                "search",
                "--keywords",
                "unknown ??",
            ]
        )


@pytest.mark.asyncio
async def test_goofish_search_cli_keeps_plain_ascii_question_marks(monkeypatch):
    monkeypatch.setattr(config, "KEYWORDS", "抖音 刷赞,tiktok 刷赞,抖音 买号")

    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "search",
            "--keywords",
            "what?",
        ]
    )

    assert config.KEYWORDS == "what?"


@pytest.mark.asyncio
async def test_goofish_detail_cli_accepts_item_urls_and_ids():
    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "detail",
            "--specified_id",
            "https://www.goofish.com/item?id=996308918808&categoryId=201943802,912469187094",
        ]
    )

    assert config.GOOFISH_SPECIFIED_ID_LIST == [
        "996308918808",
        "912469187094",
    ]


@pytest.mark.asyncio
async def test_goofish_creator_cli_accepts_raw_user_ids_and_share_urls():
    await parse_cmd(
        [
            "--platform",
            "goofish",
            "--type",
            "creator",
            "--creator_id",
            (
                "12345,"
                "https://pages.goofish.com/sharexy?bft=personal&bfp="
                "%7B%22userId%22%3A%2267890%22%7D"
            ),
        ]
    )

    assert config.GOOFISH_CREATOR_ID_LIST == ["12345", "67890"]
