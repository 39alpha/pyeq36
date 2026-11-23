"""
Prepare runs of the EQ3/6 binaries on the EQ3/6 test data, with non-ASCII filenames.

Each run copies test data files into a directory under a common non-ASCII stem,
keeping their extensions. The binaries name the files they write after their
last argument, so the files they write share the same stem.

The filenames are passed to the binaries without a directory, so that only
their encoding, and not the binaries' handling of path separators, is tested.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from .ansi import NON_ASCII, ansi_encodable
from .eqpt_reference import DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

## The directory containing the EQ3/6 test data
EQ36_DATA_DIR = DATA_DIR.parent

## Stems of the non-ASCII filenames, one that the Windows-1252 code page can represent and one that it cannot.
NON_ASCII_STEMS = [
    pytest.param(
        stem,
        marks=pytest.mark.xfail(
            not ansi_encodable(stem),
            reason=f"the ANSI code page cannot represent {stem!r}",
            strict=True,
        ),
    )
    for stem in [NON_ASCII, "中"]
]


@dataclass(frozen=True)
class Run:
    """A run of an EQ3/6 binary on the test data."""

    ## The name of the binary
    executable: str
    ## The test data files passed to the binary, relative to `EQ36_DATA_DIR`
    inputs: list[str]
    ## The extensions of the files that the binary writes
    extensions: list[str]


## A run of each binary
RUNS = [
    Run("eqpt", ["eqpt/1kb.d0"], [".d1", ".d1f", ".po", ".s"]),
    Run("eq3nr", ["eqpt/cmp.d1", "eq3nr/cmp/acidmwb.3i"], [".3o", ".3p"]),
    Run("eq6", ["eqpt/cmp.d1", "eq6/cmp/crisqtz.6i"], [".6o", ".6p", ".6tx"]),
]


def copy_inputs(inputs: list[str], stem: str, directory: Path) -> list[str]:
    """
    Copy test data files into a directory, renaming each to `stem` with its original extension.

    @param inputs    The paths of the files, relative to `EQ36_DATA_DIR`
    @param stem      The stem of the copied files
    @param directory The directory into which the files are copied

    @return The names of the copied files, in the order of `inputs`
    """
    names: list[str] = []
    for name in inputs:
        source = EQ36_DATA_DIR / name
        copied = f"{stem}{source.suffix}"
        _ = shutil.copy(source, directory / copied)
        names.append(copied)
    return names
