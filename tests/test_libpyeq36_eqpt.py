"""
Test `eq36.libpyeq36.read_data1` against the `eqpt` test data.

Each data1 file is read and the raw arrays are compared with the reference
values in the corresponding `.d1f` file. Indices in the arrays are 1-based.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from eq36.libpyeq36 import Data, read_data1

from .eqpt_reference import D1F, DATA_DIR, NAME_WIDTH, REL_10SF, TOL_3DP, TOL_5DP, Species

if TYPE_CHECKING:
    import numpy as np

    from eq36.typing import Array1D


@pytest.fixture(scope="module")
def data(database: str) -> Data:
    """
    Read the database's data1 file with `read_data1`.

    @param database The name of the database

    @return The data read
    """
    return read_data1(DATA_DIR / f"{database}.d1")


def decode(names: Array1D[np.bytes_]) -> list[str]:
    """
    Decode fixed-width names, keeping only the first `NAME_WIDTH` characters.

    @param names The names

    @return The decoded names, stripped of whitespace
    """
    return [bytes(name)[:NAME_WIDTH].decode("ascii").strip() for name in names]


def species_range(first: np.int32, last: np.int32) -> slice:
    """
    Convert a 1-based, inclusive species index range into a slice.

    @param first The index of the first species
    @param last  The index of the last species

    @return The corresponding slice of the species arrays
    """
    return slice(int(first) - 1, int(last))


def test_reads_elements(data: Data, d1f: D1F) -> None:
    """
    Ensure that the element names and atomic weights are read, in order.

    @param data The data read
    @param d1f  The reference values
    """
    assert decode(data.element_names) == list(d1f.elements)
    assert data.atomic_weights.tolist() == pytest.approx(list(d1f.elements.values()), abs=TOL_5DP)


def test_reads_minimum_temperature(data: Data, d1f: D1F) -> None:
    """
    Ensure that the nominal minimum temperature is read.

    @param data The data read
    @param d1f  The reference values
    """
    assert data.min_temperature == pytest.approx(d1f.temperature_limits[0], abs=TOL_3DP)


def test_reads_range_maxima(data: Data, d1f: D1F) -> None:
    """
    Ensure that the maximum temperature of each temperature range is read.

    @param data The data read
    @param d1f  The reference values
    """
    assert data.max_temperature_range.tolist() == pytest.approx(d1f.range_maxima, abs=TOL_3DP)


def test_reads_pressure_coefficients(data: Data, d1f: D1F) -> None:
    """
    Ensure that the pressure polynomial coefficients of each range are read, padded with zeros.

    @param data The data read
    @param d1f  The reference values
    """
    size = data.pressure_coefficients.shape[0]
    expected = [coefficients + [0.0] * (size - len(coefficients)) for coefficients in d1f.pressure_coefficients]
    assert data.pressure_coefficients.T.tolist() == [pytest.approx(c, rel=REL_10SF) for c in expected]


def assert_species(data: Data, first: np.int32, last: np.int32, expected: list[Species]) -> None:
    """
    Assert that a range of species has the expected names, molecular weights and charges, in order.

    @param data     The data read
    @param first    The 1-based index of the first species in the range
    @param last     The 1-based index of the last species in the range
    @param expected The expected species
    """
    species = species_range(first, last)
    assert decode(data.species_names[species]) == [s.name for s in expected]
    assert data.species_molar_weights[species].tolist() == pytest.approx(
        [s.molar_mass for s in expected],
        abs=TOL_3DP,
    )
    assert data.charges[species].tolist() == pytest.approx([s.charge for s in expected])


def test_reads_aqueous_species(data: Data, d1f: D1F) -> None:
    """
    Ensure that the aqueous species are read, in order.

    @param data The data read
    @param d1f  The reference values
    """
    assert_species(data, data.narn1a, data.narn2a, d1f.aqueous)


def test_reads_minerals(data: Data, d1f: D1F) -> None:
    """
    Ensure that the pure minerals are read, in order.

    @param data The data read
    @param d1f  The reference values
    """
    assert_species(data, data.nmrn1a, data.nmrn2a, d1f.minerals)


def test_reads_water_as_only_liquid(data: Data, d1f: D1F) -> None:
    """
    Ensure that water, the first aqueous species, is (cloned as) the only pure liquid.

    @param data The data read
    @param d1f  The reference values
    """
    assert_species(data, data.nlrn1a, data.nlrn2a, d1f.aqueous[:1])


def test_reads_gases(data: Data, d1f: D1F) -> None:
    """
    Ensure that the gas species are read, in order.

    @param data The data read
    @param d1f  The reference values
    """
    assert_species(data, data.ngrn1a, data.ngrn2a, d1f.gases)


def test_reads_solid_solution_end_members(data: Data, d1f: D1F) -> None:
    """
    Ensure that the solid-solution end members are read, in order, with their solid solution as the phase name.

    @param data The data read
    @param d1f  The reference values
    """
    species = species_range(data.nxrn1a, data.nxrn2a)
    pairs = [
        (bytes(name)[:NAME_WIDTH].decode("ascii").strip(), bytes(name)[NAME_WIDTH:].decode("ascii").strip())
        for name in data.species_names[species]
    ]
    assert pairs == [(member, name) for name, members in d1f.solid_solutions.items() for member in members]
