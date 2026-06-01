# -*- coding: utf-8 -*-

from typing import Any, Dict, Iterable, List, Optional

from tools import utils


def _iter_tweet_result_nodes(node: Any) -> Iterable[Dict]:
    if isinstance(node, dict):
        tweet_results = node.get("tweet_results")
        if isinstance(tweet_results, dict):
            result = tweet_results.get("result")
            if isinstance(result, dict):
                yield result

        for value in node.values():
            yield from _iter_tweet_result_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_tweet_result_nodes(value)


def _unwrap_tweet_result(result: Dict) -> Dict:
    current = result
    for _ in range(5):
        if not isinstance(current, dict):
            return {}
        if isinstance(current.get("tweet"), dict):
            current = current["tweet"]
            continue
        if isinstance(current.get("tweetResult"), dict):
            current = current["tweetResult"].get("result", {})
            continue
        if isinstance(current.get("result"), dict):
            current = current["result"]
            continue
        break
    return current if isinstance(current, dict) else {}


def _as_count(value: Any) -> str:
    if value is None:
        return "0"
    return str(value)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _parse_created_at(created_at: str) -> int:
    if not created_at:
        return 0
    try:
        return utils.rfc2822_to_timestamp(created_at)
    except Exception:
        return 0


def _extract_photo_urls(legacy: Dict) -> str:
    image_urls = []
    seen = set()
    for entity_key in ("extended_entities", "entities"):
        media_items = (legacy.get(entity_key) or {}).get("media") or []
        if not isinstance(media_items, list):
            continue
        for media_item in media_items:
            if not isinstance(media_item, dict) or media_item.get("type") != "photo":
                continue
            image_url = media_item.get("media_url_https") or media_item.get("media_url") or ""
            if image_url and image_url not in seen:
                seen.add(image_url)
                image_urls.append(str(image_url))
    return ",".join(image_urls)


def normalize_tweet_result(result: Dict) -> Optional[Dict]:
    tweet = _unwrap_tweet_result(result)
    legacy = tweet.get("legacy") or {}
    tweet_id = tweet.get("rest_id") or legacy.get("id_str")
    content = legacy.get("full_text") or legacy.get("text") or ""
    if not tweet_id or not content:
        return None

    user_result = (
        tweet.get("core", {})
        .get("user_results", {})
        .get("result", {})
    )
    user_legacy = user_result.get("legacy") or {}
    username = user_legacy.get("screen_name", "")
    created_at = legacy.get("created_at", "")

    return {
        "tweet_id": str(tweet_id),
        "tweet_url": (
            f"https://x.com/{username}/status/{tweet_id}"
            if username else f"https://x.com/i/status/{tweet_id}"
        ),
        "content": content,
        "created_at": created_at,
        "create_time": _parse_created_at(created_at),
        "user_id": str(user_result.get("rest_id") or user_legacy.get("id_str") or ""),
        "username": username,
        "nickname": user_legacy.get("name", ""),
        "avatar": user_legacy.get("profile_image_url_https", ""),
        "reply_count": _as_count(legacy.get("reply_count")),
        "retweet_count": _as_count(legacy.get("retweet_count")),
        "like_count": _as_count(legacy.get("favorite_count")),
        "quote_count": _as_count(legacy.get("quote_count")),
        "view_count": _as_count((tweet.get("views") or {}).get("count")),
        "conversation_id_str": _as_str(legacy.get("conversation_id_str")),
        "in_reply_to_status_id_str": _as_str(legacy.get("in_reply_to_status_id_str")),
        "in_reply_to_user_id_str": _as_str(legacy.get("in_reply_to_user_id_str")),
        "image_list": _extract_photo_urls(legacy),
    }


def extract_tweets_from_graphql(payload: Dict) -> List[Dict]:
    tweets: List[Dict] = []
    seen_tweet_ids = set()
    for result in _iter_tweet_result_nodes(payload):
        tweet = normalize_tweet_result(result)
        if not tweet:
            continue
        tweet_id = tweet["tweet_id"]
        if tweet_id in seen_tweet_ids:
            continue
        seen_tweet_ids.add(tweet_id)
        tweets.append(tweet)
    return tweets
