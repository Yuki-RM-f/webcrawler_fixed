# -*- coding: utf-8 -*-

from media_platform.x.help import extract_tweets_from_graphql


def test_extract_tweets_from_search_graphql_response():
    payload = {
        "data": {
            "search_by_raw_query": {
                "search_timeline": {
                    "timeline": {
                        "instructions": [
                            {
                                "entries": [
                                    {
                                        "content": {
                                            "itemContent": {
                                                "tweet_results": {
                                                    "result": {
                                                        "__typename": "Tweet",
                                                        "rest_id": "1800000000000000001",
                                                        "views": {"count": "42"},
                                                        "core": {
                                                            "user_results": {
                                                                "result": {
                                                                    "rest_id": "1001",
                                                                    "legacy": {
                                                                        "screen_name": "alice",
                                                                        "name": "Alice",
                                                                        "profile_image_url_https": "https://img.example/avatar.jpg",
                                                                    },
                                                                }
                                                            }
                                                        },
                                                        "legacy": {
                                                            "full_text": "hello from x",
                                                            "created_at": "Sat May 30 12:34:56 +0000 2026",
                                                            "reply_count": 1,
                                                            "retweet_count": 2,
                                                            "favorite_count": 3,
                                                            "quote_count": 4,
                                                        },
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    {
                                        "content": {
                                            "itemContent": {
                                                "tweet_results": {
                                                    "result": {
                                                        "__typename": "Tweet",
                                                        "rest_id": "1800000000000000001",
                                                        "legacy": {"full_text": "duplicate"},
                                                    }
                                                }
                                            }
                                        }
                                    },
                                    {
                                        "content": {
                                            "itemContent": {
                                                "promotedMetadata": {"advertiser": "skip"},
                                            }
                                        }
                                    },
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }

    tweets = extract_tweets_from_graphql(payload)

    assert tweets == [
        {
            "tweet_id": "1800000000000000001",
            "tweet_url": "https://x.com/alice/status/1800000000000000001",
            "content": "hello from x",
            "created_at": "Sat May 30 12:34:56 +0000 2026",
            "create_time": 1780144496,
            "user_id": "1001",
            "username": "alice",
            "nickname": "Alice",
            "avatar": "https://img.example/avatar.jpg",
            "reply_count": "1",
            "retweet_count": "2",
            "like_count": "3",
            "quote_count": "4",
            "view_count": "42",
            "conversation_id_str": "",
            "in_reply_to_status_id_str": "",
            "in_reply_to_user_id_str": "",
            "image_list": "",
        }
    ]


def test_extract_tweets_unwraps_visibility_results_and_skips_missing_text():
    payload = {
        "tweet_results": {
            "result": {
                "__typename": "TweetWithVisibilityResults",
                "tweet": {
                    "rest_id": "1800000000000000002",
                    "core": {
                        "user_results": {
                            "result": {
                                "rest_id": "1002",
                                "legacy": {"screen_name": "bob", "name": "Bob"},
                            }
                        }
                    },
                    "legacy": {
                        "full_text": "",
                        "created_at": "Sat May 30 12:34:56 +0000 2026",
                    },
                },
            }
        }
    }

    assert extract_tweets_from_graphql(payload) == []


def test_extract_tweets_preserves_reply_relationship_fields():
    payload = {
        "tweet_results": {
            "result": {
                "__typename": "Tweet",
                "rest_id": "1800000000000000003",
                "core": {
                    "user_results": {
                        "result": {
                            "rest_id": "1003",
                            "legacy": {"screen_name": "carol", "name": "Carol"},
                        }
                    }
                },
                "legacy": {
                    "full_text": "reply from x",
                    "created_at": "Sat May 30 12:35:56 +0000 2026",
                    "conversation_id_str": "1800000000000000001",
                    "in_reply_to_status_id_str": "1800000000000000001",
                    "in_reply_to_user_id_str": "1001",
                },
            }
        }
    }

    tweets = extract_tweets_from_graphql(payload)

    assert tweets[0]["conversation_id_str"] == "1800000000000000001"
    assert tweets[0]["in_reply_to_status_id_str"] == "1800000000000000001"
    assert tweets[0]["in_reply_to_user_id_str"] == "1001"


def test_extract_tweets_keeps_unique_photo_urls_from_graphql_media_entities():
    payload = {
        "tweet_results": {
            "result": {
                "__typename": "Tweet",
                "rest_id": "1800000000000000004",
                "core": {
                    "user_results": {
                        "result": {
                            "rest_id": "1004",
                            "legacy": {"screen_name": "dave", "name": "Dave"},
                        }
                    }
                },
                "legacy": {
                    "full_text": "post with photos",
                    "created_at": "Sat May 30 12:35:56 +0000 2026",
                    "extended_entities": {
                        "media": [
                            {
                                "type": "photo",
                                "media_url_https": "https://img.example/x-photo-a.jpg",
                            },
                            {
                                "type": "photo",
                                "media_url": "http://img.example/x-photo-b.jpg",
                            },
                            {
                                "type": "animated_gif",
                                "media_url_https": "https://img.example/x-gif.jpg",
                            },
                        ]
                    },
                    "entities": {
                        "media": [
                            {
                                "type": "photo",
                                "media_url_https": "https://img.example/x-photo-a.jpg",
                            },
                            {
                                "type": "photo",
                                "media_url_https": "https://img.example/x-photo-c.jpg",
                            },
                        ]
                    },
                },
            }
        }
    }

    tweets = extract_tweets_from_graphql(payload)

    assert tweets[0]["image_list"] == (
        "https://img.example/x-photo-a.jpg,"
        "http://img.example/x-photo-b.jpg,"
        "https://img.example/x-photo-c.jpg"
    )
