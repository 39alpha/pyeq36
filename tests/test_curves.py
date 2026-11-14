"""
Test the temperature-pressure curve `eq36.curves.TPCurve`.

@todo Test the cases that remain untested, each noted by a `@todo` in
      `eq36.data1`:
      - a root that `np.roots` returns with a tiny imaginary part, e.g. where
        the curve touches an edge of the rectangle from outside
        (`find_boundary_intersections`, `set_domain`);
      - a temperature bound of the rectangle lying just outside the domain, by
        rounding (`find_boundary_intersections`);
      - an endpoint that touches the rectangle only to within rounding, and is
        the curve's only contact with it (`set_domain`);
      - a temperature just outside the domain, by rounding, passed to
        `__call__`, or sampled by `sample` so that no curve contains it
        (`temperature_in_domain`);
      - a crossing at `mid` on a curve whose pieces differ there by more than
        the tolerances of `find_boundary_intersections` but less than those of
        the continuity check in `__init__`;
      - overriding `atol` and `rtol`, once they are properties of the class
        with per-method overrides, including in `set_domain`.
@todo Add Hypothesis tests, reusing `domain_cases` where possible, for:
      - `find_boundary_intersections`: every point returned lies in the
        domain, inside the rectangle and on its boundary (at a temperature
        bound, or with the pressure at a pressure bound), and the points are
        sorted and distinct;
      - `__init__` and `__call__`: any continuous curve can be constructed,
        evaluating it agrees with `evaluate` throughout the domain, and
        evaluating it outside the domain raises a `ValueError`;
      - `set_domain`: restricting an already-restricted curve gives the same
        result as restricting a fresh one;
      - `sample`, with a real random number generator: the requested number
        of samples is drawn, every temperature lies in `union_domains`, every
        selected curve's domain contains its temperature, and every pressure
        is the selected curve evaluated there.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, TypeAlias, cast

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from numpy.polynomial import polynomial

from eq36.curves import TPCurve, _merge_intervals

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from eq36.typing import Array1D, FloatRange

## The type of the pressure polynomials of a `TPCurve`
Pressure: TypeAlias = "tuple[Array1D[np.float64], Array1D[np.float64]]"


def temperatures() -> dict[str, np.float64]:
    """
    Construct the bounding temperatures, `0`, `5` and `10`, used by the curves in these tests.

    @return The bounding temperatures, keyed by `"min"`, `"mid"` and `"max"`
    """
    return {"min": np.float64(0.0), "mid": np.float64(5.0), "max": np.float64(10.0)}


def constant_curve(domain: list[FloatRange] | None = None) -> TPCurve:
    """
    Construct a curve with a constant pressure of `1` on `[0, 10]`.

    @param domain The domain to which the curve is restricted, if any

    @return The curve
    """
    curve = TPCurve(temperatures(), (np.array([1.0]), np.array([1.0])))
    if domain is not None:
        curve.domain = domain
    return curve


def interval(lower: float, upper: float) -> FloatRange:
    """
    Construct a temperature or pressure interval.

    @param lower The lower bound
    @param upper The upper bound

    @return The interval
    """
    return (np.float64(lower), np.float64(upper))


@pytest.mark.parametrize(
    ("temperature", "pressure", "match"),
    [
        (
            {"min": np.float64(0.0), "max": np.float64(10.0)},
            (np.array([1.0]), np.array([1.0])),
            "must have min, mid and max",
        ),
        (temperatures(), (np.array([1.0]),), "not enough values to unpack"),
        (temperatures(), (np.array([]), np.array([1.0])), "no coefficients"),
        (temperatures(), (np.array([1.0]), np.array([2.0])), "differ at the common temperature"),
        (
            {"min": np.float64(5.0), "mid": np.float64(0.0), "max": np.float64(10.0)},
            (np.array([1.0]), np.array([1.0])),
            "min <= mid <= max",
        ),
        (
            {"min": np.float64(0.0), "mid": np.float64(10.0), "max": np.float64(5.0)},
            (np.array([1.0]), np.array([1.0])),
            "min <= mid <= max",
        ),
    ],
    ids=["missing-mid", "one-polynomial", "empty-polynomial", "discontinuous", "mid-below-min", "max-below-mid"],
)
def test_init_rejects_invalid_arguments(temperature: object, pressure: object, match: str) -> None:
    """
    Ensure that `TPCurve` raises a `ValueError` for invalid temperatures or polynomials.

    @param temperature The bounding temperatures
    @param pressure    The pressure polynomials
    @param match       A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = TPCurve(cast("dict[str, np.float64]", temperature), cast("Pressure", pressure))


@pytest.mark.parametrize(
    "dot_results",
    [[1.0, np.float64(1.0)], [np.float64(1.0), 1.0]],
    ids=["left", "right"],
)
def test_init_requires_float64_evaluations(mocker: MockerFixture, dot_results: list[object]) -> None:
    """
    Ensure that `TPCurve` raises a `TypeError` if either polynomial does not evaluate to an `np.float64`.

    @param mocker      The pytest-mock mocker fixture
    @param dot_results The successive results of `np.dot`
    """
    _ = mocker.patch("numpy.dot", side_effect=dot_results)
    with pytest.raises(TypeError):
        _ = constant_curve()


