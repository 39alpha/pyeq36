"""Test the species and solid-solution types in `eq36.data1`."""

from __future__ import annotations

import numpy as np
import pytest

from eq36.data1 import AqueousSpecies, BasisSpecies, SolidSolution


@pytest.mark.parametrize(
    ("name", "molar_mass", "match"),
    [("", 1.0, "empty name"), ("H2O", -1.0, "negative molar mass")],
    ids=["empty-name", "negative-molar-mass"],
)
def test_species_rejects_invalid_arguments(name: str, molar_mass: float, match: str) -> None:
    """
    Ensure that `Species` (via `AqueousSpecies`) raises a `ValueError` for invalid arguments.

    @param name       The name of the species
    @param molar_mass The molar mass of the species
    @param match      A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = AqueousSpecies(name=name, molar_mass=np.float64(molar_mass))


@pytest.mark.parametrize(
    ("composition", "volume", "match"),
    [
        ({"H": -1}, None, "negative count"),
        ({"H": 1}, np.float64(-1.0), "negative volume"),
    ],
    ids=["negative-count", "negative-volume"],
)
def test_basis_species_rejects_invalid_arguments(
    composition: dict[str, int],
    volume: np.float64 | None,
    match: str,
) -> None:
    """
    Ensure that `BasisSpecies` raises a `ValueError` for invalid arguments.

    @param composition The elemental composition of the species
    @param volume      The molar volume of the species
    @param match       A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = BasisSpecies(name="H+", molar_mass=np.float64(1.0), composition=composition, charge=1, volume=volume)


@pytest.mark.parametrize(
    ("name", "end_members", "match"),
    [
        ("", {"A": np.float64(1.0)}, "empty name"),
        ("SS", {}, "without end members"),
        ("SS", {"A": np.float64(-1.0)}, "negative end member molar mass"),
    ],
    ids=["empty-name", "no-end-members", "negative-molar-mass"],
)
def test_solid_solution_rejects_invalid_arguments(name: str, end_members: dict[str, np.float64], match: str) -> None:
    """
    Ensure that `SolidSolution` raises a `ValueError` for invalid arguments.

    @param name        The name of the solid solution
    @param end_members The end members of the solid solution
    @param match       A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = SolidSolution(name=name, end_members=end_members)


@pytest.fixture
def solid_solution() -> SolidSolution:
    """
    Construct a solid solution with end members `A` (40 g/mol) and `B` (60 g/mol).

    @return The solid solution
    """
    return SolidSolution(name="SS", end_members={"A": np.float64(40.0), "B": np.float64(60.0)})


@pytest.mark.parametrize(
    "mole_fractions",
    [{"A": np.float64(0.25), "B": np.float64(0.75)}, {"A": np.float64(1.0), "B": np.float64(3.0)}],
    ids=["normalized", "unnormalized"],
)
def test_solid_solution_molar_mass(solid_solution: SolidSolution, mole_fractions: dict[str, np.float64]) -> None:
    """
    Ensure that `SolidSolution.molar_mass` is the fraction-weighted mean of the end-member molar masses.

    @param solid_solution The solid solution
    @param mole_fractions The end-member mole fractions, in the ratio 1:3
    """
    assert solid_solution.molar_mass(mole_fractions) == np.float64(55.0)


@pytest.mark.parametrize(
    ("mole_fractions", "error", "match"),
    [
        ({}, ValueError, "no mole_fractions"),
        ({"A": np.float64(1.0), "C": np.float64(1.0)}, KeyError, "unknown end member"),
        ({"A": np.float64(1.0)}, KeyError, "missing mole fractions"),
        ({"A": np.float64(-0.5), "B": np.float64(1.5)}, ValueError, "is negative"),
        ({"A": np.float64(0.0), "B": np.float64(0.0)}, ValueError, "sum to a positive value"),
    ],
    ids=["empty", "unknown-end-member", "missing-end-member", "negative-fraction", "zero-sum"],
)
def test_solid_solution_molar_mass_rejects_invalid_fractions(
    solid_solution: SolidSolution,
    mole_fractions: dict[str, np.float64],
    error: type[Exception],
    match: str,
) -> None:
    """
    Ensure that `SolidSolution.molar_mass` raises for invalid mole fractions.

    @param solid_solution The solid solution
    @param mole_fractions The end-member mole fractions
    @param error          The expected type of exception
    @param match          A pattern matching the expected error message
    """
    with pytest.raises(error, match=match):
        _ = solid_solution.molar_mass(mole_fractions)
