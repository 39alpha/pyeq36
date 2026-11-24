"""
Provide the Data1 class to represent the parsed contents of a data1 file.

Also provided are the species, solid solution and temperature-pressure curve
types from which a `Data1` is built.

@note Importing this module imports `eq36.libpyeq36`, which loads the
      `libpyeq36` shared library, so it raises an `ImportError` if the library
      cannot be loaded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

import numpy as np
from typing_extensions import Self

from eq36.curves import PiecewisePolynomial, Polynomial
from eq36.libpyeq36 import Data, Data1Error, read_data1

if TYPE_CHECKING:
    from collections.abc import Callable


def _ascii_decode(raw: bytes, filename: Path) -> str:
    """
    Decode a name read from a data1 file as ASCII, stripped of whitespace.

    @private

    @param raw      The name, as read from the file
    @param filename The path to the data1 file, used in the error message

    @return The decoded name

    @throws eq36.libpyeq36.Data1Error if the name is not ASCII
    """
    try:
        return str(raw.strip(), "ascii")
    except UnicodeDecodeError as e:
        msg = f"{filename}: name {raw.strip()!r} is not ASCII"
        raise Data1Error(msg) from e


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
        @param molar_mass The (finite, non-negative) molar mass (g/mol) of the
                          species

        @throws ValueError if `name` is empty
        @throws ValueError if `molar_mass` is not finite (NaN or infinite)
        @throws ValueError if `molar_mass` is negative
        """
        self.name = name
        self.molar_mass = molar_mass

        if self.name == "":
            msg = "species has empty name"
            raise ValueError(msg)

        if not np.isfinite(self.molar_mass):
            msg = f"species {name!r} has non-finite molar mass"
            raise ValueError(msg)

        if self.molar_mass < 0:
            msg = f"species {name!r} has negative molar mass"
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
        @param molar_mass  The (finite, non-negative) molar mass (g/mol) of the
                           species
        @param composition The elemental composition, mapping element names to
                           (non-negative) counts
        @param charge      The electrical charge of the species
        @param volume      The (finite, non-negative) molar volume of the
                           species, or `None` if unknown

        @throws ValueError if `name` is empty
        @throws ValueError if `molar_mass` is not finite (NaN or infinite)
        @throws ValueError if `molar_mass` is negative
        @throws ValueError if any count in `composition` is negative
        @throws ValueError if `volume` is not finite (NaN or infinite)
        @throws ValueError if `volume` is negative
        """
        super().__init__(name=name, molar_mass=molar_mass)
        self.composition = composition
        self.charge = charge
        self.volume = volume

        for component, count in self.composition.items():
            if count < 0:
                msg = f"component {component!r} of basis species {self.name!r} has negative count"
                raise ValueError(msg)

        if self.volume is not None:
            if not np.isfinite(self.volume):
                msg = f"basis species {self.name!r} has non-finite volume"
                raise ValueError(msg)

            if self.volume < 0:
                msg = f"basis species {self.name!r} has negative volume"
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
                           names to (finite, non-negative) molar masses
                           (g/mol)

        @throws ValueError if `name` is empty
        @throws ValueError if `end_members` is empty
        @throws ValueError if any end-member molar mass is not finite (NaN or
                infinite)
        @throws ValueError if any end-member molar mass is negative
        """
        self.name = name
        self.end_members = end_members

        if self.name == "":
            msg = "solid solution has empty name"
            raise ValueError(msg)

        if not self.end_members:
            msg = f"solid solution {self.name!r} has no end members"
            raise ValueError(msg)

        for end_member_name, molar_mass in self.end_members.items():
            if not np.isfinite(molar_mass):
                msg = f"end member {end_member_name!r} of solid solution {self.name!r} has non-finite molar mass"
                raise ValueError(msg)

            if molar_mass < 0:
                msg = f"end member {end_member_name!r} of solid solution {self.name!r} has negative molar mass"
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
        @throws ValueError if `mole_fractions` names an unknown end member
        @throws ValueError if `mole_fractions` omits any end member
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
            raise ValueError(msg)

        missing = set(self.end_members) - set(mole_fractions)
        if missing:
            msg = f"missing mole fractions for end member(s) for solid solution {self.name!r}: {sorted(missing)}"
            raise ValueError(msg)

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