def test_reset_domain_returns_curve() -> None:
    """Ensure that `reset_domain` restores the full domain and returns the curve."""
    curve = constant_curve([interval(1.0, 2.0)])
    assert curve.reset_domain() is curve
    assert curve.domain == [interval(0.0, 10.0)]


@pytest.mark.parametrize(("temperature", "expected"), [(1.0, True), (20.0, False)])
def test_temperature_in_domain(temperature: float, *, expected: bool) -> None:
    """
    Ensure that `temperature_in_domain` determines whether a temperature is in the domain.

    @param temperature The temperature to check
    @param expected    Whether the temperature is in the domain
    """
    assert constant_curve().temperature_in_domain(np.float64(temperature)) is expected


@pytest.mark.parametrize(("temperature", "pressure"), [(0.0, 2.0), (10.0, 12.0)])
def test_call_evaluates_polynomial(temperature: float, pressure: float) -> None:
    """
    Ensure that calling a curve evaluates its polynomial.

    @param temperature The temperature at which to evaluate the curve
    @param pressure    The expected pressure
    """
    curve = TPCurve(temperatures(), (np.array([2.0, 1.0]), np.array([2.0, 1.0])))
    assert curve(np.float64(temperature)) == np.float64(pressure)


def test_call_rejects_temperature_outside_domain() -> None:
    """Ensure that calling a curve raises a `ValueError` for a temperature outside of its domain."""
    with pytest.raises(ValueError, match="not in the restricted domain"):
        _ = constant_curve()(np.float64(99.0))


def test_call_requires_float64_evaluation(mocker: MockerFixture) -> None:
    """
    Ensure that calling a curve raises a `TypeError` if the polynomial does not evaluate to an `np.float64`.

    @param mocker The pytest-mock mocker fixture
    """
    curve = constant_curve()
    _ = mocker.patch("numpy.dot", return_value=1.0)
    with pytest.raises(TypeError):
        _ = curve(np.float64(1.0))


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((interval(0.0, 3.0), interval(0.0, 2.0)), (interval(1.0, 2.0), interval(0.0, 2.0))),
        ((interval(0.0, 3.0), interval(0.0, 2.0)), (interval(0.0, 10.0), interval(0.0, 2.0))),
        ((interval(0.0, 10.0), interval(5.0, 6.0)), (interval(0.0, 10.0), interval(0.0, 2.0))),
        ((interval(0.0, 3.0), interval(0.0, 2.0)), (interval(5.0, 8.0), interval(0.0, 2.0))),
        ((interval(0.0, 3.0), interval(0.0, 2.0)), (interval(0.0, 10.0), interval(5.0, 6.0))),
    ],
    ids=["narrower", "wider", "after-empty", "disjoint", "disjoint-miss"],
)
def test_set_domain_ignores_previous_restriction(
    first: tuple[FloatRange, FloatRange],
    second: tuple[FloatRange, FloatRange],
) -> None:
    """
    Ensure that `set_domain` on an already-restricted curve gives the same result as on an unrestricted one.

    The curve, a constant pressure of `1` on `[0, 10]`, is restricted to a
    first rectangle (which, for `after-empty`, it misses entirely) and then to
    a second. For `disjoint`, the second rectangle lies outside the first
    restriction but crosses the curve; for `disjoint-miss`, it misses the
    curve entirely.

    @param first  The temperature and pressure bounds of the first rectangle
    @param second The temperature and pressure bounds of the second rectangle
    """
    restricted = constant_curve()
    _ = restricted.set_domain(*first)
    unrestricted = constant_curve()

    assert restricted.set_domain(*second) == unrestricted.set_domain(*second)
    assert restricted.domain == unrestricted.domain


## The roots, `3 - sqrt(3)` and `3 + sqrt(3)`, of the pressure polynomial `-T**2 + 6*T - 6`
LOWER_ROOT, UPPER_ROOT = 3.0 - np.sqrt(3.0), 3.0 + np.sqrt(3.0)


