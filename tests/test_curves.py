"""Test the polynomial types `eq36.curves.Polynomial` and `eq36.curves.PiecewisePolynomial`."""

from __future__ import annotations

from bisect import bisect_left
from itertools import pairwise
from typing import TYPE_CHECKING

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from numpy.polynomial import polynomial

from eq36.curves import PiecewisePolynomial, Polynomial, _format_interval

if TYPE_CHECKING:
    from random import Random

    from eq36.typing import FloatRange

## Positive infinity
INF = float("inf")

## Not a number
NAN = float("nan")


def poly(domain: tuple[float, float] | None, *coeffs: float) -> Polynomial:
    """
    Construct a polynomial.

    @param domain The bounds of the domain, or `None` for an unbounded domain
    @param coeffs The polynomial coefficients, in increasing order of degree

    @return The polynomial
    """
    return Polynomial(domain, np.array(coeffs, dtype=np.float64))


def interval(lower: float, upper: float) -> FloatRange:
    """
    Construct an interval.

    @param lower The lower bound
    @param upper The upper bound

    @return The interval
    """
    return (np.float64(lower), np.float64(upper))


@pytest.mark.parametrize(
    ("bounds", "expected"),
    [
        ((0.0, 1.0), "[0.0, 1.0]"),
        ((-INF, 1.0), "(-inf, 1.0]"),
        ((0.0, INF), "[0.0, inf)"),
        ((-INF, INF), "(-inf, inf)"),
    ],
    ids=["finite", "unbounded-below", "unbounded-above", "unbounded"],
)
def test_format_interval(bounds: tuple[float, float], expected: str) -> None:
    """
    Ensure that `_format_interval` closes finite bounds and opens infinite ones.

    @param bounds   The bounds of the interval
    @param expected The formatted interval
    """
    assert _format_interval(interval(*bounds)) == expected


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ((0.0, 1.0), (0.0, 1.0)),
        ((1.0, 1.0), (1.0, 1.0)),
        ((-INF, INF), (-INF, INF)),
        (None, (-INF, INF)),
    ],
    ids=["finite", "zero-width", "infinite", "none"],
)
def test_init_sets_domain(domain: tuple[float, float] | None, expected: tuple[float, float]) -> None:
    """
    Ensure that the domain is set from the given bounds, and is unbounded if none are given.

    @param domain   The bounds of the domain, or `None`
    @param expected The expected bounds
    """
    p = poly(domain, 1.0)
    assert p.domain == expected
    assert all(isinstance(bound, np.float64) for bound in p.domain)


def test_init_copies_coefficients() -> None:
    """Ensure that the coefficients are copied into a new `np.float64` array."""
    coeffs = np.array([1, 2, 3])
    p = Polynomial(None, coeffs)
    coeffs[0] = 99
    assert p.coeffs.dtype == np.float64
    assert p.coeffs.tolist() == [1.0, 2.0, 3.0]


