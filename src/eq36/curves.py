"""Provide a basic piecewise polynomial curve type."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from eq36.typing import Array1D, FloatRange


def _format_interval(interval: FloatRange) -> str:
    """
    Format an interval for use in error messages.

    A finite bound is enclosed by a square bracket and an infinite bound by a
    parenthesis, e.g. `[0.0, inf)`.

    @private

    @param interval The lower and upper bounds of the interval

    @return The formatted interval
    """
    left, right = interval
    left_bracket = "[" if np.isfinite(left) else "("
    right_bracket = "]" if np.isfinite(right) else ")"
    return f"{left_bracket}{left}, {right}{right_bracket}"


@dataclass(init=False)
class Polynomial:
    """
    A polynomial restricted to a domain.

    The domain is a closed interval, `[x_min, x_max]`, whose bounds may be
    infinite. The polynomial cannot be evaluated outside of its domain, nor at
    an infinite value even if the domain is unbounded.
    """

    ## The bounds of the domain, `(x_min, x_max)`
    _domain: FloatRange
    ## The polynomial coefficients, in increasing order of degree
    coeffs: Array1D[np.float64]

    def __init__(
        self,
        domain: tuple[float | np.floating, float | np.floating] | None,
        coeffs: Array1D[np.float64],
    ) -> None:
        """
        Construct a polynomial from its domain and coefficients.

        The coefficients are copied into a new `np.float64` array.

        @param domain The bounds of the domain, `(x_min, x_max)`, or `None` for
                      an unbounded domain, `(-inf, inf)`
        @param coeffs The polynomial coefficients, in increasing order of
                      degree

        @throws ValueError if `coeffs` is empty
        @throws ValueError if any coefficient is not finite
        @throws ValueError if either bound of `domain` is NaN
        @throws ValueError if the bounds of `domain` are not ordered, i.e.
                `x_min > x_max`
        """
        if len(coeffs) == 0:
            msg = "polynomial has no coefficients"
            raise ValueError(msg)
        if any(not np.isfinite(c) for c in coeffs):
            msg = "polynomial has a non-finite coefficient"
            raise ValueError(msg)

        self._domain = (-np.float64(np.inf), np.float64(np.inf))
        self.domain = domain if domain is not None else (-np.inf, np.inf)
        self.coeffs = np.array(coeffs, dtype=np.float64)

    @property
    def domain(self) -> FloatRange:
        """
        Get the domain.

        @return The bounds of the domain, `(x_min, x_max)`
        """
        return self._domain

    @domain.setter
    def domain(self, domain: tuple[float | np.floating, float | np.floating]) -> None:
        """
        Set the domain.

        The domain is left unchanged if the bounds are invalid.

        @param domain The bounds of the domain, `(x_min, x_max)`, which may be
                      infinite

        @throws ValueError if either bound is NaN
        @throws ValueError if the bounds are not ordered, i.e. `x_min > x_max`
        """
        x_min, x_max = domain

        x_min = np.float64(x_min)
        x_max = np.float64(x_max)

        if np.isnan(x_min):
            msg = "x_min must be a number"
            raise ValueError(msg)
        if np.isnan(x_max):
            msg = "x_max must be a number"
            raise ValueError(msg)
        if x_min > x_max:
            msg = "bounds on the independent variable are not properly ordered (x_min > x_max)"
            raise ValueError(msg)

        self._domain = (x_min, x_max)

    def in_domain(self, x: float | np.floating) -> bool:
        """
        Determine whether a value is in the polynomial's domain.

        @param x The value to check

        @return Whether `x` is finite and lies in the (closed) domain
        """
        return bool(np.isfinite(x) and self.domain[0] <= x <= self.domain[1])

    def __call__(self, x: float | np.floating) -> np.float64:
        """
        Evaluate the polynomial at a point in its domain.

        @param x The point at which to evaluate the polynomial

        @return The value of the polynomial at `x`

        @throws ValueError if `x` is not in the domain (see `in_domain`)
        @throws ValueError if the value is not finite, e.g. if it overflows
        """
        if not self.in_domain(x):
            msg = f"the provided value ({x}) is not in the domain {_format_interval(self.domain)}"
            raise ValueError(msg)

        x = np.float64(x)
        value: np.float64 = np.dot(self.coeffs, np.pow(x, np.arange(len(self.coeffs))))
        if not np.isfinite(value):
            msg = f"the polynomial did not evaluate to a finite number at {x}"
            raise ValueError(msg)

        return value


@dataclass(init=False)
class PiecewisePolynomial:
    """
    A continuous piecewise polynomial.

    The pieces are polynomials whose domains are contiguous, i.e. each piece's
    domain ends where the next begins, and which agree where they meet.
    """

    ## The pieces, sorted by domain
    pieces: list[Polynomial]

    def __init__(self, pieces: Sequence[Polynomial]) -> None:
        """
        Construct a piecewise polynomial from its pieces.

        The pieces are copied (with `deepcopy`) and sorted by domain, so they
        may be given in any order. Pieces with zero-width domains are allowed.

        @param pieces The polynomial pieces

        @throws ValueError if `pieces` is empty
        @throws ValueError if the upper bound of a piece's domain is not equal
                to the lower bound of the next, i.e. if the domains have a gap
                or overlap
        @throws ValueError if two consecutive pieces are not close
                (`np.isclose`, with its default tolerances) at their common
                bound
        @throws ValueError if a piece cannot be evaluated at a common bound
                (see `Polynomial.__call__`), e.g. if the bound is infinite
        """
        if not pieces:
            msg = "no polynomial pieces provided"
            raise ValueError(msg)

        self.pieces = sorted(deepcopy(pieces), key=lambda p: p.domain)

        for i, (left, right) in enumerate(pairwise(self.pieces)):
            if left.domain[1] != right.domain[0]:
                msg = f"polynomials {i} and {i + 1} do not share a boundary"
                raise ValueError(msg)

            y_left, y_right = left(left.domain[1]), right(right.domain[0])
            if not np.isclose(y_left, y_right):
                msg = f"polynomials {i} and {i + 1} do not agree at their boundary"
                raise ValueError(msg)

    @property
    def domain(self) -> FloatRange:
        """
        Get the domain.

        @return The bounds of the domain, from the lower bound of the first
                piece to the upper bound of the last
        """
        return (self.pieces[0].domain[0], self.pieces[-1].domain[1])

    def in_domain(self, x: float | np.float64) -> bool:
        """
        Determine whether a value is in the piecewise polynomial's domain.

        @param x The value to check

        @return Whether `x` is in the domain of any piece (see
                `Polynomial.in_domain`)
        """
        return any(piece.in_domain(x) for piece in self.pieces)

    def __call__(self, x: float | np.float64) -> np.float64:
        """
        Evaluate the piecewise polynomial at a point in its domain.

        The first piece whose domain contains `x` is evaluated, so at a bound
        shared by two pieces the left piece is used.

        @param x The point at which to evaluate the piecewise polynomial

        @return The value of the piecewise polynomial at `x`

        @throws ValueError if `x` is not in the domain (see `in_domain`)
        @throws ValueError if the value is not finite, e.g. if it overflows
        """
        for piece in self.pieces:
            if piece.in_domain(x):
                return piece(x)

        msg = f"the provided value ({x}) is not in the domain {_format_interval(self.domain)}"
        raise ValueError(msg)
