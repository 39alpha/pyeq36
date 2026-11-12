"""
Test `eq36.data1.Data1.from_file` against the `eqpt` test data.

Each data1 file is parsed and compared with the reference values in the
corresponding `.d1f` file. The temperature-pressure curve is also compared
with the grid in the `.d0` file from which `eqpt` fit it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from eq36 import eqpt
from eq36.data1 import Data1

from .eqpt_reference import D1F, DATA_DIR, ENCODING, REL_10SF, TOL_3DP, TOL_4DP, TOL_5DP

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from eq36.data1 import Species


@pytest.fixture(scope="module")
def parsed(database: str) -> Data1:
    """
    Parse the database's data1 file with `Data1.from_file`.

    @param database The name of the database

    @return The parsed data
    """
    return Data1.from_file(DATA_DIR / f"{database}.d1")


def molar_masses(species: Mapping[str, Species]) -> dict[str, float]:
    """
    Get the molar masses of species, keyed by name.

    @param species The species, keyed by name

    @return The molar masses, keyed by name
    """
    return {name: float(s.molar_mass) for name, s in species.items()}


def test_records_filename(parsed: Data1, database: str) -> None:
    """
    Ensure that the path of the data1 file is recorded.

    @param parsed   The parsed data
    @param database The name of the database
    """
    assert parsed.filename == DATA_DIR / f"{database}.d1"


def test_reads_elements(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the elements and their atomic weights are read.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    assert {name: float(weight) for name, weight in parsed.elements.items()} == pytest.approx(
        d1f.elements,
        abs=TOL_5DP,
    )


def test_reads_aqueous_species(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the aqueous species and their molar masses are read.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    expected = {s.name: s.molar_mass for s in d1f.aqueous}
    assert molar_masses(parsed.aqueous_species) == pytest.approx(expected, abs=TOL_3DP)


def test_reads_minerals(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the pure minerals and their molar masses are read.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    expected = {s.name: s.molar_mass for s in d1f.minerals}
    assert molar_masses(parsed.minerals) == pytest.approx(expected, abs=TOL_3DP)


def test_reads_water_as_only_liquid(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that water, the first aqueous species, is the only pure liquid.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    water = d1f.aqueous[0]
    assert molar_masses(parsed.liquids) == pytest.approx({water.name: water.molar_mass}, abs=TOL_3DP)


def test_reads_gases(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the gas species and their molar masses are read.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    expected = {s.name: s.molar_mass for s in d1f.gases}
    assert molar_masses(parsed.gases) == pytest.approx(expected, abs=TOL_3DP)


def test_reads_basis_species(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the strict basis species (those without a reaction) are read with their compositions and charges.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    basis = [s for s in d1f.aqueous if s.reaction_size == 0]
    assert {name: (s.composition, s.charge) for name, s in parsed.basis_species.items()} == {
        s.name: ({element: int(count) for element, count in s.composition.items()}, int(s.charge)) for s in basis
    }
    assert molar_masses(parsed.basis_species) == pytest.approx({s.name: s.molar_mass for s in basis}, abs=TOL_3DP)


@pytest.mark.parametrize(("element", "expected"), [("H", "H+"), ("O", "O2(g)")])
def test_get_basis_species_of_shared_element(parsed: Data1, element: str, expected: str) -> None:
    """
    Ensure that the basis species of an element shared by many basis species is the one consisting only of it.

    @param parsed   The parsed data
    @param element  The element, which occurs in many basis species
    @param expected The name of the basis species consisting only of `element`
    """
    species = parsed.get_basis_species(element)
    assert species is not None
    assert species.name == expected


def test_reads_solid_solutions(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the solid solutions are read with their end members, whose molar masses are those of the minerals.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    minerals = {s.name: s.molar_mass for s in d1f.minerals}
    actual = {name: molar_masses_of(ss.end_members) for name, ss in parsed.solid_solutions.items()}
    expected = {name: {member: minerals[member] for member in members} for name, members in d1f.solid_solutions.items()}
    assert actual.keys() == expected.keys()
    for name, members in expected.items():
        assert actual[name] == pytest.approx(members, abs=TOL_3DP)


def molar_masses_of(end_members: dict[str, np.float64]) -> dict[str, float]:
    """
    Convert end-member molar masses to plain floats.

    @param end_members The end-member molar masses, keyed by name

    @return The molar masses, keyed by name
    """
    return {name: float(mass) for name, mass in end_members.items()}


## The number of temperature ranges supported by `TPCurve`
TPCURVE_RANGES = 2


@pytest.fixture
def xfail_multi_range(request: pytest.FixtureRequest, d1f: D1F) -> None:
    """
    Mark a test as an expected failure for databases with more than two temperature ranges.

    `Data1.from_file` constructs `tp_curve` from only the first two ranges, and
    `TPCurve` supports exactly two polynomials. The failure is strict, so the
    mark must be removed once more ranges are supported.

    @param request The pytest fixture request, used to apply the mark
    @param d1f     The reference values
    """
    if len(d1f.range_maxima) > TPCURVE_RANGES:
        request.applymarker(
            pytest.mark.xfail(reason="tp_curve supports only two temperature ranges", strict=True),
        )


@pytest.mark.usefixtures("xfail_multi_range")
def test_tp_curve_spans_temperature_ranges(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the curve starts at the nominal minimum temperature and is split at, and ends at, the range maxima.

    @param parsed The parsed data
    @param d1f    The reference values

    @todo Decide whether the curve should start at the nominal minimum
          temperature (`tdamin`, as `Data1.from_file` does and this test
          expects) or at the start of the temperature grid. They differ for
          some databases, e.g. `fmt`, whose nominal limits are 25-25 C but
          whose grid spans 0-300 C.
    """
    assert parsed.tp_curve is not None
    temperature = {key: float(value) for key, value in parsed.tp_curve.temperature.items()}
    expected = {"min": d1f.temperature_limits[0], "mid": d1f.range_maxima[0], "max": d1f.range_maxima[-1]}
    assert temperature == pytest.approx(expected, abs=TOL_3DP)


