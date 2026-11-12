"""
Test the parsed data1 file representation `eq36.data1.Data1`.

`Data1.from_file` is tested against a small, hand-built `Data` payload rather
than a data1 file by replacing `eq36.data1.read_data1`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from eq36 import data1
from eq36.data1 import AqueousSpecies, BasisSpecies, Data1, Gas, Liquid, Mineral, Species
from eq36.libpyeq36 import Data

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def payload(mocker: MockerFixture) -> Data:
    """
    Construct a small `Data` payload and make `eq36.data1.read_data1` return it.

    The payload contains one species of each kind: the basis (and aqueous)
    species `H+`, the mineral `Calcite`, the liquid `H2O(l)`, the gas `CO2(g)`
    and the end members `EM1` and `EM2` of the solid solution `SOLID1`. Tests
    may modify the payload before calling `Data1.from_file`.

    @param mocker The pytest-mock mocker fixture

    @return The payload
    """
    data = Data(
        min_temperature=np.float64(0.0),
        max_temperature_range=np.array([5.0, 10.0]),
        pressure_coefficients=np.array([[1.0, 1.0]]),
        element_names=np.array([b"H", b"O"]),
        atomic_weights=np.array([1.0, 16.0]),
        species_names=np.array(
            [
                b"H+                      ",
                b"Calcite                 ",
                b"H2O(l)                  ",
                b"CO2(g)                  ",
                b"EM1                     SOLID1",
                b"EM2                     SOLID1",
            ],
            dtype="|S48",
        ),
        species_molar_weights=np.array([1.0, 100.09, 18.0, 44.01, 50.0, 70.0]),
        cdrsa=np.array([0.0, 1.0, 1.0, 1.0, 1.0, 1.0]),
        charges=np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        volumes=np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        nessra=np.array([[1, 0, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0]], dtype=np.int32),
        nessa=np.array([1, 2], dtype=np.int32),
        cessa=np.array([2.0, 1.0]),
        narn1a=np.int32(1),
        narn2a=np.int32(1),
        nmrn1a=np.int32(2),
        nmrn2a=np.int32(2),
        nlrn1a=np.int32(3),
        nlrn2a=np.int32(3),
        ngrn1a=np.int32(4),
        ngrn2a=np.int32(4),
        nxrn1a=np.int32(5),
        nxrn2a=np.int32(6),
    )
    _ = mocker.patch.object(data1, "read_data1", return_value=data)
    return data


@pytest.fixture
def parsed(payload: Data) -> Data1:
    """
    Parse the unmodified `payload` with `Data1.from_file`.

    @param payload The payload returned by the mocked `read_data1`

    @return The parsed data
    """
    _ = payload
    return Data1.from_file("fake.d1")


def basis_species(*species: BasisSpecies) -> Data1:
    """
    Construct a `Data1` containing only hydrogen and the given basis species.

    @param species The basis species

    @return The data
    """
    return Data1(
        filename=Path("x"),
        elements={"H": np.float64(1.0)},
        basis_species={s.name: s for s in species},
        aqueous_species={s.name: AqueousSpecies(name=s.name, molar_mass=s.molar_mass) for s in species},
        minerals={},
        liquids={},
        gases={},
        solid_solutions={},
        tp_curve=None,
    )


## The basis species `H+`
H_PLUS = BasisSpecies(name="H+", molar_mass=np.float64(1.0), composition={"H": 1}, charge=1, volume=None)

## A (fictitious) second basis species containing hydrogen
H2_PLUS = BasisSpecies(name="H2+", molar_mass=np.float64(2.0), composition={"H": 2}, charge=2, volume=None)


def test_get_basis_species_finds_species() -> None:
    """Ensure that `get_basis_species` returns the basis species containing an element."""
    assert basis_species(H_PLUS).get_basis_species("H") == H_PLUS


def test_get_basis_species_prefers_species_of_only_that_element() -> None:
    """Ensure that `get_basis_species` returns the basis species consisting only of an element shared by others."""
    water = BasisSpecies(
        name="H2O",
        molar_mass=np.float64(18.0),
        composition={"H": 2, "O": 1},
        charge=0,
        volume=None,
    )
    assert basis_species(water, H_PLUS).get_basis_species("H") == H_PLUS


def test_get_basis_species_returns_none_if_missing() -> None:
    """Ensure that `get_basis_species` returns `None` if no basis species contains the element."""
    assert basis_species(H_PLUS).get_basis_species("Na") is None


def test_get_basis_species_rejects_multiple_matches() -> None:
    """Ensure that `get_basis_species` raises if more than one basis species contains the element."""
    with pytest.raises(ValueError, match="multiple basis species"):
        _ = basis_species(H_PLUS, H2_PLUS).get_basis_species("H")


def test_from_file_reads_metadata(parsed: Data1) -> None:
    """
    Ensure that `from_file` records the filename and elements, and constructs the temperature-pressure curve.

    @param parsed The parsed data
    """
    assert parsed.filename == Path("fake.d1")
    assert parsed.elements == {"H": np.float64(1.0), "O": np.float64(16.0)}
    assert parsed.tp_curve is not None


def test_from_file_reads_basis_species(parsed: Data1) -> None:
    """
    Ensure that `from_file` constructs the basis species.

    @param parsed The parsed data
    """
    assert parsed.basis_species == {
        "H+": BasisSpecies(
            name="H+",
            molar_mass=np.float64(1.0),
            composition={"H": 2, "O": 1},
            charge=1,
            volume=None,
        ),
    }


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("aqueous_species", AqueousSpecies(name="H+", molar_mass=np.float64(1.0))),
        ("minerals", Mineral(name="Calcite", molar_mass=np.float64(100.09))),
        ("liquids", Liquid(name="H2O(l)", molar_mass=np.float64(18.0))),
        ("gases", Gas(name="CO2(g)", molar_mass=np.float64(44.01))),
    ],
)
def test_from_file_reads_species(parsed: Data1, category: str, expected: Species) -> None:
    """
    Ensure that `from_file` constructs the species of each category.

    @param parsed   The parsed data
    @param category The name of the attribute holding the category
    @param expected The single species expected in the category
    """
    assert getattr(parsed, category) == {expected.name: expected}


def test_from_file_reads_solid_solutions(parsed: Data1) -> None:
    """
    Ensure that `from_file` constructs the solid solutions from their end members.

    @param parsed The parsed data
    """
    assert list(parsed.solid_solutions) == ["SOLID1"]
    assert parsed.solid_solutions["SOLID1"].end_members == {"EM1": np.float64(50.0), "EM2": np.float64(70.0)}


def test_from_file_returns_no_species_for_zero_range(payload: Data) -> None:
    """
    Ensure that `from_file` constructs no species for a category whose range starts at zero.

    @param payload The payload returned by the mocked `read_data1`
    """
    payload.narn1a = np.int32(0)
    assert Data1.from_file("fake.d1").aqueous_species == {}


def test_from_file_preserves_nonzero_basis_species_volume(payload: Data) -> None:
    """
    Ensure that `from_file` preserves a nonzero basis-species volume.

    @param payload The payload returned by the mocked `read_data1`
    """
    volume = np.float64(1.5)
    payload.volumes = np.array([volume, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert Data1.from_file("fake.d1").basis_species["H+"].volume == volume


@pytest.mark.parametrize(
    ("nessa", "cessa", "expected"),
    [
        ([0], [0.0], {}),
        ([0, 1], [0.0, 2.0], {"H": 2}),
        ([1, 0], [2.0, 0.0], {"H": 2}),
    ],
    ids=["null-only", "null-first", "null-last"],
)
def test_from_file_skips_null_element(
    payload: Data,
    nessa: list[int],
    cessa: list[float],
    expected: dict[str, int],
) -> None:
    """
    Ensure that `from_file` skips the null element (index 0) in a basis species' composition.

    @param payload  The payload returned by the mocked `read_data1`
    @param nessa    The element indices of the composition of `H+`
    @param cessa    The element counts of the composition of `H+`
    @param expected The expected composition of `H+`
    """
    payload.nessra = np.array([[1, 0, 0, 0, 0, 0], [len(nessa), 0, 0, 0, 0, 0]], dtype=np.int32)
    payload.nessa = np.array(nessa, dtype=np.int32)
    payload.cessa = np.array(cessa)
    assert Data1.from_file("fake.d1").basis_species["H+"].composition == expected


def test_from_file_rejects_duplicate_end_members(payload: Data) -> None:
    """
    Ensure that `from_file` raises a `RuntimeError` if a solid-solution end member occurs more than once.

    @param payload The payload returned by the mocked `read_data1`
    """
    payload.species_names[5] = b"EM1                     SOLID1"
    with pytest.raises(RuntimeError, match="occurs multiple times"):
        _ = Data1.from_file("fake.d1")


def disable_species_ranges(payload: Data) -> None:
    """
    Set the start of the aqueous, mineral, liquid and gas ranges to zero so that only basis species are parsed.

    @param payload The payload to modify
    """
    payload.narn1a = np.int32(0)
    payload.nmrn1a = np.int32(0)
    payload.nlrn1a = np.int32(0)
    payload.ngrn1a = np.int32(0)


## The species names, other than `H+`, of the payload
OTHER_NAMES = [
    b"Calcite                 ",
    b"H2O(l)                  ",
    b"CO2(g)                  ",
    b"EM1                     SOLID1",
    b"EM2                     SOLID1",
]

## The molar weights, other than that of `H+`, of the payload
OTHER_WEIGHTS = [np.float64(100.09), np.float64(18.0), np.float64(44.01), np.float64(50.0), np.float64(70.0)]


@pytest.mark.parametrize(
    ("field", "value", "basis_only"),
    [
        ("element_names", ["H", b"O"], False),
        ("species_names", [123, OTHER_NAMES[3], OTHER_NAMES[4]], False),
        ("species_names", [456, *OTHER_NAMES], True),
        ("species_names", [b"H+                      ", *OTHER_NAMES[:4], 456], False),
        ("species_molar_weights", [42, *OTHER_WEIGHTS], False),
        ("species_molar_weights", [42, *OTHER_WEIGHTS], True),
        ("species_molar_weights", [np.float64(1.0), *OTHER_WEIGHTS[:3], 42, OTHER_WEIGHTS[4]], False),
    ],
    ids=[
        "element-name",
        "species-name",
        "basis-species-name",
        "solid-solution-name",
        "species-weight",
        "basis-species-weight",
        "solid-solution-weight",
    ],
)
def test_from_file_rejects_unexpected_types(
    payload: Data, field: str, value: list[object], *, basis_only: bool
) -> None:
    """
    Ensure that `from_file` raises a `TypeError` if a name is not `bytes` or a molar weight is not an `np.float64`.

    @param payload    The payload returned by the mocked `read_data1`
    @param field      The name of the payload field to replace
    @param value      The (object array) replacement, containing one value of an unexpected type
    @param basis_only Whether to disable all but the basis species, so that the basis-species loop reads the value
    """
    setattr(payload, field, np.array(value, dtype=object))
    if basis_only:
        disable_species_ranges(payload)
    with pytest.raises(TypeError):
        _ = Data1.from_file("fake.d1")


def test_from_file_rejects_non_float64_composition_counts(payload: Data) -> None:
    """
    Ensure that `from_file` raises a `TypeError` if a composition count is not an `np.float64`.

    @param payload The payload returned by the mocked `read_data1`
    """
    payload.cessa = np.array([2, 1])
    with pytest.raises(TypeError):
        _ = Data1.from_file("fake.d1")


@pytest.mark.parametrize(
    ("name", "expected"),
    [("H+", 1.0), ("Calcite", 100.09), ("H2O(l)", 18.0), ("CO2(g)", 44.01), ("EM1", 50.0)],
)
def test_molar_mass(parsed: Data1, name: str, expected: float) -> None:
    """
    Ensure that `molar_mass` finds species of every category, and solid-solution end members.

    @param parsed   The parsed data
    @param name     The name of the species
    @param expected The expected molar mass
    """
    assert parsed.molar_mass(name) == np.float64(expected)


def test_molar_mass_of_solid_solution(parsed: Data1) -> None:
    """
    Ensure that `molar_mass` computes the molar mass of a solid solution from its mole fractions.

    @param parsed The parsed data
    """
    mass = parsed.molar_mass("SOLID1", {"EM1": np.float64(0.25), "EM2": np.float64(0.75)})
    assert mass == np.float64(0.25 * 50.0 + 0.75 * 70.0)


def test_molar_mass_of_solid_solution_requires_mole_fractions(parsed: Data1) -> None:
    """
    Ensure that `molar_mass` raises a `ValueError` for a solid solution without mole fractions.

    @param parsed The parsed data
    """
    with pytest.raises(ValueError, match="mole_fractions is required"):
        _ = parsed.molar_mass("SOLID1")


@pytest.mark.parametrize("name", ["H+", "Calcite", "EM1"])
def test_molar_mass_rejects_mole_fractions_for_non_solid_solution(parsed: Data1, name: str) -> None:
    """
    Ensure that `molar_mass` raises a `ValueError` if mole fractions are given for anything but a solid solution.

    @param parsed The parsed data
    @param name   The name of a species or end member that is not a solid solution
    """
    with pytest.raises(ValueError, match="only allowed for solid solutions"):
        _ = parsed.molar_mass(name, {"EM1": np.float64(0.25), "EM2": np.float64(0.75)})


def test_molar_mass_rejects_unknown_species(parsed: Data1) -> None:
    """
    Ensure that `molar_mass` raises a `KeyError` for an unknown species.

    @param parsed The parsed data
    """
    with pytest.raises(KeyError, match="no species named"):
        _ = parsed.molar_mass("Unknown")


def test_compute_molar_mass(parsed: Data1) -> None:
    """
    Ensure that `compute_molar_mass` sums the atomic weights of a composition.

    @param parsed The parsed data
    """
    assert parsed.compute_molar_mass({"H": 2, "O": 1}) == np.float64(18.0)


@pytest.mark.parametrize(
    ("composition", "error", "match"),
    [
        ({}, ValueError, "at least one element"),
        ({"Xe": 1}, KeyError, "unknown element"),
        ({"H": -1}, ValueError, "negative count"),
    ],
    ids=["empty", "unknown-element", "negative-count"],
)
def test_compute_molar_mass_rejects_invalid_composition(
    parsed: Data1,
    composition: dict[str, int],
    error: type[Exception],
    match: str,
) -> None:
    """
    Ensure that `compute_molar_mass` raises for an invalid composition.

    @param parsed      The parsed data
    @param composition The composition
    @param error       The expected type of exception
    @param match       A pattern matching the expected error message
    """
    with pytest.raises(error, match=match):
        _ = parsed.compute_molar_mass(composition)