@pytest.mark.parametrize(
    ("temperature", "expected"),
    [
        ((1.5, 4.5), [(1.5, 2.0), (4.0, 4.5)]),
        ((1.5, 5.5), [(1.5, 2.0), (4.0, UPPER_ROOT)]),
        ((0.5, 4.5), [(LOWER_ROOT, 2.0), (4.0, 4.5)]),
        ((0.5, 5.5), [(LOWER_ROOT, 2.0), (4.0, UPPER_ROOT)]),
    ],
    ids=["both-endpoints", "first-endpoint", "last-endpoint", "no-endpoints"],
)
def test_set_domain_includes_segments_at_endpoints(
    temperature: tuple[float, float],
    expected: list[tuple[float, float]],
) -> None:
    """
    Ensure that `set_domain` includes the segments between an endpoint in the rectangle and the nearest intersection.

    The curve, `p = -T**2 + 6*T - 6` (with `mid` at its peak, `T = 3`), rises
    above the rectangle `[0, 6] x [0, 2]` between `T = 2` and `T = 4`. Each
    endpoint lies either in the rectangle or below it, where the curve crosses
    `p = 0` at `LOWER_ROOT` or `UPPER_ROOT`. For `no-endpoints`, both lie below
    it, so the domain is made up only of intervals between intersections.

    @param temperature The minimum and maximum temperatures of the curve
    @param expected    The expected domain
    """
    coefficients = np.array([-6.0, 6.0, -1.0])
    temperatures = {"min": np.float64(temperature[0]), "mid": np.float64(3.0), "max": np.float64(temperature[1])}
    curve = TPCurve(temperatures, (coefficients, coefficients))

    assert curve.set_domain(interval(0.0, 6.0), interval(0.0, 2.0))
    assert len(curve.domain) == len(expected)
    for actual, bounds in zip(curve.domain, expected, strict=True):
        assert actual == pytest.approx(bounds)


@pytest.mark.parametrize(
    ("temperature", "temperature_range", "expected"),
    [
        ((2.0, 4.5), (0.0, 6.0), [(2.0, 2.0), (4.0, 4.5)]),
        ((1.5, 4.0), (0.0, 6.0), [(1.5, 2.0), (4.0, 4.0)]),
        ((2.0, 4.0), (0.0, 6.0), [(2.0, 2.0), (4.0, 4.0)]),
        ((1.5, 4.5), (1.5, 6.0), [(1.5, 2.0), (4.0, 4.5)]),
        ((1.5, 4.5), (0.0, 4.5), [(1.5, 2.0), (4.0, 4.5)]),
    ],
    ids=[
        "first-on-boundary-curve-outside",
        "last-on-boundary-curve-outside",
        "both-on-boundary-curve-outside",
        "first-on-boundary-curve-inside",
        "last-on-boundary-curve-inside",
    ],
)
def test_set_domain_includes_endpoints_on_boundary(
    temperature: tuple[float, float],
    temperature_range: tuple[float, float],
    expected: list[tuple[float, float]],
) -> None:
    """
    Ensure that `set_domain` includes an endpoint on the boundary as a single point if the curve leaves the rectangle.

    The curve, `p = -T**2 + 6*T - 6` (with `mid` at its peak, `T = 3`), is
    above the rectangle `temperature_range x [0, 2]` between `T = 2` and
    `T = 4`, where it meets the top edge. Each case names the endpoint(s) on
    the boundary and whether the curve beside them lies outside or inside the
    rectangle. An endpoint at `T = 2` or `T = 4`, beside which the curve is
    outside, touches the rectangle only at that point. An endpoint on the edge
    `T = 1.5` or `T = 4.5`, beside which the curve is inside, instead bounds an
    interval, and should not also appear as a single point.

    @param temperature       The minimum and maximum temperatures of the curve
    @param temperature_range The temperature bounds of the rectangle
    @param expected          The expected domain
    """
    coefficients = np.array([-6.0, 6.0, -1.0])
    temperatures = {"min": np.float64(temperature[0]), "mid": np.float64(3.0), "max": np.float64(temperature[1])}
    curve = TPCurve(temperatures, (coefficients, coefficients))

    assert curve.set_domain(interval(*temperature_range), interval(0.0, 2.0))
    assert len(curve.domain) == len(expected)
    for actual, bounds in zip(curve.domain, expected, strict=True):
        assert actual == pytest.approx(bounds)


## A curve: its minimum, middle and maximum temperatures, and the coefficients of its left and right polynomials
CurveSpec: TypeAlias = "tuple[tuple[float, float, float], list[float], list[float]]"


def make_curve(spec: CurveSpec) -> TPCurve:
    """
    Construct a curve from its specification.

    @param spec The minimum, middle and maximum temperatures, and the
                coefficients of the left and right polynomials

    @return The curve
    """
    (low, mid, high), left, right = spec
    temps = {"min": np.float64(low), "mid": np.float64(mid), "max": np.float64(high)}
    return TPCurve(temps, (np.array(left), np.array(right)))


## `p = 1` on `[0, 10]`
CONSTANT: CurveSpec = ((0.0, 5.0, 10.0), [1.0], [1.0])

## `p = T` on `[0, 10]`
LINEAR: CurveSpec = ((0.0, 5.0, 10.0), [0.0, 1.0], [0.0, 1.0])

## `p = -T**2 + 6*T - 6`, which peaks at `p = 3` at `T = 3`
QUADRATIC = [-6.0, 6.0, -1.0]