@pytest.mark.usefixtures("xfail_multi_range")
def test_tp_curve_has_pressure_polynomial_per_range(parsed: Data1, d1f: D1F) -> None:
    """
    Ensure that the curve has the pressure polynomial of each temperature range, padded with zeros.

    @param parsed The parsed data
    @param d1f    The reference values
    """
    assert parsed.tp_curve is not None
    actual = [coefficients.tolist() for coefficients in parsed.tp_curve.pressure]
    expected = [c + [0.0] * (len(actual[0]) - len(c)) for c in d1f.pressure_coefficients]
    assert actual == [pytest.approx(c, rel=REL_10SF) for c in expected]


@pytest.mark.usefixtures("xfail_multi_range")
def test_tp_curve_reproduces_d0_grid(parsed: Data1, d1f: D1F, d0_grid: list[tuple[float, float]]) -> None:
    """
    Ensure that the curve reproduces the `.d0` grid pressures within the nominal temperature limits.

    @param parsed  The parsed data
    @param d1f     The reference values
    @param d0_grid The `(temperature, pressure)` points of the `.d0` grid

    @todo Decide whether the curve should reproduce the whole grid or only the
          points within the nominal temperature limits, as this test assumes.
          For `fmt`, `hmw` and `ph5`, whose nominal limits are 25-25 C, only
          the 25 C point is currently checked.
    """
    assert parsed.tp_curve is not None
    low, high = d1f.temperature_limits
    points = [(t, p) for t, p in d0_grid if low <= t <= high]
    actual = [float(parsed.tp_curve(np.float64(t))) for t, _ in points]
    assert actual == pytest.approx([p for _, p in points], abs=TOL_4DP)


def test_reads_no_solid_solutions_without_gases(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that a data file with neither gases nor solid solutions is read with neither.

    The data0 file is `hmw.d0`, which has no solid solutions, with its gas
    species removed. For such a file, `EQLIB/indata` sets the start of the gas
    range and both ends of the solid-solution range to zero.

    @param monkeypatch The pytest monkeypatch fixture, used to run `eqpt` in `tmp_path`
    @param tmp_path    A temporary directory in which to write and process the data0 file
    """
    lines = (DATA_DIR / "hmw.d0").read_text(encoding=ENCODING).split("\n")
    gases = lines.index("gases")
    solid_solutions = lines.index("solid solutions")
    _ = (tmp_path / "nogas.d0").write_text(
        "\n".join(lines[: gases + 2] + lines[solid_solutions:]),
        encoding=ENCODING,
    )
    monkeypatch.chdir(tmp_path)
    _ = eqpt("nogas.d0")

    parsed = Data1.from_file(tmp_path / "nogas.d1")
    assert parsed.gases == {}
    assert parsed.solid_solutions == {}
