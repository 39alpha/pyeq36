"""
Determine whether text can be represented in the Windows ANSI code page.

On Windows, `eq36.libpyeq36.read_data1` encodes filenames with the ANSI code
page (`mbcs`), so tests involving non-ASCII filenames depend on the code page
of the machine on which they run.
"""

from __future__ import annotations

import sys

import pytest


def ansi_encodable(text: str) -> bool:
    """
    Determine whether text can be encoded with the ANSI code page, which is only used on Windows.

    @param text The text to encode

    @return `True` if `text` can be encoded with the ANSI code page or the
            platform is not Windows, and `False` otherwise
    """
    if not sys.platform.startswith("win"):
        return True
    try:
        _ = text.encode("mbcs")
    except UnicodeEncodeError:
        return False
    return True


## The non-ASCII character used in filenames by the tests
NON_ASCII = "μ"

## Skip a test if the ANSI code page cannot represent `NON_ASCII`
requires_non_ascii = pytest.mark.skipif(
    not ansi_encodable(NON_ASCII),
    reason=f"the ANSI code page cannot represent {NON_ASCII!r}",
)