@pytest.mark.parametrize(
    ("spec", "temperature_range", "pressure_range", "expected"),
    [
        (CONSTANT, (20.0, 30.0), (0.0, 2.0), []),
        (CONSTANT, (0.0, 10.0), (5.0, 6.0), []),
        (CONSTANT, (-1.0, 11.0), (0.0, 2.0), [(0.0, 10.0)]),
        (CONSTANT, (5.0, 5.0), (0.0, 2.0), [(5.0, 5.0)]),
        (CONSTANT, (2.0, 8.0), (0.0, 2.0), [(2.0, 8.0)]),
        (((0.0, 5.0, 10.0), [2.0], [2.0]), (-1.0, 11.0), (0.0, 2.0), [(0.0, 10.0)]),
        (LINEAR, (-1.0, 11.0), (-1.0, 5.0), [(0.0, 5.0)]),
        (((0.0, 3.0, 10.0), [0.0, 1.0], [0.0, 1.0]), (-1.0, 11.0), (-1.0, 5.0), [(0.0, 5.0)]),
        (LINEAR, (-1.0, 5.0), (-1.0, 5.0), [(0.0, 5.0)]),
        (((0.0, 2.5, 5.0), [0.0, 1.0], [0.0, 1.0]), (-1.0, 11.0), (-1.0, 5.0), [(0.0, 5.0)]),
        (((0.0, 5.0, 10.0), [27.0, -10.0, 1.0], [27.0, -10.0, 1.0]), (-1.0, 11.0), (0.0, 2.0), [(5.0, 5.0)]),
        (((0.0, 5.0, 10.0), [0.0, 1.0], [10.0, -1.0]), (-1.0, 11.0), (-1.0, 4.0), [(0.0, 4.0), (6.0, 10.0)]),
        (((0.0, 5.0, 10.0), [0.0, 1.0], [10.0, -1.0]), (-1.0, 11.0), (-1.0, 5.0), [(0.0, 10.0)]),
        (((0.5, 1.25, 2.0), QUADRATIC, QUADRATIC), (0.0, 6.0), (0.0, 2.0), [(LOWER_ROOT, 2.0)]),
        (((4.0, 4.75, 5.5), QUADRATIC, QUADRATIC), (0.0, 6.0), (0.0, 2.0), [(4.0, UPPER_ROOT)]),
    ],
    ids=[
        "beside",
        "above",
        "inside",
        "zero-width-rectangle",
        "crosses-side-edges",
        "along-top-edge",
        "one-crossing",
        "one-crossing-mid-inside",
        "through-corner",
        "last-on-top-edge-curve-inside-one-crossing",
        "touches-top-edge-from-outside",
        "different-pieces",
        "different-pieces-touch-top-edge-at-mid",
        "last-on-top-edge-curve-inside",
        "first-on-top-edge-curve-inside",
    ],
)
def test_set_domain(
    spec: CurveSpec,
    temperature_range: tuple[float, float],
    pressure_range: tuple[float, float],
    expected: list[tuple[float, float]],
) -> None:
    """
    Ensure that `set_domain` restricts a curve to the parts inside a rectangle, merging touching intervals.

    The domain is expected to be a sorted list of disjoint intervals: pieces of
    the curve that touch or overlap, e.g. on either side of a point at which the
    curve touches the boundary from inside, form a single interval. Single
    points are kept where the curve touches the rectangle only at that point,
    but are merged into any interval that contains them.

    @param spec              The curve
    @param temperature_range The temperature bounds of the rectangle
    @param pressure_range    The pressure bounds of the rectangle
    @param expected          The expected domain
    """
    curve = make_curve(spec)

    assert curve.set_domain(interval(*temperature_range), interval(*pressure_range)) == bool(expected)
    assert len(curve.domain) == len(expected)
    for actual, bounds in zip(curve.domain, expected, strict=True):
        assert actual == pytest.approx(bounds)


## The number of temperatures at which `set_domain` is checked against the curve
GRID_SIZE = 1001

## The tolerance, relative to the scale of the curve, within which a grid point is too close to the boundary to check
BOUNDARY_TOLERANCE = 1e-6

## Polynomial coefficients: zero, as for the unused high-degree terms in data1 files, or of magnitude `1e-6` to `10`
COEFFICIENTS = st.one_of(
    st.just(0.0),
    st.floats(min_value=1e-6, max_value=10.0),
    st.floats(min_value=-10.0, max_value=-1e-6),
)

## A rectangle: its temperature bounds and its pressure bounds
Rectangle: TypeAlias = "tuple[tuple[float, float], tuple[float, float]]"


def evaluate(spec: CurveSpec, temps: Array1D[np.float64]) -> Array1D[np.float64]:
    """
    Evaluate a curve, independently of `TPCurve`, using the left polynomial up to and including `mid`.

    @param spec  The curve
    @param temps The temperatures at which to evaluate it

    @return The pressures
    """
    (_, mid, _), left, right = spec
    return np.where(temps <= mid, polynomial.polyval(temps, left), polynomial.polyval(temps, right))


