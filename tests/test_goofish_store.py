# -*- coding: utf-8 -*-

from unittest.mock import patch

import pytest

from store.excel_store_base import ExcelStoreBase
from store.goofish import GoofishStoreFactory
from store.goofish._store_impl import (
    GoofishCsvStoreImplement,
    GoofishDbStoreImplement,
    GoofishExcelStoreImplement,
    GoofishJsonStoreImplement,
    GoofishJsonlStoreImplement,
    GoofishMongoStoreImplement,
    GoofishSqliteStoreImplement,
)


@pytest.mark.parametrize(
    ("save_option", "expected_cls"),
    [
        ("csv", GoofishCsvStoreImplement),
        ("json", GoofishJsonStoreImplement),
        ("jsonl", GoofishJsonlStoreImplement),
        ("db", GoofishDbStoreImplement),
        ("postgres", GoofishDbStoreImplement),
        ("sqlite", GoofishSqliteStoreImplement),
        ("mongodb", GoofishMongoStoreImplement),
        ("excel", GoofishExcelStoreImplement),
    ],
)
def test_goofish_store_factory_registers_supported_storage_options(
    save_option,
    expected_cls,
):
    with patch("config.SAVE_DATA_OPTION", save_option):
        store = GoofishStoreFactory.create_store()

    if save_option == "excel":
        assert isinstance(store, ExcelStoreBase)
        assert store.platform == "goofish"
    else:
        assert isinstance(store, expected_cls)


def test_goofish_store_factory_rejects_unsupported_storage_option():
    with patch("config.SAVE_DATA_OPTION", "invalid"):
        with pytest.raises(ValueError, match="Invalid save option"):
            GoofishStoreFactory.create_store()