@pytest.mark.parametrize(
    ("domain", "coeffs", "match"),
    [
        ((0.0, 1.0), [], "no coefficients"),
        ((0.0, 1.0), [1.0, NAN], "non-finite coefficient"),
        ((0.0, 1.0), [INF], "non-finite coefficient"),
        ((0.0, 1.0), [1.0, -INF], "non-finite coefficient"),
        ((NAN, 1.0), [1.0], "x_min must be a number"),
        ((0.0, NAN), [1.0], "x_max must be a number"),
        ((1.0, 0.0), [1.0], "not properly ordered"),
    ],
    ids=["empty", "nan-coefficient", "inf-coefficient", "negative-inf-coefficient", "nan-min", "nan-max", "unordered"],
)
def test_init_rejects_invalid_arguments(domain: tuple[float, float], coeffs: list[float], match: str) -> None:
    """
    Ensure that `Polynomial` raises a `ValueError` for invalid coefficients or domains.

    @param domain The bounds of the domain
    @param coeffs The polynomial coefficients
    @param match  A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = poly(domain, *coeffs)


def test_domain_setter_updates_domain() -> None:
    """Ensure that setting the domain replaces it."""
    p = poly((0.0, 1.0), 1.0)
    p.domain = (2.0, INF)
    assert p.domain == (2.0, INF)


@pytest.mark.parametrize(
    ("domain", "match"),
    [((NAN, 1.0), "x_min"), ((0.0, NAN), "x_max"), ((2.0, 1.0), "not properly ordered")],
    ids=["nan-min", "nan-max", "unordered"],
)
def test_domain_setter_rejects_invalid_bounds(domain: tuple[float, float], match: str) -> None:
    """
    Ensure that setting invalid bounds raises a `ValueError` and leaves the domain unchanged.

    @param domain The invalid bounds
    @param match  A pattern matching the expected error message
    """
    p = poly((0.0, 1.0), 1.0)
    with pytest.raises(ValueError, match=match):
        p.domain = domain
    assert p.domain == (0.0, 1.0)


@pytest.mark.parametrize(
    ("domain", "x", "expected"),
    [
        ((0.0, 1.0), 0.5, True),
        ((0.0, 1.0), 0.0, True),
        ((0.0, 1.0), 1.0, True),
        ((0.0, 1.0), -0.5, False),
        ((0.0, 1.0), 1.5, False),
        ((1.0, 1.0), 1.0, True),
        ((0.0, 1.0), NAN, False),
        (None, NAN, False),
        (None, INF, False),
        (None, -INF, False),
        (None, 1e300, True),
    ],
    ids=[
        "interior",
        "lower-bound",
        "upper-bound",
        "below",
        "above",
        "zero-width",
        "nan",
        "nan-unbounded",
        "inf-unbounded",
        "negative-inf-unbounded",
        "large-unbounded",
    ],
)
def test_in_domain(domain: tuple[float, float] | None, x: float, *, expected: bool) -> None:
    """
    Ensure that `in_domain` accepts finite values in the closed domain, and nothing else.

    @param domain   The bounds of the domain, or `None`
    @param x        The value to check
    @param expected Whether `x` is in the domain
    """
    assert poly(domain, 1.0).in_domain(x) is expected


@pytest.mark.parametrize(
    ("coeffs", "x", "expected"),
    [
        ([3.0], 2.0, 3.0),
        ([2.0, 1.0], 3.0, 5.0),
        ([1.0, -2.0, 1.0], 1.0, 0.0),
        ([0.0, 0.0, 0.0, 1.0], -2.0, -8.0),
    ],
    ids=["constant", "linear", "quadratic", "cubic"],
)
def test_call_evaluates_polynomial(coeffs: list[float], x: float, expected: float) -> None:
    """
    Ensure that calling a polynomial evaluates it.

    @param coeffs   The polynomial coefficients
    @param x        The point at which to evaluate the polynomial
    @param expected The expected value
    """
    value = poly(None, *coeffs)(x)
    assert isinstance(value, np.float64)
    assert value == expected


def test_call_does_not_overflow_integers() -> None:
    """Ensure that evaluating a polynomial at a Python `int` does not overflow `int64`."""
    p = poly(None, *([0.0] * 8), 1.0)
    assert p(1000) == p(1000.0) == pytest.approx(1e24)


@pytest.mark.parametrize(
    ("domain", "x", "match"),
    [
        ((0.0, 1.0), 2.0, r"\(2.0\) is not in the domain \[0.0, 1.0\]"),
        (None, INF, r"\(inf\) is not in the domain \(-inf, inf\)"),
        (None, NAN, r"\(nan\) is not in the domain \(-inf, inf\)"),
    ],
    ids=["outside", "inf", "nan"],
)
def test_call_rejects_value_outside_domain(domain: tuple[float, float] | None, x: float, match: str) -> None:
    """
    Ensure that calling a polynomial raises a `ValueError` for a value outside of its domain.

    @param domain The bounds of the domain, or `None`
    @param x      The value at which to evaluate the polynomial
    @param match  A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = poly(domain, 1.0)(x)


def test_call_rejects_non_finite_value() -> None:
    """Ensure that calling a polynomial raises a `ValueError` if its value overflows."""
    with pytest.raises(ValueError, match="did not evaluate to a finite number"), pytest.warns(RuntimeWarning):
        _ = poly(None, 0.0, 0.0, 1.0)(1e200)