@st.composite
def domain_cases(draw: st.DrawFn) -> tuple[CurveSpec, Rectangle]:
    """
    Draw a continuous curve and a rectangle around (part of) it.

    The curve's pieces are polynomials of degree at most four, with the
    constant term of the right one adjusted so that they agree at `mid`. The
    rectangle's bounds are drawn from slightly beyond the curve's temperatures
    and pressures, so that it may cross the curve, contain it or miss it.

    @param draw The Hypothesis draw function

    @return The curve and the rectangle
    """
    low = draw(st.floats(min_value=-10.0, max_value=10.0))
    width = draw(st.floats(min_value=0.1, max_value=20.0))
    high = low + width
    mid = low + width * draw(st.floats(min_value=0.0, max_value=1.0))

    coefficients = st.lists(COEFFICIENTS, min_size=1, max_size=5)
    left = draw(coefficients)
    right = draw(coefficients)
    right[0] += float(polynomial.polyval(mid, left) - polynomial.polyval(mid, right))
    spec: CurveSpec = ((low, mid, high), left, right)

    press = evaluate(spec, np.linspace(low, high, GRID_SIZE))
    temperature_bound = st.floats(min_value=low - 5.0, max_value=high + 5.0)
    pressure_bound = st.floats(min_value=float(press.min()) - 1.0, max_value=float(press.max()) + 1.0)
    temperature_range = cast("tuple[float, float]", tuple(sorted((draw(temperature_bound), draw(temperature_bound)))))
    pressure_range = cast("tuple[float, float]", tuple(sorted((draw(pressure_bound), draw(pressure_bound)))))
    return spec, (temperature_range, pressure_range)


## `p = T**2` on `[0, 3]`, which crosses `p = 3` at `T = sqrt(3)`
SQUARE: CurveSpec = ((0.0, 1.5, 3.0), [0.0, 0.0, 1.0], [0.0, 0.0, 1.0])

## The temperature-pressure curve of the `geo` database: `p = 1.0132` up to `T = 100`, then rising to about `85.8`
GEO: CurveSpec = (
    (0.0, 100.0, 300.0),
    [1.0132, 0.0, 0.0, 0.0, 0.0],
    [
        -0.43449999999946487,
        0.007632333333320295,
        5.514000000011349e-05,
        -1.2637333333337557e-06,
        1.3968000000000564e-08,
    ],
)

## `p = 0` up to `mid`, then `p = (T**2 - mid**2) / 3`
FLAT_THEN_RISING: CurveSpec = (
    (0.0, 2.604750395920054, 4.155660823455067),
    [0.0],
    [-2.261574875015226, 0.0, 0.3333333333333333],
)

## `p = 0` up to `mid = 2.875`, then `p = T**3 - 2.875**3`
FLAT_THEN_CUBIC: CurveSpec = ((-5.0, 2.875, 9.0), [0.0], [-23.763671875, 0.0, 0.0, 1.0])

## `p = 9.5` up to `mid`, then a quartic falling steeply, at a slope of about `-58000`
FLAT_THEN_STEEP: CurveSpec = (
    (0.0, 11.373728226520658, 14.0),
    [9.5],
    [165928.63230288014, 0.0, 0.0, 0.96875, -10.0],
)


@given(domain_cases())
@example((SQUARE, ((-1.0, 4.0), (0.0, 3.0))))
@example((GEO, ((0.0, 300.0), (1.0132, 5.0))))
@example((FLAT_THEN_RISING, ((-3.0, 5.0), (-1.0, 0.0))))
@example((FLAT_THEN_CUBIC, ((0.0, 3.0), (6.103515625e-05, 1.0))))
@example((FLAT_THEN_STEEP, ((0.0, 12.0), (-475.0, 0.0))))
def test_set_domain_matches_curve(case: tuple[CurveSpec, Rectangle]) -> None:
    """
    Ensure that the domain set by `set_domain` contains exactly the parts of the curve inside the rectangle.

    The domain must be sorted, disjoint intervals within `[min, max]`. On a
    dense grid of temperatures, a temperature must be in the domain if and only
    if the curve there is inside the rectangle. Grid points within
    `BOUNDARY_TOLERANCE` (relative to the scale of the curve) of the
    rectangle's boundary are skipped, since the intersections are located only
    approximately.

    The `@example`s pin crossings that `find_boundary_intersections` has
    missed:
    - `SQUARE` in `[-1, 4] x [0, 3]`: the curve leaves through the top edge at
      `T = sqrt(3)`, at which the computed pressure rounds to slightly more
      than `3`;
    - `GEO` in `[0, 300] x [1.0132, 5]`: likewise, at `T ~ 151.9`, so that the
      whole curve, which reaches `85.8`, was taken to lie in the rectangle;
    - `FLAT_THEN_RISING` in `[-3, 5] x [-1, 0]`: the curve leaves through the
      top edge exactly at `mid`, but the right polynomial's root there rounds
      to slightly less than `mid`, outside its piece;
    - `FLAT_THEN_CUBIC` in `[0, 3] x [6.1e-5, 1]`: the curve enters through the
      bottom edge about `2.5e-6` after `mid`; snapping that root onto `mid`,
      where the pressure is `0`, would move it off the boundary;
    - `FLAT_THEN_STEEP` in `[0, 12] x [-475, 0]`: the curve enters through the
      top edge at `T ~ 11.37389`, where, because of the steep slope, the
      computed pressure is `1.7e-9`, too far from `0` for the crossing to be
      kept.

    @param case The curve and the rectangle
    """
    spec, (temperature_range, pressure_range) = case
    (low, _, high), _, _ = spec
    curve = make_curve(spec)

    found = curve.set_domain(interval(*temperature_range), interval(*pressure_range))

    domain = curve.domain
    assert found == bool(domain)
    assert all(start <= stop for start, stop in domain)
    assert all(stop < start for (_, stop), (start, _) in pairwise(domain))
    assert all(low <= start and stop <= high for start, stop in domain)

    temps = np.linspace(low, high, GRID_SIZE)
    press = evaluate(spec, temps)
    temperature_tolerance = BOUNDARY_TOLERANCE * max(1.0, high - low)
    pressure_tolerance = BOUNDARY_TOLERANCE * max(1.0, float(np.max(np.abs(press))))
    for temp, pressure in zip(temps.tolist(), press.tolist(), strict=True):
        if min(abs(temp - bound) for bound in temperature_range) <= temperature_tolerance:
            continue
        if min(abs(pressure - bound) for bound in pressure_range) <= pressure_tolerance:
            continue
        inside: bool = (
            temperature_range[0] <= temp <= temperature_range[1] and pressure_range[0] <= pressure <= pressure_range[1]
        )
        in_domain = any(start <= temp <= stop for start, stop in domain)
        assert in_domain == inside, f"T = {temp}, p = {pressure}: in domain {domain} but inside rectangle is {inside}"


