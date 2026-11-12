"""Test the species and solid-solution types in `eq36.data1`."""

from __future__ import annotations

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st

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
    ("mole_fractions", "error", "match"),
    [
        ({}, ValueError, "no mole_fractions"),
        ({"A": np.float64(1.0), "C": np.float64(1.0)}, KeyError, "unknown end member"),
        ({"A": np.float64(1.0)}, KeyError, "missing mole fractions"),
        ({"A": np.float64(-0.5), "B": np.float64(1.5)}, ValueError, "is negative"),
        ({"A": np.float64(np.nan), "B": np.float64(1.0)}, ValueError, "is not finite"),
        ({"A": np.float64(np.inf), "B": np.float64(1.0)}, ValueError, "is not finite"),
        ({"A": np.float64(-np.inf), "B": np.float64(1.0)}, ValueError, "is not finite"),
        ({"A": np.float64(0.0), "B": np.float64(0.0)}, ValueError, "sum to a positive value"),
        ({"A": np.float64(1e308), "B": np.float64(1e308)}, ValueError, "sum to a finite value"),
    ],
    ids=[
        "empty",
        "unknown-end-member",
        "missing-end-member",
        "negative-fraction",
        "nan-fraction",
        "infinite-fraction",
        "negative-infinite-fraction",
        "zero-sum",
        "overflowing-sum",
    ],
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


## End-member molar masses (g/mol): zero (e.g. `e-`) or bounded away from zero
## so that the weighted sums neither underflow nor overflow
MOLAR_MASSES = st.one_of(st.just(0.0), st.floats(min_value=1e-3, max_value=1e4)).map(np.float64)

## The largest magnitude of a generated mole fraction, small enough that the
## sums cannot overflow
MAX_FRACTION = 1e6

## Positive mole fractions, bounded so that their (scaled) sums neither
## underflow nor overflow
MOLE_FRACTIONS = st.floats(min_value=1e-6, max_value=MAX_FRACTION).map(np.float64)

## End members, mapping end-member names to molar masses
END_MEMBERS = st.dictionaries(st.text(min_size=1, max_size=8), MOLAR_MASSES, min_size=1, max_size=5)


@st.composite
def compositions(
    draw: st.DrawFn,
    fractions: st.SearchStrategy[np.float64] = MOLE_FRACTIONS,
) -> tuple[SolidSolution, dict[str, np.float64]]:
    """
    Draw a solid solution and a mole fraction for each of its end members.

    @param draw      The Hypothesis draw function
    @param fractions The strategy from which each mole fraction is drawn

    @return The solid solution and its mole fractions
    """
    end_members = draw(END_MEMBERS)
    mole_fractions = {name: draw(fractions) for name in end_members}
    return SolidSolution(name="SS", end_members=end_members), mole_fractions


def tolerance(solid_solution: SolidSolution) -> float:
    """
    Get the absolute tolerance for comparing molar masses of a solid solution.

    @param solid_solution The solid solution

    @return A tolerance relative to the largest end-member molar mass
    """
    return 1e-9 * max(1.0, *(float(m) for m in solid_solution.end_members.values()))


def assert_bounded(solid_solution: SolidSolution, molar_mass: np.float64) -> None:
    """
    Assert that a molar mass lies between the smallest and largest end-member molar masses.

    @param solid_solution The solid solution
    @param molar_mass     The molar mass
    """
    masses = solid_solution.end_members.values()
    tol = tolerance(solid_solution)
    assert min(masses) - tol <= molar_mass <= max(masses) + tol


@given(compositions())
def test_solid_solution_molar_mass_is_bounded(composition: tuple[SolidSolution, dict[str, np.float64]]) -> None:
    """
    Ensure that `SolidSolution.molar_mass` lies between the smallest and largest end-member molar masses.

    @param composition The solid solution and its mole fractions
    """
    solid_solution, mole_fractions = composition
    assert_bounded(solid_solution, solid_solution.molar_mass(mole_fractions))


@given(compositions(), st.floats(min_value=1e-3, max_value=1e3))
def test_solid_solution_molar_mass_is_scale_invariant(
    composition: tuple[SolidSolution, dict[str, np.float64]],
    scale: float,
) -> None:
    """
    Ensure that scaling every mole fraction by the same factor does not change `SolidSolution.molar_mass`.

    @param composition The solid solution and its mole fractions
    @param scale       The factor by which every mole fraction is scaled
    """
    solid_solution, mole_fractions = composition
    scaled = {name: fraction * np.float64(scale) for name, fraction in mole_fractions.items()}
    assert solid_solution.molar_mass(scaled) == pytest.approx(
        solid_solution.molar_mass(mole_fractions),
        abs=tolerance(solid_solution),
    )


@given(compositions(), st.data())
def test_solid_solution_molar_mass_of_pure_end_member(
    composition: tuple[SolidSolution, dict[str, np.float64]],
    data: st.DataObject,
) -> None:
    """
    Ensure that `SolidSolution.molar_mass` is an end member's molar mass if only that end member is present.

    @param composition The solid solution and its mole fractions
    @param data        The Hypothesis data object, used to draw the end member present
    """
    solid_solution, mole_fractions = composition
    present = data.draw(st.sampled_from(sorted(mole_fractions)))
    pure = {name: (fraction if name == present else np.float64(0.0)) for name, fraction in mole_fractions.items()}
    assert solid_solution.molar_mass(pure) == pytest.approx(
        solid_solution.end_members[present],
        abs=tolerance(solid_solution),
    )


@given(compositions())
def test_solid_solution_molar_mass_is_independent_of_order(
    composition: tuple[SolidSolution, dict[str, np.float64]],
) -> None:
    """
    Ensure that `SolidSolution.molar_mass` does not depend on the order of the end members or mole fractions.

    @param composition The solid solution and its mole fractions
    """
    solid_solution, mole_fractions = composition
    reordered = SolidSolution(name=solid_solution.name, end_members=dict(reversed(solid_solution.end_members.items())))
    assert reordered.molar_mass(dict(reversed(mole_fractions.items()))) == pytest.approx(
        solid_solution.molar_mass(mole_fractions),
        abs=tolerance(solid_solution),
    )


## Arbitrary mole fractions, including negative, non-finite and large values (whose sums can overflow)
ARBITRARY_FRACTIONS = st.floats().map(np.float64)


@given(compositions(fractions=ARBITRARY_FRACTIONS))
@example((SolidSolution(name="SS", end_members={"0": np.float64(1.5)}), {"0": np.float64(5e-324)}))
def test_solid_solution_molar_mass_is_bounded_or_rejected(
    composition: tuple[SolidSolution, dict[str, np.float64]],
) -> None:
    """
    Ensure that `SolidSolution.molar_mass` either rejects arbitrary mole fractions or is bounded by the end members.

    @param composition The solid solution and its (arbitrary) mole fractions
    """
    solid_solution, mole_fractions = composition
    try:
        molar_mass = solid_solution.molar_mass(mole_fractions)
    except ValueError:
        return
    assert_bounded(solid_solution, molar_mass)
