# ruff: noqa: C901,PLR0912,PLR0915
"""
Provide the Data1 class to represent the parsed contents of a data1 file.

Also provided are the species, solid solution and temperature-pressure curve
types from which a `Data1` is built.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias, TypeVar, cast

import numpy as np
from typing_extensions import Self

from eq36.libpyeq36 import read_data1

## A closed interval `(lower, upper)`
FloatRange: TypeAlias = tuple[np.float64, np.float64]
## A point `(x, y)`, e.g. `(temperature, pressure)`
CartesianCoord: TypeAlias = tuple[np.float64, np.float64]

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from eq36.typing import Array1D


@dataclass(init=False)
class Species:
    """A named chemical species with a molar mass."""

    ## The name of the species
    name: str
    ## The molar mass (g/mol) of the species
    molar_mass: np.float64

    def __init__(self, *, name: str, molar_mass: np.float64) -> None:
        """
        Construct a `Species`.

        @param name       The (non-empty) name of the species
        @param molar_mass The (non-negative) molar mass (g/mol) of the species

        @throws ValueError if `name` is empty
        @throws ValueError if `molar_mass` is negative
        """
        self.name = name
        self.molar_mass = molar_mass

        if self.name == "":
            msg = "cannot construct Species with empty name"
            raise ValueError(msg)

        if self.molar_mass < 0:
            msg = "cannot construct Species with negative molar mass"
            raise ValueError(msg)


## A type variable bound to `Species`
SpeciesT = TypeVar("SpeciesT", bound=Species)


@dataclass(init=False)
class BasisSpecies(Species):
    """A basis species, i.e. a species from which other species are formed."""

    ## The elemental composition, mapping element names to counts
    composition: dict[str, int]
    ## The electrical charge of the species
    charge: int
    ## The molar volume of the species, if known
    volume: np.float64 | None

    def __init__(
        self,
        *,
        name: str,
        molar_mass: np.float64,
        composition: dict[str, int],
        charge: int,
        volume: np.float64 | None,
    ) -> None:
        """
        Construct a `BasisSpecies`.

        @param name        The (non-empty) name of the species
        @param molar_mass  The (non-negative) molar mass (g/mol) of the species
        @param composition The elemental composition, mapping element names to
                           (non-negative) counts
        @param charge      The electrical charge of the species
        @param volume      The (non-negative) molar volume of the species, or
                           `None` if unknown

        @throws ValueError if `name` is empty
        @throws ValueError if `molar_mass` is negative
        @throws ValueError if any count in `composition` is negative
        @throws ValueError if `volume` is negative
        """
        super().__init__(name=name, molar_mass=molar_mass)
        self.composition = composition
        self.charge = charge
        self.volume = volume

        for count in self.composition.values():
            if count < 0:
                msg = "cannot construct a BasisSpecies with a component with negative count"
                raise ValueError(msg)

        if self.volume is not None and self.volume < 0:
            msg = "cannot construct a BasisSpecies with negative volume"
            raise ValueError(msg)


@dataclass(init=False)
class AqueousSpecies(Species):
    """An aqueous species."""


@dataclass(init=False)
class Mineral(Species):
    """A pure mineral."""


@dataclass(init=False)
class Liquid(Species):
    """A pure liquid."""


@dataclass(init=False)
class Gas(Species):
    """A gas species."""


@dataclass(init=False)
class SolidSolution:
    """A solid solution and the molar masses of its end members."""

    ## The name of the solid solution
    name: str
    ## The end members, mapping end-member names to molar masses (g/mol)
    end_members: dict[str, np.float64]

    def __init__(self, *, name: str, end_members: dict[str, np.float64]) -> None:
        """
        Construct a `SolidSolution`.

        @param name        The (non-empty) name of the solid solution
        @param end_members The (non-empty) end members, mapping end-member
                           names to (non-negative) molar masses (g/mol)

        @throws ValueError if `name` is empty
        @throws ValueError if `end_members` is empty
        @throws ValueError if any end-member molar mass is negative
        """
        self.name = name
        self.end_members = end_members

        if self.name == "":
            msg = "cannot construct SolidSolution with empty name"
            raise ValueError(msg)

        if not self.end_members:
            msg = "cannot construct SolidSolution without end members"
            raise ValueError(msg)

        for molar_mass in self.end_members.values():
            if molar_mass < 0:
                msg = "cannot construct SolidSolution with negative end member molar mass"
                raise ValueError(msg)

    def molar_mass(self, mole_fractions: dict[str, np.float64]) -> np.float64:
        """
        Compute the molar mass of the solid solution for a given composition.

        The result is the average of the end-member molar masses weighted by
        `mole_fractions`. Each fraction is divided by the sum of the fractions
        before weighting, so they need not sum to one.

        @param mole_fractions The mole fraction of every end member, mapping
                              end-member names to (finite, non-negative)
                              fractions

        @return The weighted-average molar mass (g/mol)

        @throws ValueError if `mole_fractions` is empty
        @throws KeyError   if `mole_fractions` names an unknown end member
        @throws KeyError   if `mole_fractions` omits any end member
        @throws ValueError if any mole fraction is not finite (NaN or infinite)
        @throws ValueError if any mole fraction is negative
        @throws ValueError if the mole fractions sum to a non-finite value
                (i.e. the sum overflows)
        @throws ValueError if the mole fractions do not sum to a positive value
        """
        if not mole_fractions:
            msg = "no mole_fractions provided"
            raise ValueError(msg)

        missing = set(mole_fractions) - set(self.end_members)
        if missing:
            msg = f"unknown end member(s) for solid solution {self.name!r}: {sorted(missing)}"
            raise KeyError(msg)

        missing = set(self.end_members) - set(mole_fractions)
        if missing:
            msg = f"missing mole fractions for end member(s) for solid solution {self.name!r}: {sorted(missing)}"
            raise KeyError(msg)

        for end_member, fraction in mole_fractions.items():
            if not np.isfinite(fraction):
                msg = f"mole fraction for solid solution {self.name!r} end member {end_member!r} is not finite"
                raise ValueError(msg)

            if fraction < 0.0:
                msg = f"mole fraction for solid solution {self.name!r} end member {end_member!r} is negative"
                raise ValueError(msg)

        with np.errstate(over="ignore"):
            total = sum(mole_fractions.values())

        if not np.isfinite(total):
            msg = f"mole fractions for solid solution {self.name!r} must sum to a finite value"
            raise ValueError(msg)
        if total <= 0:
            msg = f"mole fractions for solid solution {self.name!r} must sum to a positive value"
            raise ValueError(msg)

        molar_mass = np.float64(0.0)
        for name, fraction in mole_fractions.items():
            molar_mass += (fraction / total) * self.end_members[name]
        return molar_mass


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


@dataclass
class Data1:
    """The parsed contents of a data1 file."""

    ## The path of the data1 file
    filename: Path
    ## The chemical elements, mapping element names to atomic weights
    elements: dict[str, np.float64]
    ## The (strict) basis species, keyed by name
    basis_species: dict[str, BasisSpecies]
    ## The aqueous species (including the basis species), keyed by name
    aqueous_species: dict[str, AqueousSpecies]
    ## The pure minerals, keyed by name
    minerals: dict[str, Mineral]
    ## The pure liquids, keyed by name
    liquids: dict[str, Liquid]
    ## The gas species, keyed by name
    gases: dict[str, Gas]
    ## The solid solutions, keyed by name
    solid_solutions: dict[str, SolidSolution]
    ## The standard grid pressure as a function of temperature
    tp_curve: TPCurve | None

    def get_basis_species(self, element: str) -> BasisSpecies | None:
        """
        Get the basis species whose composition includes an element.

        `H` and `O` appear in many basis species (e.g. `H2O`), so for these
        elements only basis species consisting solely of the element (e.g. `H+`
        and `O2(g)`) are considered.

        @param element The name of the element

        @return The basis species containing `element`, or `None` if there is
                none; for `H` and `O`, `None` if no basis species consists
                solely of `element`

        @throws ValueError if more than one basis species contains `element`
                (for `H` and `O`, consists solely of `element`)
        """
        basis_species = [
            species
            for species in self.basis_species.values()
            if element in species.composition and (element not in {"H", "O"} or len(species.composition) == 1)
        ]

        if len(basis_species) > 1:
            msg = f"data1 file contains multiple basis species for element {element}"
            raise ValueError(msg)

        return None if not basis_species else basis_species[0]

    def molar_mass(
        self,
        name: str,
        mole_fractions: dict[str, np.float64] | None = None,
    ) -> np.float64:
        """
        Get the molar mass of a species or phase in the data file.

        `name` is looked up, in order, among the solid solutions, aqueous
        species, pure minerals, pure liquids, and finally gases; the first match
        is used. For a solid solution, the molar mass is computed with
        `SolidSolution.molar_mass`.

        @param name           The name of the species or phase
        @param mole_fractions The end-member mole fractions; required if
                              `name` is a solid solution

        @return The molar mass (g/mol)

        @throws ValueError if `name` is a solid solution and `mole_fractions`
                is `None`
        @throws ValueError if `name` is not a solid solution and
                `mole_fractions` is not `None`
        @throws KeyError   if `name` is not found
        @throws ValueError if `SolidSolution.molar_mass` raises `ValueError`
        @throws KeyError   if `SolidSolution.molar_mass` raises `KeyError`
        """
        if name in self.solid_solutions:
            if mole_fractions is None:
                msg = "mole_fractions is required to get the molar_mass of a solid solution"
                raise ValueError(msg)
            return self.solid_solutions[name].molar_mass(mole_fractions)

        for category in (self.aqueous_species, self.minerals, self.liquids, self.gases):
            if name in category:
                if mole_fractions is not None:
                    msg = f"mole_fractions is only allowed for solid solutions; {name!r} is not one"
                    raise ValueError(msg)
                return category[name].molar_mass

        msg = f"no species named {name!r} in {self.filename}"
        raise KeyError(msg)

    def compute_molar_mass(self, composition: dict[str, int]) -> np.float64:
        """
        Compute a molar mass from an elemental composition.

        This uses the atomic weights read from the data1 file, which is useful
        for species not present in the data file or for cross-checking
        `molar_mass`.

        @param composition The composition, mapping element names to
                           (non-negative) counts

        @return The molar mass (g/mol)

        @throws ValueError if `composition` is empty
        @throws KeyError   if `composition` contains an unknown element
        @throws ValueError if any count is negative
        """
        if not composition:
            msg = "composition must contain at least one element"
            raise ValueError(msg)

        total = np.float64(0.0)
        for element, count in composition.items():
            if element not in self.elements:
                msg = f"unknown element {element!r}"
                raise KeyError(msg)
            if count < 0:
                msg = f"{element!r} has negative count"
                raise ValueError(msg)
            total += np.float64(count) * self.elements[element]
        return total

    @classmethod
    def from_file(cls, filename: str | Path) -> Self:
        """
        Read and parse a data1 file.

        The file is read with `eq36.libpyeq36.read_data1`, after which:
        - `tp_curve` is constructed from the minimum temperature, the maxima of
          the first two temperature ranges, and the first two columns of the
          pressure coefficients;
        - the aqueous species, minerals, liquids and gases are taken from the
          corresponding index ranges of the species arrays (an empty
          dictionary if either index is non-positive), keeping the first 24
          characters of each name;
        - the basis species are the leading species whose corresponding entry
          of `cdrsa` is zero, with their compositions taken from `nessra`,
          `nessa` and `cessa`, and a zero volume treated as unknown; entries
          for the null element (index 0), which EQ3/6 assigns to species
          composed of no elements (e.g. `e-`), are skipped, leaving such a
          species with an empty composition;
        - the solid solutions are assembled from the end-member index range (an
          empty dictionary if either index is non-positive), with the
          end-member name in the first 24 characters of the species name and
          the solid-solution name in the remainder.

        @param filename The path to the data1 file

        @return The parsed data file

        @throws RuntimeError if `read_data1` fails
        @throws RuntimeError if a solid-solution end member occurs more than
                once
        @throws ValueError   if any constructed `TPCurve`, species or solid
                solution is invalid
        @throws TypeError    if any data read has an unexpected type
        """
        filename = Path(filename)

        data = read_data1(filename)

        temp: dict[str, np.float64] = {
            "min": data.min_temperature,
            "mid": data.max_temperature_range[0],
            "max": data.max_temperature_range[1],
        }
        press = (data.pressure_coefficients[:, 0], data.pressure_coefficients[:, 1])
        tp_curve = TPCurve(temp, press)

        element_names: list[str] = []
        elements: dict[str, np.float64] = {}
        for raw_name_obj, weight in zip(
            cast("list[object]", list(data.element_names)),
            data.atomic_weights,
            strict=True,
        ):
            if not isinstance(raw_name_obj, bytes):
                raise TypeError(raw_name_obj)
            name = str(raw_name_obj.strip(), "ascii")
            element_names.append(name)
            elements[name] = weight

        def _species_name(idx: int) -> str:
            """
            Get the name of a species, i.e. the first 24 characters of its entry.

            @private

            @param idx The 0-based index of the species

            @return The species name, stripped of whitespace

            @throws TypeError if the entry is not `bytes`
            """
            raw = cast("object", data.species_names[idx])
            if not isinstance(raw, bytes):
                raise TypeError(raw)
            return str(raw[:24].strip(), "ascii")

        def _make_species(
            start: np.int32,
            stop: np.int32,
            factory: Callable[..., SpeciesT],
        ) -> dict[str, SpeciesT]:
            """
            Construct the species in a 1-based, inclusive index range.

            @private

            @param start   The 1-based index of the first species
            @param stop    The 1-based index of the last species
            @param factory The species type to construct

            @return The species, keyed by name; empty if `start` or `stop` is
                    non-positive

            @throws TypeError  if a molar mass or name has an unexpected type
            @throws ValueError if `factory` rejects a species
            """
            result: dict[str, SpeciesT] = {}
            if int(start) <= 0 or int(stop) <= 0:
                return result
            for idx in range(int(start) - 1, int(stop)):
                weight = cast("object", data.species_molar_weights[idx])
                if not isinstance(weight, np.float64):
                    raise TypeError(weight)
                name = _species_name(idx)
                result[name] = factory(name=name, molar_mass=weight)
            return result

        aqueous_species = _make_species(data.narn1a, data.narn2a, AqueousSpecies)
        minerals = _make_species(data.nmrn1a, data.nmrn2a, Mineral)
        liquids = _make_species(data.nlrn1a, data.nlrn2a, Liquid)
        gases = _make_species(data.ngrn1a, data.ngrn2a, Gas)

        basis_species: dict[str, BasisSpecies] = {}
        for i, (raw_species_name_obj, c, charge, volume) in enumerate(
            zip(
                cast("list[object]", list(data.species_names)),
                data.cdrsa,
                data.charges,
                data.volumes,
                strict=False,
            ),
        ):
            if not isinstance(raw_species_name_obj, bytes):
                raise TypeError(raw_species_name_obj)

            if c != 0:
                break
            name = str(raw_species_name_obj[0:24].strip(), "ascii")
            a = int(cast("np.int32", data.nessra[0, i]))
            b = int(cast("np.int32", data.nessra[1, i]))
            indices = cast("Array1D[np.int32]", data.nessa[a - 1 : b])
            counts = cast("list[object]", list(data.cessa[a - 1 : b]))
            selected = [
                (element_names[jdx - 1], count)
                for idx, count in zip(indices, counts, strict=True)
                if (jdx := int(idx)) != 0
            ]

            composition: dict[str, int] = {}
            for element, count in selected:
                if not isinstance(count, np.float64):
                    raise TypeError(count)
                composition[element] = int(count)
            molar_mass_obj = cast("object", data.species_molar_weights[i])
            if not isinstance(molar_mass_obj, np.float64):
                raise TypeError(molar_mass_obj)
            mass = molar_mass_obj
            resolved_volume: np.float64 | None = None if volume == 0.0 else volume
            basis_species[name] = BasisSpecies(
                name=name,
                molar_mass=mass,
                composition=composition,
                charge=int(charge),
                volume=resolved_volume,
            )

        solid_solutions: dict[str, SolidSolution] = {}
        start, stop = int(data.nxrn1a), int(data.nxrn2a)
        for i in range(start - 1, stop) if start > 0 and stop > 0 else ():
            line = cast("object", data.species_names[i])
            if not isinstance(line, bytes):
                raise TypeError(line)

            end_member = str(line[:24].strip(), "ascii")
            solid_solution = str(line[24:].strip(), "ascii")
            end_member_mass_obj = cast("object", data.species_molar_weights[i])
            if not isinstance(end_member_mass_obj, np.float64):
                raise TypeError(end_member_mass_obj)
            end_member_mass = end_member_mass_obj
            if solid_solution in solid_solutions:
                if end_member in solid_solutions[solid_solution].end_members:
                    msg = f"solid solution ({solid_solution}) end member ({end_member}) occurs multiple times"
                    raise RuntimeError(msg)
                solid_solutions[solid_solution].end_members[end_member] = end_member_mass
            else:
                solid_solutions[solid_solution] = SolidSolution(
                    name=solid_solution,
                    end_members={end_member: end_member_mass},
                )

        return cls(
            filename,
            elements,
            basis_species,
            aqueous_species,
            minerals,
            liquids,
            gases,
            solid_solutions,
            tp_curve,
        )
