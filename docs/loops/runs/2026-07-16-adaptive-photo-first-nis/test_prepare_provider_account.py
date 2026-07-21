from __future__ import annotations

import sys
from pathlib import Path

import pytest


RUN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(RUN_DIR))

import prepare_provider_account  # noqa: E402


def test_validate_test_pin_rejects_value_the_ui_would_truncate() -> None:
    with pytest.raises(SystemExit, match="4 to 12 characters"):
        prepare_provider_account.validate_test_pin("a" * 13)
