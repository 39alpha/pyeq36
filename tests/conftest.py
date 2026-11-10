"""Provide fixtures shared by the test suite."""

import pytest


@pytest.fixture(autouse=True)
def _unset_eq36_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that the bundled binaries are used unless a test sets `EQ36_BIN` itself.

    @param monkeypatch The pytest monkeypatch fixture
    """
    monkeypatch.delenv("EQ36_BIN", raising=False)