@pytest.mark.parametrize(
    ("pieces", "match"),
    [
        ([], "no polynomial pieces"),
        ([poly((0.0, 1.0), 1.0), poly((2.0, 3.0), 1.0)], "polynomials 0 and 1 do not share a boundary"),
        ([poly((0.0, 2.0), 1.0), poly((1.0, 3.0), 1.0)], "polynomials 0 and 1 do not share a boundary"),
        (
            [poly((0.0, 1.0), 1.0), poly((1.0, 2.0), 1.0), poly((2.0, 3.0), 2.0)],
            "polynomials 1 and 2 do not agree",
        ),
        ([poly((0.0, INF), 1.0), poly((INF, INF), 1.0)], "not in the domain"),
    ],
    ids=["empty", "gap", "overlap", "discontinuous", "infinite-boundary"],
)
def test_piecewise_init_rejects_invalid_pieces(pieces: list[Polynomial], match: str) -> None:
    """
    Ensure that `PiecewisePolynomial` raises a `ValueError` for missing, non-contiguous or discontinuous pieces.

    @param pieces The polynomial pieces
    @param match  A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = PiecewisePolynomial(pieces)


def test_piecewise_init_sorts_pieces() -> None:
    """Ensure that the pieces are sorted by domain."""
    pp = PiecewisePolynomial([poly((2.0, 3.0), 3.0), poly((0.0, 1.0), 0.0, 1.0), poly((1.0, 2.0), -1.0, 2.0)])
    assert [piece.domain for piece in pp.pieces] == [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)]


def test_piecewise_init_copies_pieces() -> None:
    """Ensure that the pieces are copied, so that changing the originals does not affect the piecewise polynomial."""
    left, right = poly((0.0, 1.0), 1.0), poly((1.0, 2.0), 1.0)
    pp = PiecewisePolynomial([left, right])
    left.coeffs[0] = 99.0
    right.domain = (5.0, 6.0)
    assert pp.pieces[0].coeffs.tolist() == [1.0]
    assert pp.pieces[1].domain == (1.0, 2.0)


def test_piecewise_init_accepts_zero_width_pieces() -> None:
    """Ensure that pieces with zero-width domains are accepted."""
    pp = PiecewisePolynomial([poly((0.0, 1.0), 1.0), poly((1.0, 1.0), 1.0), poly((1.0, 2.0), 1.0)])
    assert pp.domain == (0.0, 2.0)
    assert pp(1.0) == 1.0


def test_piecewise_init_accepts_unbounded_pieces() -> None:
    """Ensure that the outermost pieces may be unbounded."""
    pp = PiecewisePolynomial([poly((0.0, INF), 0.0, 1.0), poly((-INF, 0.0), 0.0, -1.0)])
    assert pp.domain == (-INF, INF)
    assert [pp(-2.0), pp(2.0)] == [2.0, 2.0]


@pytest.mark.parametrize(
    ("x", "expected"),
    [(-0.5, False), (0.0, True), (1.0, True), (1.5, True), (2.0, True), (2.5, False), (NAN, False)],
)
def test_piecewise_in_domain(x: float, *, expected: bool) -> None:
    """
    Ensure that `in_domain` determines whether a value lies in the domain of any piece.

    @param x        The value to check
    @param expected Whether `x` is in the domain
    """
    pp = PiecewisePolynomial([poly((0.0, 1.0), 1.0), poly((1.0, 2.0), 1.0)])
    assert pp.in_domain(x) is expected


def test_piecewise_call_evaluates_containing_piece() -> None:
    """Ensure that calling a piecewise polynomial evaluates the piece whose domain contains the value."""
    pp = PiecewisePolynomial([poly((0.0, 1.0), 0.0, 1.0), poly((1.0, 2.0), 2.0, -1.0)])
    assert [pp(0.5), pp(1.5)] == [0.5, 0.5]


def test_piecewise_call_uses_left_piece_at_boundary() -> None:
    """Ensure that the left piece is evaluated at a boundary shared by two pieces."""
    pp = PiecewisePolynomial([poly((0.0, 1.0), 1.0), poly((1.0, 2.0), 1.0 + 1e-9)])
    assert pp(1.0) == 1.0


def test_piecewise_call_rejects_value_outside_domain() -> None:
    """Ensure that calling a piecewise polynomial raises a `ValueError` for a value outside of its domain."""
    pp = PiecewisePolynomial([poly((0.0, 1.0), 1.0), poly((1.0, 2.0), 1.0)])
    with pytest.raises(ValueError, match=r"\(3.0\) is not in the domain \[0.0, 2.0\]"):
        _ = pp(3.0)


## Polynomial coefficients of moderate magnitude
COEFFICIENTS = st.lists(st.floats(min_value=-10.0, max_value=10.0), min_size=1, max_size=5)

## Points of moderate magnitude
POINTS = st.floats(min_value=-5.0, max_value=5.0)


@given(COEFFICIENTS, POINTS)
def test_call_matches_polyval(coeffs: list[float], x: float) -> None:
    """
    Ensure that calling a polynomial agrees with `numpy.polynomial.polynomial.polyval`.

    @param coeffs The polynomial coefficients
    @param x      The point at which to evaluate the polynomial
    """
    scale = sum(abs(c) * abs(x) ** k for k, c in enumerate(coeffs))
    expected = float(polynomial.polyval(x, coeffs))
    assert float(poly(None, *coeffs)(x)) == pytest.approx(expected, rel=0.0, abs=1e-12 * (1.0 + scale))


@given(st.tuples(POINTS, POINTS).map(sorted), POINTS)
def test_call_is_defined_exactly_on_domain(bounds: list[float], x: float) -> None:
    """
    Ensure that a polynomial can be evaluated in its domain, and raises a `ValueError` outside of it.

    @param bounds The bounds of the domain
    @param x      The point at which to evaluate the polynomial
    """
    lower, upper = bounds
    p = poly((lower, upper), 1.0)
    assert p.in_domain(x) is (lower <= x <= upper)
    if lower <= x <= upper:
        assert p(x) == 1.0
    else:
        with pytest.raises(ValueError, match="not in the domain"):
            _ = p(x)


@st.composite
def piecewise_cases(draw: st.DrawFn) -> tuple[list[float], list[Polynomial]]:
    """
    Draw the breakpoints and pieces of a continuous piecewise polynomial.

    Each piece's coefficients are drawn freely, after which its constant term
    is shifted so that it agrees with the previous piece at their common bound.

    @param draw The Hypothesis draw function

    @return The sorted breakpoints, and the pieces in sorted order
    """
    breaks = sorted(draw(st.lists(POINTS, min_size=2, max_size=6, unique=True)))
    pieces: list[Polynomial] = []
    for lower, upper in pairwise(breaks):
        coeffs = draw(COEFFICIENTS)
        if pieces:
            shift = pieces[-1](lower) - poly((lower, upper), *coeffs)(lower)
            coeffs = [float(coeffs[0] + shift), *coeffs[1:]]
        pieces.append(poly((lower, upper), *coeffs))
    return breaks, pieces


@given(piecewise_cases(), st.randoms(use_true_random=False), POINTS)
def test_piecewise_evaluates_piece_containing_point(
    case: tuple[list[float], list[Polynomial]],
    rng: Random,
    x: float,
) -> None:
    """
    Ensure that a piecewise polynomial evaluates the piece containing a point, whatever the order of its pieces.

    The pieces are shuffled before construction, and at a bound shared by two
    pieces the left piece is expected.

    @param case   The breakpoints and pieces
    @param rng    A random number generator, used to shuffle the pieces
    @param x      The point at which to evaluate the piecewise polynomial
    """
    breaks, pieces = case
    shuffled = list(pieces)
    rng.shuffle(shuffled)
    pp = PiecewisePolynomial(shuffled)

    assert [piece.domain for piece in pp.pieces] == [piece.domain for piece in pieces]
    assert pp.domain == (breaks[0], breaks[-1])
    assert pp.in_domain(x) is (breaks[0] <= x <= breaks[-1])
    if pp.in_domain(x):
        piece = pieces[max(bisect_left(breaks, x) - 1, 0)]
        assert pp(x) == piece(x)
    else:
        with pytest.raises(ValueError, match="not in the domain"):
            _ = pp(x)