def _make_elements(data: Data, filename: Path) -> tuple[dict[str, np.float64], list[str]]:
    """
    Construct the elements of a data1 file.

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The atomic weights, keyed by element name, and the element names
            in the order in which they appear in the file (which the
            composition element indices refer to)

    @throws eq36.libpyeq36.Data1Error if an element name is not ASCII
    """
    element_names: list[str] = []
    elements: dict[str, np.float64] = {}
    for raw_name, weight in zip(data.element_names, data.atomic_weights, strict=True):
        name = _ascii_decode(raw_name, filename)
        element_names.append(name)
        elements[name] = weight
    return elements, element_names


def _make_basis_species(data: Data, element_names: list[str], filename: Path) -> dict[str, BasisSpecies]:
    """
    Construct the basis species of a data1 file.

    The basis species are the leading species whose corresponding entry of
    `reaction_coefficients` is zero. The name of each is the first 24
    characters of its entry. Its composition is read from
    `composition_ranges`, `composition_element_indices` and
    `composition_counts`, with the counts converted to integers. Entries for
    the null element (index 0), which EQ3/6 assigns to species composed of no
    elements (e.g. `e-`), are skipped, leaving such a species with an empty
    composition. A zero volume is treated as unknown (`None`).

    @private

    @param data          The contents of the data1 file, as read by
                         `read_data1`
    @param element_names The element names, in the order in which they appear
                         in the file (see `_make_elements`)
    @param filename      The path to the data1 file, used in error messages

    @return The basis species, keyed by name

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `BasisSpecies` rejects a species
    """
    basis_species: dict[str, BasisSpecies] = {}
    for i, (raw_name, charge, volume) in enumerate(zip(data.species_names, data.charges, data.volumes, strict=True)):
        if data.reaction_coefficients[i] != 0:
            break

        name = _ascii_decode(raw_name[:24], filename)

        a = int(data.composition_ranges[0, i])
        b = int(data.composition_ranges[1, i])

        indices = data.composition_element_indices[a - 1 : b]
        counts = data.composition_counts[a - 1 : b]

        composition = {
            element_names[jdx - 1]: int(count)
            for idx, count in zip(indices, counts, strict=True)
            if (jdx := int(idx)) != 0
        }

        basis_species[name] = BasisSpecies(
            name=name,
            molar_mass=data.species_molar_weights[i],
            composition=composition,
            charge=int(charge),
            volume=None if volume == 0.0 else volume,
        )

    return basis_species


def _make_species(
    data: Data,
    start: np.int32,
    stop: np.int32,
    factory: Callable[..., SpeciesT],
    filename: Path,
) -> dict[str, SpeciesT]:
    """
    Construct the species in a 1-based, inclusive index range.

    The name of each species is the first 24 characters of its entry.

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param start    The 1-based index of the first species
    @param stop     The 1-based index of the last species
    @param factory  The species type to construct
    @param filename The path to the data1 file, used in error messages

    @return The species, keyed by name; empty if `start` or `stop` is
            non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `factory` rejects a species
    """
    result: dict[str, SpeciesT] = {}
    if int(start) <= 0 or int(stop) <= 0:
        return result

    for idx in range(int(start) - 1, int(stop)):
        weight = data.species_molar_weights[idx]
        name = _ascii_decode(data.species_names[idx][:24], filename)
        result[name] = factory(name=name, molar_mass=weight)
    return result


def _make_aqueous_species(data: Data, filename: Path) -> dict[str, AqueousSpecies]:
    """
    Construct the aqueous species of a data1 file (see `_make_species`).

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The aqueous species, keyed by name; empty if either end of the aqueous
            index range is non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `AqueousSpecies` rejects a species
    """
    return _make_species(data, data.first_aqueous_index, data.last_aqueous_index, AqueousSpecies, filename)


def _make_mineral_species(data: Data, filename: Path) -> dict[str, Mineral]:
    """
    Construct the minerals of a data1 file (see `_make_species`).

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The minerals, keyed by name; empty if either end of the mineral
            index range is non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `Mineral` rejects a species
    """
    return _make_species(data, data.first_mineral_index, data.last_mineral_index, Mineral, filename)


