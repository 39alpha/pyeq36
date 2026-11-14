"""Provide type aliases."""

from typing import TypeAlias, TypeVar

import numpy as np
from typing_extensions import TypeAliasType

## A generic type variable representing a numpy scalar
ScalarT = TypeVar("ScalarT", bound=np.generic)

## A type alias for a 1-D numpy array
Array1D = TypeAliasType("Array1D", np.ndarray[tuple[int], np.dtype[ScalarT]], type_params=(ScalarT,))

## A type alias for a 2-D numpy array
Array2D = TypeAliasType("Array2D", np.ndarray[tuple[int, int], np.dtype[ScalarT]], type_params=(ScalarT,))

## A closed interval `(lower, upper)`
FloatRange: TypeAlias = tuple[np.float64, np.float64]

## A point `(x, y)`, e.g. `(temperature, pressure)`
CartesianCoord: TypeAlias = tuple[np.float64, np.float64]


__all__ = [
    "Array1D",
    "Array2D",
    "CartesianCoord",
    "FloatRange",
    "ScalarT",
]