def test_find_boundary_intersections_includes_temperature_bounds() -> None:
    """Ensure that `find_boundary_intersections` includes the curve's crossings of the temperature bounds."""
    intersections = constant_curve().find_boundary_intersections(interval(0.0, 10.0), interval(1.0, 2.0))
    assert (0.0, 1.0) in intersections
    assert (10.0, 1.0) in intersections


def test_find_boundary_intersections_skips_temperatures_outside_domain() -> None:
    """Ensure that `find_boundary_intersections` skips temperature bounds outside of the curve's domain."""
    curve = constant_curve([interval(1.0, 2.0)])
    intersections = curve.find_boundary_intersections(interval(0.0, 2.0), interval(1.0, 1.0))
    assert all(t != 0.0 for t, _ in intersections)


def test_find_boundary_intersections_includes_right_polynomial_roots() -> None:
    """Ensure that `find_boundary_intersections` includes roots of the polynomial on `[mid, max]`."""
    curve = make_curve(((0.0, 5.0, 10.0), [0.0, 1.0], [10.0, -1.0]))
    intersections = curve.find_boundary_intersections(interval(-1.0, 11.0), interval(-1.0, 4.0))
    assert (6.0, 4.0) in intersections


@pytest.mark.parametrize(
    ("spec", "temperature_range", "pressure_range", "expected"),
    [
        (
            (
                (0.0, 5.094572997602054, 10.0),
                [2.702782177955612, -2.135042323682198, 2.6918966828234634],
                [13.004184138378308, -0.4600413061645461, 1.9662155629226508],
            ),
            (-1.0, 11.0),
            (61.69295412644422, 161.69295412644422),
            [5.094572997602054, 8.813853216147377],
        ),
        (
            (
                (0.0, 5.295776636574341, 10.0),
                [-0.29376668297165276, 2.743766203521224, 2.7249080211998544],
                [27.147641224406293, 1.02952580388422, 2.0701385494100784],
            ),
            (-1.0, 5.295776636574341),
            (-9.342666541877335, 90.65733345812266),
            [5.295776636574341],
        ),
    ],
    ids=["root-at-mid", "edge-and-root-at-mid"],
)
def test_find_boundary_intersections_removes_near_duplicates(
    spec: CurveSpec,
    temperature_range: tuple[float, float],
    pressure_range: tuple[float, float],
    expected: list[float],
) -> None:
    """
    Ensure that `find_boundary_intersections` reports a point found more than once, up to rounding, only once.

    In `root-at-mid`, a pressure bound equals the pressure at `mid`, so both
    polynomials have a root there. In `edge-and-root-at-mid`, the rectangle's
    upper temperature bound is also `mid`, so the point is found both on that
    edge and as a root. In each case the duplicates differ only in their last
    digits.

    @param spec              The curve
    @param temperature_range The temperature bounds of the rectangle
    @param pressure_range    The pressure bounds of the rectangle
    @param expected          The expected temperatures of the intersections
    """
    curve = make_curve(spec)

    intersections = curve.find_boundary_intersections(interval(*temperature_range), interval(*pressure_range))

    assert [float(temp) for temp, _ in intersections] == pytest.approx(expected)