def _make_liquid_species(data: Data, filename: Path) -> dict[str, Liquid]:
    """
    Construct the liquids of a data1 file (see `_make_species`).

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The liquids, keyed by name; empty if either end of the liquid
            index range is non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `Liquid` rejects a species
    """
    return _make_species(data, data.first_liquid_index, data.last_liquid_index, Liquid, filename)


def _make_gas_species(data: Data, filename: Path) -> dict[str, Gas]:
    """
    Construct the gases of a data1 file (see `_make_species`).

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The gases, keyed by name; empty if either end of the gas
            index range is non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `Gas` rejects a species
    """
    return _make_species(data, data.first_gas_index, data.last_gas_index, Gas, filename)


def _make_solid_solutions(data: Data, filename: Path) -> dict[str, SolidSolution]:
    """
    Construct the solid solutions of a data1 file.

    Each entry in the solid-solution index range is an end member, whose name
    is the first 24 characters of the entry and whose solid solution's name is
    the remainder.

    @private

    @param data     The contents of the data1 file, as read by `read_data1`
    @param filename The path to the data1 file, used in error messages

    @return The solid solutions, keyed by name; empty if either end of the
            solid-solution index range is non-positive

    @throws eq36.libpyeq36.Data1Error if a name is not ASCII
    @throws ValueError if `SolidSolution` rejects a solid solution
    """
    solid_solutions: dict[str, SolidSolution] = {}
    start, stop = int(data.first_solid_solution_index), int(data.last_solid_solution_index)
    for i in range(start - 1, stop) if start > 0 and stop > 0 else ():
        line = data.species_names[i]
        end_member = _ascii_decode(line[:24], filename)
        solid_solution = _ascii_decode(line[24:], filename)
        end_member_mass = data.species_molar_weights[i]
        if solid_solution in solid_solutions:
            solid_solutions[solid_solution].end_members[end_member] = end_member_mass
        else:
            solid_solutions[solid_solution] = SolidSolution(
                name=solid_solution,
                end_members={end_member: end_member_mass},
            )
    return solid_solutions


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
    tp_curve: PiecewisePolynomial | None

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
        @throws ValueError if `SolidSolution.molar_mass` rejects
                `mole_fractions`
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

        The file's temperature-pressure curve, `tp_curve`, has one polynomial
        piece per temperature range: the first spans the minimum temperature
        to the first range's maximum, and each subsequent piece spans
        consecutive range maxima.

        @param filename The path to the data1 file

        @return The parsed data file

        @throws UnicodeEncodeError if the filename cannot be encoded (see
                `read_data1`)
        @throws OSError if `read_data1` cannot open the file (see `read_data1`
                for the specific types)
        @throws eq36.libpyeq36.Data1Error if `read_data1` finds that the file
                is not a valid data1 file
        @throws eq36.libpyeq36.Data1Error if any element, species or
                solid-solution name is not ASCII
        @throws eq36.libpyeq36.Data1Error if the constructed `tp_curve` (see
                `eq36.curves.PiecewisePolynomial`), or any species or solid
                solution, is invalid; the message is that of the underlying
                `ValueError`, prefixed with the filename
        """
        filename = Path(filename)
        try:
            data = read_data1(filename)
            tp_curve = PiecewisePolynomial(
                [
                    Polynomial((data.min_temperature, data.max_temperature_range[0]), data.pressure_coefficients[:, 0]),
                    *(
                        Polynomial(tuple(data.max_temperature_range[i - 1 : i + 1]), data.pressure_coefficients[:, i])
                        for i in range(1, len(data.max_temperature_range))
                    ),
                ]
            )
            elements, element_names = _make_elements(data, filename)
            return cls(
                filename=filename,
                elements=elements,
                basis_species=_make_basis_species(data, element_names, filename),
                aqueous_species=_make_aqueous_species(data, filename),
                minerals=_make_mineral_species(data, filename),
                liquids=_make_liquid_species(data, filename),
                gases=_make_gas_species(data, filename),
                solid_solutions=_make_solid_solutions(data, filename),
                tp_curve=tp_curve,
            )
        except (UnicodeEncodeError, Data1Error):
            raise
        except ValueError as err:
            msg = f"{filename}: {err}"
            raise Data1Error(msg) from err
