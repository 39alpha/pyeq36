"""Provide a basic piecewise polynomial curve type."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, cast

import numpy as np
from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterable

    from eq36.typing import Array1D, CartesianCoord, FloatRange


def _snap(x: np.float64, bounds: FloatRange, atol: float = 1e-8, rtol: float = 1e-6) -> np.float64:
    """
    Snap a value lying just outside an interval onto the nearer bound.

    A value below the lower bound (above the upper bound) is replaced by that
    bound if the two are close (`np.isclose` with `atol` and `rtol`), e.g.
    when rounding has pushed a computed value just outside the interval.
    Values inside the interval, or far outside it, are returned unchanged.

    @private

    @param x      The value
    @param bounds The lower and upper bounds of the interval
    @param atol   The absolute tolerance passed to `np.isclose`
    @param rtol   The relative tolerance passed to `np.isclose`

    @return The bound onto which `x` is snapped, or `x` itself
    """
    if x < bounds[0] and np.isclose(x, bounds[0], atol=atol, rtol=rtol):
        return bounds[0]
    if x > bounds[1] and np.isclose(x, bounds[1], atol=atol, rtol=rtol):
        return bounds[1]
    return x


def _merge_intervals(intervals: Iterable[FloatRange]) -> list[FloatRange]:
    """
    Merge overlapping and touching closed intervals.

    Single points, `(t, t)`, are treated like any other interval: they are
    merged into an interval that contains or touches them, and kept otherwise.

    @private

    @param intervals The closed intervals, in any order

    @return The disjoint, non-touching intervals covering the same values,
            sorted
    """
    merged: list[FloatRange] = []
    for start, stop in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged


@dataclass(init=False)
class TPCurve:
    """
    A piecewise-polynomial pressure curve as a function of temperature.

    The curve consists of two polynomials, one on `[min, mid]` and one on
    `[mid, max]`, which must agree at `mid`. The curve can be restricted to a
    `domain`, a list of closed temperature intervals, outside of which it
    cannot be evaluated.

    @todo Rename this class to `PiecewiseCurve`.
    @todo Support more than two polynomials. Data files with more than two
          temperature ranges (e.g. `1kb`, `2kb` and `5kb` in
          `eq36/test/data/eqpt`) have one polynomial per range, so
          `Data1.from_file` keeps only the first two and the curve ends at the
          second range's maximum (see `tests/test_data1_eqpt.py`).
    """

    ## The temperatures bounding the curve's pieces, keyed by `"min"`, `"mid"`
    ## and `"max"`
    temperature: dict[str, np.float64]
    ## The polynomial coefficients, in increasing order of degree, on
    ## `[min, mid]` and `[mid, max]` respectively
    pressure: tuple[Array1D[np.float64], Array1D[np.float64]]
    ## The temperature intervals on which the curve may be evaluated
    domain: list[FloatRange]

    def __init__(self, temp: dict[str, np.float64], press: tuple[Array1D[np.float64], Array1D[np.float64]]) -> None:
        """
        Construct a `TPCurve` with an unrestricted domain, `[min, max]`.

        @param temp  The bounding temperatures, with `"min"`, `"mid"` and
                     `"max"` keys
        @param press The polynomial coefficients, in increasing order of
                     degree, on `[min, mid]` and `[mid, max]` respectively

        @throws ValueError if `temp` is missing any of `"min"`, `"mid"` or
                `"max"`
        @throws ValueError if the temperatures are not ordered, i.e. if
                `min <= mid <= max` does not hold (e.g. if any is NaN)
        @throws ValueError if either polynomial has no coefficients
        @throws ValueError if `press` does not contain exactly two polynomials
        @throws TypeError  if evaluating either polynomial at `mid` does not
                produce an `np.float64`
        @throws ValueError if the polynomials are not close (`np.isclose`, with
                its default tolerances) at `mid`

        @todo The continuity check uses `np.isclose`'s default tolerances
              (`rtol=1e-5`, `atol=1e-8`), which are looser than those of
              `find_boundary_intersections`. A root at `mid` found by the right
              polynomial is evaluated with the left one, so on a curve whose
              pieces differ at `mid` by more than the latter, that crossing
              can be rejected.
        """
        if not ("min" in temp and "mid" in temp and "max" in temp):
            msg = "temperature dictionary must have min, mid and max keys"
            raise ValueError(msg)
        if not (temp["min"] <= temp["mid"] <= temp["max"]):
            msg = "min, mid and max temperatures are not properly ordered (min <= mid <= max)"
            raise ValueError(msg)

        if any(len(coeffs) == 0 for coeffs in press):
            msg = "polynomial has no coefficients"
            raise ValueError(msg)

        self.pressure = press
        self.temperature = temp
        self.domain = []

        _ = self.reset_domain()

        [coeff_left, coeff_right] = self.pressure

        tmp_left = cast("object", np.dot(coeff_left, self.temperature["mid"] ** np.arange(len(coeff_left))))
        if not isinstance(tmp_left, np.float64):
            raise TypeError(tmp_left)
        left = tmp_left

        tmp_right = cast("object", np.dot(coeff_right, self.temperature["mid"] ** np.arange(len(coeff_right))))
        if not isinstance(tmp_right, np.float64):
            raise TypeError(tmp_right)
        right = tmp_right

        if not np.isclose(left, right):
            msg = "provided polynomials differ at the common temperature"
            raise ValueError(msg)

    def reset_domain(self) -> Self:
        """
        Reset the domain to the full temperature range, `[min, max]`.

        @return This curve
        """
        self.domain = [(self.temperature["min"], self.temperature["max"])]
        return self

    def temperature_in_domain(self, temp: np.float64) -> bool:
        """
        Determine whether a temperature is in the curve's (closed) domain.

        @param temp The temperature to check

        @return Whether `temp` is in any interval of the domain

        @todo The comparisons are exact, so a temperature that rounding has put
              just outside the domain is rejected, e.g. by `__call__`, or by
              `sample` when choosing the curves that contain a sampled
              temperature (which raises if there are none).
        """
        return any(subdomain[0] <= temp <= subdomain[1] for subdomain in self.domain)

    def __call__(self, temp: np.float64) -> np.float64:
        """
        Evaluate the curve at a temperature.

        The first polynomial is used if `temp <= mid`, the second otherwise.

        @param temp The temperature at which to evaluate the curve

        @return The pressure at `temp`

        @throws ValueError if `temp` is not in the domain
        @throws TypeError  if the evaluation does not produce an `np.float64`
        """
        if not self.temperature_in_domain(temp):
            msg = f"the provided temperature ({temp}) is not in the restricted domain {self.domain}"
            raise ValueError(msg)

        coefficients = self.pressure[0] if temp <= self.temperature["mid"] else self.pressure[1]
        value = cast("object", np.dot(coefficients, temp ** np.arange(len(coefficients))))
        if not isinstance(value, np.float64):
            raise TypeError(value)
        return value

    def set_domain(self, temperature_range: FloatRange, pressure_range: FloatRange) -> bool:
        """
        Restrict the domain to the parts of the curve inside a T-P rectangle.

        Any previous restriction is discarded: the domain is first reset to
        `[min, max]` (see `reset_domain`), so the result depends only on the
        curve and the rectangle. The temperatures at which the curve meets the
        boundary of the rectangle (found with `find_boundary_intersections`)
        and the curve's endpoints divide `[min, max]` into segments. Then:
        - each intersection, which lies on the boundary, is kept as a single
          point;
        - each endpoint is kept as a single point if it is in the rectangle;
        - each segment is kept if its midpoint is in the rectangle.

        These are merged (see `_merge_intervals`), so the domain is a sorted
        list of disjoint intervals, with single points only where the curve
        meets the rectangle at an isolated point.

        @param temperature_range The temperature bounds of the rectangle
        @param pressure_range    The pressure bounds of the rectangle

        @return Whether the resulting domain is non-empty

        @note This assumes that `find_boundary_intersections` finds every
              intersection, so that each segment lies wholly inside or wholly
              outside the rectangle. If one is missed, the midpoint of the
              segment containing it decides whether the whole segment is kept.

        @todo `find_boundary_intersections` is called with its default
              tolerances, which cannot be overridden here.
        @todo Whether an endpoint is in the rectangle is decided by exact
              comparisons, so an endpoint that touches the rectangle only to
              within rounding, and is the curve's only contact with it, is
              dropped.
        """
        _ = self.reset_domain()

        temp_min, temp_max = temperature_range
        press_min, press_max = pressure_range

        def inside(temp: np.float64) -> np.bool:
            """
            Determine whether the curve at a temperature lies in the rectangle.

            @private

            @param temp The temperature, in `[min, max]`

            @return Whether `temp` and the pressure there are within the
                    bounds of the rectangle
            """
            return temp_min <= temp <= temp_max and press_min <= self(temp) <= press_max

        intersections = self.find_boundary_intersections(temperature_range, pressure_range)
        crossings = [temp for temp, _ in intersections]
        endpoints = [self.temperature["min"], self.temperature["max"]]
        breaks = sorted(set(crossings + endpoints))

        segments = [(temp, temp) for temp in crossings]
        segments += [(temp, temp) for temp in endpoints if inside(temp)]
        segments += [(a, b) for a, b in pairwise(breaks) if inside((a + b) / 2)]

        self.domain = _merge_intervals(segments)

        return bool(self.domain)

    def find_boundary_intersections(
        self,
        temperature_range: FloatRange,
        pressure_range: FloatRange,
        *,
        atol: float = 1e-9,
        rtol: float = 1e-9,
    ) -> list[CartesianCoord]:
        """
        Find the points at which the curve meets the boundary of a T-P rectangle.

        Only temperatures in the current domain are considered. On the vertical
        edges, the curve is evaluated and kept if it is inside the rectangle.
        On the horizontal edges, the real roots of each polynomial minus the
        bound are kept if they lie within `temperature_range` and the
        polynomial's piece. Values just outside a bound, by rounding, are
        snapped onto it (see `_snap`); a root snapped onto the end of its piece
        is kept only if the curve's pressure there is close to the bound.

        @param temperature_range The temperature bounds of the rectangle
        @param pressure_range    The pressure bounds of the rectangle
        @param atol              The (keyword-only) absolute tolerance
        @param rtol              The (keyword-only) relative tolerance

        @return The distinct `(temperature, pressure)` intersections, sorted.

        @todo Roots are taken to be real only if their imaginary parts are
              exactly zero (`np.isreal`), so a root that `np.roots` returns
              with a tiny imaginary part, e.g. where the curve touches an edge,
              is missed.
        @todo The bounds of `temperature_range` are not snapped, so one lying
              just outside the domain, by rounding, is not reported.
        """
        temp_min, temp_max = temperature_range
        press_min, press_max = pressure_range

        temp_bounds = [
            (self.temperature["min"], self.temperature["mid"]),
            (self.temperature["mid"], self.temperature["max"]),
        ]

        intersections = [
            (temp, press)
            for temp in temperature_range
            if self.temperature_in_domain(temp)
            and press_min <= (press := _snap(self(temp), pressure_range, atol=atol, rtol=rtol)) <= press_max
        ]
        for i, coefficients in enumerate(self.pressure):
            for press in pressure_range:
                coeff = np.copy(coefficients)
                coeff[0] = coeff[0] - press
                roots = np.roots(coeff[::-1])
                real_roots: Array1D[np.float64] = np.asarray(np.real(roots[np.isreal(roots)]), dtype=np.float64)
                intersections.extend(
                    (t, press)
                    for temp in real_roots
                    if temp_min <= (t := _snap(temp, temp_bounds[i], atol=atol, rtol=rtol)) <= temp_max
                    and temp_bounds[i][0] <= t <= temp_bounds[i][1]
                    and self.temperature_in_domain(t)
                    and (t == temp or np.isclose(self(t), press, atol=atol, rtol=rtol))
                )

        distinct: list[CartesianCoord] = []
        for t, p in sorted(set(intersections)):
            if (
                not distinct
                or not np.isclose(t, distinct[-1][0], atol=atol, rtol=rtol)
                or not np.isclose(distinct[-1][1], p, atol=atol, rtol=rtol)
            ):
                distinct.append((t, p))

        return distinct

    @staticmethod
    def union_domains(curves: list[TPCurve]) -> list[FloatRange]:
        """
        Compute the union of the domains of a collection of curves.

        Overlapping and touching intervals, including single points, are merged
        (see `_merge_intervals`).

        @param curves The curves whose domains are combined

        @return The disjoint intervals making up the union, sorted
        """
        return _merge_intervals(subdomain for curve in curves for subdomain in curve.domain)

    @classmethod
    def sample(
        cls, curves: list[TPCurve], num_samples: int, *, rng: np.random.Generator | None = None
    ) -> tuple[Array1D[np.float64], Array1D[np.float64], list[TPCurve]]:
        """
        Sample points uniformly at random from a collection of curves.

        Temperatures are drawn uniformly from the union of the curves'
        domains (see `union_domains`). If every subdomain of every curve is a
        single point, the union has zero length, so the temperatures are
        instead drawn uniformly from those points, counted once per curve
        (a point shared by several curves is proportionally more likely). For
        each temperature, one of the curves whose domain contains it is
        chosen uniformly at random and evaluated to give the pressure.

        @param curves      The curves from which to sample
        @param num_samples The number of points to sample
        @param rng         The (keyword-only) random number generator; a new
                           `np.random.default_rng()` is used if `None`

        @return The sampled temperatures, the corresponding pressures, and the
                curve selected for each sample; all empty if there is nothing
                to sample, i.e. if `curves` is empty or every curve's domain
                is empty
        """
        if rng is None:
            rng = np.random.default_rng()

        if not curves or all(len(c.domain) == 0 for c in curves):
            return np.empty(0), np.empty(0), []

        presses: list[np.float64] = []
        selected_curves: list[TPCurve] = []

        if all(all(d[0] == d[1] for d in c.domain) for c in curves):
            discrete_temps = [d[0] for c in curves for d in c.domain]
            temps: Array1D[np.float64] = rng.choice(discrete_temps, num_samples)
        else:
            domain = cls.union_domains(curves)
            domain_size = sum(s[1] - s[0] for s in domain)
            steps = [domain[i + 1][0] - domain[i][1] for i in range(len(domain) - 1)]

            temps: Array1D[np.float64] = rng.uniform(0, domain_size, num_samples) + domain[0][0]
            for i in range(len(temps)):
                temp = cast("np.float64", temps[i])
                for j, subdomain in enumerate(domain):
                    if subdomain[1] >= temp:
                        break
                    temp += steps[j]
                temps[i] = temp

        for temp in temps:
            curves_above = [curve for curve in curves if curve.temperature_in_domain(temp)]
            selected_index = rng.integers(0, len(curves_above))
            selected_curve = curves_above[selected_index]

            press = selected_curve(temp)
            presses.append(press)

            selected_curves.append(selected_curve)

        return np.asarray(temps), np.asarray(presses), selected_curves
