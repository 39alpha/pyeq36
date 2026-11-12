"""Provide type aliases."""

from typing import TypeVar

import numpy as np
from typing_extensions import TypeAliasType

## A generic type variable representing a numpy scalar
ScalarT = TypeVar("ScalarT", bound=np.generic)

## A type alias for a 1-D numpy array
Array1D = TypeAliasType("Array1D", np.ndarray[tuple[int], np.dtype[ScalarT]], type_params=(ScalarT,))

## A type alias for a 2-D numpy array
Array2D = TypeAliasType("Array2D", np.ndarray[tuple[int, int], np.dtype[ScalarT]], type_params=(ScalarT,))

__all__ = [
    "Array1D",
    "Array2D",
    "ScalarT",
]
