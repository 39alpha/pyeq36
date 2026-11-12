"""Provide fixtures and Hypothesis settings profiles shared by the test suite."""

from typing import cast

import pytest
from hypothesis import settings

from .eqpt_reference import D1F, DATA_DIR, DATABASES, read_d0_grid, read_d1f

settings.register_profile("dev", max_examples=10)
settings.register_profile("thorough", max_examples=5_000, deadline=None)


@pytest.fixture(autouse=True)
def _unset_eq36_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that the bundled binaries are used unless a test sets `EQ36_BIN` itself.

    @param monkeypatch The pytest monkeypatch fixture
    """
    monkeypatch.delenv("EQ36_BIN", raising=False)


@pytest.fixture(scope="module", params=DATABASES)
def database(request: pytest.FixtureRequest) -> str:
    """
    Provide the name of each database in the `eqpt` test data.

    @param request The pytest fixture request, whose `param` is the database name

    @return The name of the database, e.g. `"cmp"`
    """
    return cast("str", request.param)


@pytest.fixture(scope="module")
def d1f(database: str) -> D1F:
    """
    Read the reference values from the database's `.d1f` file.

    @param database The name of the database

    @return The reference values
    """
    return read_d1f(DATA_DIR / f"{database}.d1f")


@pytest.fixture(scope="module")
def d0_grid(database: str) -> list[tuple[float, float]]:
    """
    Read the temperature-pressure grid from the database's `.d0` file.

    @param database The name of the database

    @return The `(temperature, pressure)` points of the grid
    """
    return read_d0_grid(DATA_DIR / f"{database}.d0")