def test_find_boundary_intersections_ignores_roots_beyond_piece() -> None:
    """
    Ensure that `find_boundary_intersections` does not report a root of a polynomial outside its piece.

    The curve rises steeply (`p = 1e6 * (T - 5) + 5`) to `p = 5` at `mid = 5`
    and then falls (`p = 10 - T`), so it never reaches the top edge `p = 7`.
    The left polynomial, continued past `mid`, reaches `p = 7` at
    `T = 5 + 2e-6`, which is close enough to `mid` to be snapped onto it, but
    the curve there is well below the edge.
    """
    curve = make_curve(((0.0, 5.0, 10.0), [-4999995.0, 1e6], [10.0, -1.0]))

    assert curve.find_boundary_intersections(interval(-1.0, 11.0), interval(-1e9, 7.0)) == []


def test_find_boundary_intersections_skips_roots_outside_domain() -> None:
    """Ensure that `find_boundary_intersections` skips roots outside of the curve's domain."""
    curve = TPCurve(temperatures(), (np.array([-2.0]), np.array([-7.0, 1.0])))
    curve.domain = [interval(0.0, 3.0)]
    assert curve.find_boundary_intersections(interval(0.0, 10.0), interval(0.0, 0.0)) == []


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        ([], []),
        ([(1.0, 2.0)], [(1.0, 2.0)]),
        ([(3.0, 4.0), (1.0, 2.0)], [(1.0, 2.0), (3.0, 4.0)]),
        ([(1.0, 2.0), (2.0, 3.0)], [(1.0, 3.0)]),
        ([(1.0, 3.0), (2.0, 4.0)], [(1.0, 4.0)]),
        ([(1.0, 4.0), (2.0, 3.0)], [(1.0, 4.0)]),
        ([(1.0, 2.0), (1.0, 2.0)], [(1.0, 2.0)]),
        ([(1.0, 3.0), (2.0, 2.0)], [(1.0, 3.0)]),
        ([(1.0, 2.0), (2.0, 2.0)], [(1.0, 2.0)]),
        ([(2.0, 2.0), (2.0, 3.0)], [(2.0, 3.0)]),
        ([(1.0, 2.0), (3.0, 3.0)], [(1.0, 2.0), (3.0, 3.0)]),
        ([(2.0, 2.0), (2.0, 2.0)], [(2.0, 2.0)]),
    ],
    ids=[
        "empty",
        "single",
        "disjoint-unsorted",
        "touching",
        "overlapping",
        "nested",
        "duplicate",
        "point-inside",
        "point-at-stop",
        "point-at-start",
        "isolated-point",
        "duplicate-points",
    ],
)
def test_merge_intervals(intervals: list[tuple[float, float]], expected: list[tuple[float, float]]) -> None:
    """
    Ensure that `_merge_intervals` merges overlapping and touching intervals, including single points.

    @param intervals The intervals to merge
    @param expected  The merged intervals
    """
    assert _merge_intervals(interval(*bounds) for bounds in intervals) == [interval(*bounds) for bounds in expected]


## Interval bounds, mixing whole numbers (so that intervals often touch or coincide) with arbitrary values
BOUNDS = st.one_of(st.integers(min_value=-20, max_value=20).map(float), st.floats(min_value=-20.0, max_value=20.0))

## Lists of closed intervals (possibly single points), in any order
INTERVALS = st.lists(st.tuples(BOUNDS, BOUNDS).map(lambda bounds: interval(*sorted(bounds))), max_size=8)


def covers(intervals: list[FloatRange], value: float) -> bool:
    """
    Determine whether any of a list of closed intervals contains a value.

    @param intervals The intervals
    @param value     The value

    @return Whether `value` lies in any of `intervals`
    """
    return any(start <= value <= stop for start, stop in intervals)


@given(INTERVALS)
def test_merge_intervals_returns_sorted_separated_intervals(intervals: list[FloatRange]) -> None:
    """
    Ensure that `_merge_intervals` returns sorted intervals separated by gaps.

    @param intervals The intervals to merge
    """
    merged = _merge_intervals(intervals)
    assert all(start <= stop for start, stop in merged)
    assert all(stop < start for (_, stop), (start, _) in pairwise(merged))


@given(INTERVALS)
def test_merge_intervals_covers_the_same_values(intervals: list[FloatRange]) -> None:
    """
    Ensure that `_merge_intervals` covers exactly the values covered by the intervals it merges.

    Both are unions of closed intervals, so it suffices to compare them at
    every bound, at every midpoint between consecutive bounds, and beyond the
    smallest and largest bounds.

    @param intervals The intervals to merge
    """
    merged = _merge_intervals(intervals)
    bounds = sorted({float(bound) for pair in intervals for bound in pair})
    values = [*bounds, *((a + b) / 2 for a, b in pairwise(bounds))]
    if bounds:
        values += [bounds[0] - 1.0, bounds[-1] + 1.0]
    for value in values:
        assert covers(merged, value) == covers(intervals, value), value


@given(INTERVALS)
def test_merge_intervals_is_independent_of_order_and_idempotent(intervals: list[FloatRange]) -> None:
    """
    Ensure that `_merge_intervals` does not depend on the order of the intervals, and leaves merged intervals unchanged.

    @param intervals The intervals to merge
    """
    merged = _merge_intervals(intervals)
    assert _merge_intervals(reversed(intervals)) == merged
    assert _merge_intervals(merged) == merged


