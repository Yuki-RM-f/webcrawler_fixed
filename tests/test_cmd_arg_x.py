# -*- coding: utf-8 -*-

import config
import pytest
from cmd_arg import parse_cmd


@pytest.mark.asyncio
async def test_x_search_cli_sets_platform_and_keywords():
    await parse_cmd(
        [
            "--platform",
            "x",
            "--type",
            "search",
            "--keywords",
            "openai,ai",
            "--get_comment",
            "false",
        ]
    )

    assert config.PLATFORM == "x"
    assert config.CRAWLER_TYPE == "search"
    assert config.KEYWORDS == "openai,ai"
    assert config.ENABLE_GET_COMMENTS is False


@pytest.mark.asyncio
async def test_x_search_cli_defaults_comment_off(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", True)
    monkeypatch.setattr(config, "PLATFORM", "xhs")

    await parse_cmd(
        [
            "--platform",
            "x",
            "--type",
            "search",
            "--keywords",
            "openai",
        ]
    )

    assert config.PLATFORM == "x"
    assert config.ENABLE_GET_COMMENTS is False


@pytest.mark.asyncio
async def test_x_search_cli_keeps_explicit_comment_true(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_GET_COMMENTS", False)
    monkeypatch.setattr(config, "PLATFORM", "xhs")

    await parse_cmd(
        [
            "--platform",
            "x",
            "--type",
            "search",
            "--keywords",
            "openai",
            "--get_comment",
            "true",
        ]
    )

    assert config.PLATFORM == "x"
    assert config.ENABLE_GET_COMMENTS is True
