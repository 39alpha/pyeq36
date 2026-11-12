# ruff: noqa: C901,PLR0912,PLR0915
"""
Provide the Data1 class to represent the parsed contents of a data1 file.

Also provided are the species, solid solution and temperature-pressure curve
types from which a `Data1` is built.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    from collections.abc import Callable

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
        `mole_fractions`. The fractions are normalized by their sum, so they
        need not sum to one.

        @param mole_fractions The mole fraction of every end member, mapping
                              end-member names to (non-negative) fractions

        @return The weighted-average molar mass (g/mol)

        @throws ValueError if `mole_fractions` is empty
        @throws KeyError   if `mole_fractions` names an unknown end member
        @throws KeyError   if `mole_fractions` omits any end member
        @throws ValueError if any mole fraction is negative
        @throws ValueError if the mole fractions do not sum to a positive value

        @todo NaN mole fractions pass the negativity and sum checks
              (`nan < 0.0` and `nan <= 0` are both false) and yield a NaN
              result.
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
            if fraction < 0.0:
                msg = f"mole fraction for solid solution {self.name!r} end member {end_member!r} is negative"
                raise ValueError(msg)

        total = sum(mole_fractions.values())
        if total <= 0:
            msg = f"mole fractions for solid solution {self.name!r} must sum to a positive value"
            raise ValueError(msg)

        weighted = np.float64(0.0)
        for name, fraction in mole_fractions.items():
            weighted += fraction * self.end_members[name]
        return weighted / total


@dataclass(init=False)
class TPCurve:
    """
    A piecewise-polynomial pressure curve as a function of temperature.

    The curve consists of two polynomials, one on `[min, mid]` and one on
    `[mid, max]`, which must agree at `mid`. The curve can be restricted to a
    `domain`, a list of closed temperature intervals, outside of which it
    cannot be evaluated.
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
        @throws ValueError if either polynomial has no coefficients
        @throws ValueError if `press` does not contain exactly two polynomials
        @throws TypeError  if evaluating either polynomial at `mid` does not
                produce an `np.float64`
        @throws ValueError if the polynomials are not close (`np.isclose`) at
                `mid`

        @todo The ordering `min <= mid <= max` is not checked.
        """
        if not ("min" in temp and "mid" in temp and "max" in temp):
            msg = "temperature dictionary must have min, mid and max keys"
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

        The intersections of the curve with the boundary of the rectangle are
        found with `find_boundary_intersections`, and the domain is replaced
        based on their number:
        - **none**: the domain is `[min, max]` if both endpoints of the curve
          are in the rectangle, and empty if neither is;
        - **one**: the domain is made up of the intervals between the
          intersection and each of `min`, `mid` and `max` that is in the
          rectangle, or the single point of intersection if none are;
        - **two or more**: the domain is made up of the intervals between
          consecutive intersections whose midpoint is in the rectangle.

        @param temperature_range The temperature bounds of the rectangle
        @param pressure_range    The pressure bounds of the rectangle

        @return `False` if there are no intersections and neither endpoint is
                in the rectangle, `True` otherwise

        @throws Exception  if there are no intersections and exactly one
                endpoint is in the rectangle
        @throws ValueError if a temperature evaluated is outside of the current
                domain (see todo)

        @todo The search and evaluations use the current domain, so calling
              this on an already-restricted curve can raise `ValueError` (e.g.
              when evaluating at `min` or `max`). Consider calling
              `reset_domain` first or documenting that callers must.
        @todo With two or more intersections, a segment between an endpoint
              of the curve lying inside the rectangle and the first (or last)
              intersection is not included in the domain.
        @todo The return value is `True` whenever there are intersections,
              even if the resulting domain is empty. Consider returning
              `bool(self.domain)`.
        @todo Raises a bare `Exception`; consider a more specific type.
        """
        temp_min, temp_max = temperature_range
        press_min, press_max = pressure_range

        intersections = self.find_boundary_intersections(temperature_range, pressure_range)

        domain: list[FloatRange] = []
        not_empty = True
        if len(intersections) == 0:
            endpoints = 0
            for temp in [self.temperature["min"], self.temperature["max"]]:
                press = self(temp)
                if temp_min <= temp <= temp_max and press_min <= press <= press_max:
                    endpoints += 1

            if endpoints == 0:
                not_empty = False
            elif endpoints == 1:
                msg = "expected to find intersections or both points inside/outside region"
                raise Exception(msg)
            else:
                domain = [(self.temperature["min"], self.temperature["max"])]
        elif len(intersections) == 1:
            ((temp_intersect, _),) = intersections
            is_single_point = True
            for temp in [self.temperature["min"], self.temperature["mid"], self.temperature["max"]]:
                if temp == temp_intersect or not (temp_min <= temp <= temp_max):
                    continue

                press = self(temp)
                if press_min <= press <= press_max:
                    domain.append((min(temp, temp_intersect), max(temp, temp_intersect)))
                    is_single_point = False

            if is_single_point:
                domain.append((temp_intersect, temp_intersect))
        else:
            for i in range(len(intersections) - 1):
                temp_1, _ = intersections[i]
                temp_2, _ = intersections[i + 1]
                press = self((temp_1 + temp_2) / 2)
                if press_min <= press <= press_max:
                    domain.append((temp_1, temp_2))

        self.domain = domain

        return not_empty

    def find_boundary_intersections(
        self,
        temperature_range: FloatRange,
        pressure_range: FloatRange,
    ) -> list[CartesianCoord]:
        """
        Find the points at which the curve meets the boundary of a T-P rectangle.

        Both the vertical edges (the curve evaluated at the bounds of
        `temperature_range`) and the horizontal edges (the real roots of each
        polynomial minus each bound of `pressure_range`, restricted to that
        polynomial's piece) are considered. Only points in the current domain
        and inside the (closed) rectangle are kept.

        @param temperature_range The temperature bounds of the rectangle
        @param pressure_range    The pressure bounds of the rectangle

        @return The distinct `(temperature, pressure)` intersections, sorted,
                with pressures given by evaluating the curve

        @throws RuntimeError if the curve has more than two polynomials (which
                `__init__` prevents)

        @todo The walrus `press := self(temp)` in the root comprehension
              rebinds the enclosing loop variable `press`, so the second
              polynomial's roots are computed against the last evaluated
              pressure rather than the bound itself. These typically differ
              only by rounding, but the binding is fragile.
        @todo Roots at `mid` can be found by both polynomials, yielding
              near-duplicate points that `set` does not remove.
        """
        temp_min, temp_max = temperature_range
        press_min, press_max = pressure_range

        intersections = [
            (temp, press)
            for temp in temperature_range
            if self.temperature_in_domain(temp) and press_min <= (press := self(temp)) <= press_max
        ]

        for press in pressure_range:
            for i, coefficients in enumerate(self.pressure):
                if i == 0:
                    temp_bounds = self.temperature["min"], self.temperature["mid"]
                elif i == 1:
                    temp_bounds = self.temperature["mid"], self.temperature["max"]
                else:
                    # This should never raise as __init__ ensures that len(self.pressure) == 2
                    msg = "temperature-pressure curve has more than two domains"
                    raise RuntimeError(msg)

                coeff = np.copy(coefficients)
                # NOTE: The slice here deals with the fact that `ndarray.__getitem__` with an int is
                #       typed `Any`. Without the slice, we get a type error.
                #
                #       An alternative is to use a cast: `coeff[0] = cast(np.float64, coeff[0]) - press`
                coeff[:1] -= press
                roots = np.roots(coeff[::-1])
                real_roots: Array1D[np.float64] = np.asarray(np.real(roots[np.isreal(roots)]), dtype=np.float64)

                intersections.extend(
                    (temp, press)
                    for temp in real_roots
                    if temp_min <= temp <= temp_max
                    and temp_bounds[0] <= temp <= temp_bounds[1]
                    and self.temperature_in_domain(temp)
                    and press_min <= (press := self(temp)) <= press_max
                )

        return sorted(set(intersections))

    @staticmethod
    def union_domains(curves: list[TPCurve]) -> list[FloatRange]:
        """
        Compute the union of the domains of a collection of curves.

        Overlapping and touching intervals are merged.

        @param curves The curves whose domains are combined

        @return The disjoint intervals making up the union, sorted
        """
        subdomains = [subdomain for curve in curves for subdomain in curve.domain]
        subdomains = sorted(set(subdomains))

        if len(subdomains) == 0:
            return subdomains

        domain: list[FloatRange] = []
        (start, stop), *_rest = subdomains
        for i in range(1, len(subdomains)):
            (a, b) = subdomains[i]
            if a <= stop < b:
                stop = b
            elif stop < b:
                domain.append((start, stop))
                start, stop = a, b

        domain.append((start, stop))

        return domain

    @classmethod
    def sample(
        cls, curves: list[TPCurve], num_samples: int, *, rng: np.random.Generator | None = None
    ) -> tuple[Array1D[np.float64], Array1D[np.float64], list[TPCurve]]:
        """
        Sample points uniformly at random from a collection of curves.

        Temperatures are drawn uniformly from the union of the curves'
        domains (see `union_domains`). For each temperature, one of the curves
        whose domain contains it is chosen uniformly at random and evaluated
        to give the pressure.

        @param curves      The curves from which to sample
        @param num_samples The number of points to sample
        @param rng         The (keyword-only) random number generator; a new
                           `np.random.default_rng()` is used if `None`

        @return The sampled temperatures, the corresponding pressures, and the
                curve selected for each sample

        @throws IndexError if the union of the domains is empty

        @todo Single-point subdomains have zero length and so are never
              sampled.
        @todo `cls` is only used to call the static `union_domains`; this
              could be a `staticmethod`.
        """
        if rng is None:
            rng = np.random.default_rng()

        domain = cls.union_domains(curves)
        domain_size = sum(s[1] - s[0] for s in domain)
        steps = [domain[i + 1][0] - domain[i][1] for i in range(len(domain) - 1)]

        temps: Array1D[np.float64] = rng.uniform(0, domain_size, num_samples) + domain[0][0]
        presses: list[np.float64] = []
        selected_curves: list[TPCurve] = []
        for i in range(len(temps)):
            temp = cast("np.float64", temps[i])
            for j, subdomain in enumerate(domain):
                if subdomain[1] >= temp:
                    break
                temp += steps[j]
            temps[i] = temp

            curves_above = [curve for curve in curves if curve.temperature_in_domain(temp)]
            selected_index = rng.integers(0, len(curves_above))
            selected_curve = curves_above[selected_index]

            press = selected_curve(temp)
            presses.append(press)

            selected_curves.append(selected_curve)

        return temps, np.asarray(presses), selected_curves


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
        Get the molar mass of a species, phase or end member in the data file.

        `name` is looked up, in order, among the solid solutions, aqueous
        species, pure minerals, pure liquids, gases and finally solid-solution
        end members; the first match is used. For a solid solution, the molar
        mass is computed with `SolidSolution.molar_mass`.

        @param name           The name of the species, solid solution or end
                              member
        @param mole_fractions The end-member mole fractions; required if
                              `name` is a solid solution, and ignored otherwise

        @return The molar mass (g/mol)

        @throws ValueError if `name` is a solid solution and `mole_fractions`
                is `None`
        @throws KeyError   if `name` is not found
        @throws ValueError if `SolidSolution.molar_mass` raises `ValueError`
        @throws KeyError   if `SolidSolution.molar_mass` raises `KeyError`

        @todo `mole_fractions` is silently ignored when `name` is not a solid
              solution; consider raising instead.
        """
        if name in self.solid_solutions:
            if mole_fractions is None:
                msg = "mole_fractions is required to get the molar_mass of a solid solution"
                raise ValueError(msg)
            return self.solid_solutions[name].molar_mass(mole_fractions)
        for category in (self.aqueous_species, self.minerals, self.liquids, self.gases):
            if name in category:
                return category[name].molar_mass
        for solid_solution in self.solid_solutions.values():
            if name in solid_solution.end_members:
                return solid_solution.end_members[name]
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
        - the solid solutions are assembled from the end-member index range,
          with the end-member name in the first 24 characters of the species
          name and the solid-solution name in the remainder.

        @param filename The path to the data1 file

        @return The parsed data file

        @throws RuntimeError if `read_data1` fails
        @throws RuntimeError if a solid-solution end member occurs more than
                once
        @throws ValueError   if any constructed `TPCurve`, species or solid
                solution is invalid
        @throws TypeError    if any data read has an unexpected type

        @todo The basis species are identified by indexing `cdrsa` (the
              flattened reaction coefficients) by species index. This works
              only because each strict basis species has a single, zero
              coefficient; using `ndrsra` would be more robust.
        @todo Element counts and charges are truncated with `int()`, so
              non-integer values are silently changed.
        @todo Only the first two temperature ranges are used for `tp_curve`,
              so for data files with more ranges (e.g. `1kb`, `2kb` and `5kb`
              in `eq36/test/data/eqpt`) the curve ends at the second range's
              maximum and omits the remaining polynomials (see
              `tests/test_data1_eqpt.py`). `TPCurve` itself supports exactly
              two polynomials.
        @todo `tp_curve` is annotated `TPCurve | None`, but is never `None`.
        @todo Unlike `_make_species`, the solid-solution loop does not guard
              against non-positive indices; e.g. `nxrn1a == nxrn2a == 0`
              would read the last species.
        @todo Species with duplicate names within a category silently
              overwrite each other.
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
        for i in range(int(data.nxrn1a) - 1, int(data.nxrn2a)):
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