@pytest.mark.parametrize(
    ("domains", "expected"),
    [
        ([], []),
        ([[interval(0.0, 2.0), interval(3.0, 4.0)], [interval(1.0, 3.5)]], [interval(0.0, 4.0)]),
        ([[interval(0.0, 1.0)], [interval(3.0, 4.0)]], [interval(0.0, 1.0), interval(3.0, 4.0)]),
    ],
    ids=["no-curves", "overlapping", "disjoint"],
)
def test_union_domains(domains: list[list[FloatRange]], expected: list[FloatRange]) -> None:
    """
    Ensure that `union_domains` merges overlapping subdomains and preserves disjoint ones.

    @param domains  The domains of the curves
    @param expected The expected union
    """
    assert TPCurve.union_domains([constant_curve(domain) for domain in domains]) == expected


@pytest.mark.parametrize(
    ("domains", "uniform", "temps", "selected"),
    [
        ([[interval(0.0, 2.0)]], [0.5, 1.5], [0.5, 1.5], [0, 0]),
        ([[interval(0.0, 1.0)], [interval(3.0, 4.0)]], [0.2, 1.8], [0.2, 3.8], [0, 1]),
    ],
    ids=["one-subdomain", "across-gap"],
)
def test_sample(
    mocker: MockerFixture,
    domains: list[list[FloatRange]],
    uniform: list[float],
    temps: list[float],
    selected: list[int],
) -> None:
    """
    Ensure that `sample` maps uniform draws onto the union of the domains, skipping gaps between subdomains.

    @param mocker   The pytest-mock mocker fixture
    @param domains  The domains of the curves
    @param uniform  The draws returned by the mocked `rng.uniform`
    @param temps    The expected sampled temperatures
    @param selected The indices of the curves expected to be selected
    """
    curves = [constant_curve(domain) for domain in domains]
    # Configure after creation: before Python 3.12, `create_autospec` replaces
    # children configured via keyword arguments with fresh autospecced ones.
    rng: MagicMock = mocker.create_autospec(np.random.Generator, instance=True)
    rng.configure_mock(
        **{
            "uniform.return_value": np.array(uniform),
            "integers.return_value": 0,
        }
    )

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(curves, len(uniform), rng=rng)

    assert list(sampled_temps) == temps
    assert list(sampled_presses) == [1.0] * len(uniform)
    assert len(sampled_curves) == len(selected)
    assert all(curve is curves[i] for curve, i in zip(sampled_curves, selected, strict=True))


@pytest.mark.parametrize(
    "domains",
    [
        [[interval(2.0, 2.0)], [interval(7.0, 7.0)]],
        [[interval(2.0, 2.0), interval(7.0, 7.0)]],
        [[interval(2.0, 2.0)], [interval(7.0, 7.0)], []],
    ],
    ids=["one-point-per-curve", "two-points-on-one-curve", "with-empty-domain"],
)
def test_sample_chooses_between_single_point_domains(domains: list[list[FloatRange]]) -> None:
    """
    Ensure that `sample` draws from every point if the union of the domains consists only of single points.

    The union has zero length, so the temperatures cannot be drawn by length;
    instead, each sample should come from one of the points, chosen at random.

    @param domains The domains of the curves, whose union is the points `2` and `7`
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, _, sampled_curves = TPCurve.sample(curves, 100, rng=np.random.default_rng(0))

    assert set(sampled_temps.tolist()) == {2.0, 7.0}
    assert all(
        curve.temperature_in_domain(temp) for temp, curve in zip(sampled_temps.tolist(), sampled_curves, strict=True)
    )


@pytest.mark.parametrize("num_samples", [0, 3])
@pytest.mark.parametrize("domains", [[], [[], []]], ids=["no-curves", "empty-domains"])
def test_sample_returns_nothing_to_sample(domains: list[list[FloatRange]], num_samples: int) -> None:
    """
    Ensure that `sample` returns no temperatures, pressures or curves if there is nothing to sample.

    There is nothing to sample if there are no curves, or if every curve's
    domain is empty (e.g. after `set_domain` with a rectangle that no curve
    passes through).

    @param domains     The domains of the curves
    @param num_samples The number of points to sample
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(
        curves,
        num_samples,
        rng=np.random.default_rng(0),
    )

    assert sampled_temps.size == 0
    assert sampled_presses.size == 0
    assert sampled_curves == []


@pytest.mark.parametrize(
    "domains",
    [[[interval(0.0, 10.0)]], [[interval(2.0, 2.0)], [interval(7.0, 7.0)]]],
    ids=["intervals", "single-points"],
)
def test_sample_returns_nothing_for_zero_samples(domains: list[list[FloatRange]]) -> None:
    """
    Ensure that `sample` returns no temperatures, pressures or curves if no samples are requested.

    @param domains The (non-empty) domains of the curves
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(curves, 0, rng=np.random.default_rng(0))

    assert sampled_temps.size == 0
    assert sampled_presses.size == 0
    assert sampled_curves == []
