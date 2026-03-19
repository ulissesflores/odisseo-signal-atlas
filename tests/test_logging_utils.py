import logging
from typing import Any

import pytest

from odisseo_signal_atlas.logging_utils import configure_logging


def test_configure_logging_sets_root_and_quiets_http_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_basic_config(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    configure_logging("debug")

    assert captured["level"] == logging.DEBUG
    assert captured["format"] == "%(asctime)s %(levelname)s %(name)s - %(message)s"
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
