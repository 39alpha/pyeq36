# ruff: noqa: C901,PLR0912,PLR0915
"""
Provide the Data1 class to represent the parsed contents of a data1 file.

Also provided are the species, solid solution and temperature-pressure curve
types from which a `Data1` is built.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

import numpy as np
from typing_extensions import Self

from eq36.curves import TPCurve
from eq36.libpyeq36 import read_data1

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
