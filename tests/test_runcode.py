"""Test the `RunCode` enum."""

import pytest

from eq36 import RunCode


def test_runcode_from_invalid_int() -> None:
    """Ensure an error is raised when constructing a `RunCode` from an invalid value."""
    with pytest.raises(ValueError):  # noqa: PT011
        _ = RunCode(-100)


@pytest.mark.parametrize(("code", "value"), [(code, code.value) for code in RunCode])
def test_runcode_from_int(code: RunCode, value: int) -> None:
    """
    Ensure that `RunCode` instances can be constructed from their value.

    @param code  A `RunCode` instance
    @param value The integer value of `code`
    """
    assert code == RunCode(value)


@pytest.mark.parametrize(("code", "value"), [(code, code.value) for code in RunCode])
def test_runcode_str_is_not_int(code: RunCode, value: int) -> None:
    """
    Ensure that `RunCode.__str__` produces informative messages for all values.

    A message is considered informative if it is not simply the integer value.

    @param code  A `RunCode` instance
    @param value The integer value of `code`
    """
    assert str(code) != f"{value}"
