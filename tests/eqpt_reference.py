"""
Read reference values from the EQ3/6 `eqpt` test data.

The `eq36/test/data/eqpt` directory contains, for each of several databases, a
human-readable data0 file (`.d0`) and the binary data1 (`.d1`) and formatted
data1 (`.d1f`) files that `eqpt` produces from it. The `.d1f` file is a
text rendering of the contents of the `.d1` file, so it provides the expected
values for the data read from the `.d1` file. The `.d0` file provides the
temperature-pressure grid from which `eqpt` fits the pressure polynomials.

The parsers here read only what the tests need, and assume the layout used by
the files in that directory.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

## The directory containing the `eqpt` test data
DATA_DIR = Path(__file__).parent.parent / "eq36" / "test" / "data" / "eqpt"

## The names of the databases in `DATA_DIR`, i.e. the stems of the `.d1` files
DATABASES = sorted(path.stem for path in DATA_DIR.glob("*.d1"))

## The encoding of the files (some data0 files contain non-ASCII characters)
ENCODING = "latin-1"

## The prefix of the lines separating blocks
SEPARATOR = "*-----"

## The line ending a superblock of species
ENDIT = "endit."

## The width of the fixed-width floating-point fields of the polynomial coefficients
COEFFICIENT_WIDTH = 16

## The width of a species or element name
NAME_WIDTH = 24

## A small allowance for floating-point error, so that values exactly half a unit in the last printed
## place from the printed value (rounding ties) are within tolerance
TIE = 1e-9

## The tolerance for values printed to 3 decimal places, e.g. molecular weights and temperatures
TOL_3DP = 5e-4 + TIE

## The tolerance for values printed to 4 decimal places, e.g. pressures in the `.d0` grid
TOL_4DP = 5e-5 + TIE

## The tolerance for values printed to 5 decimal places, e.g. atomic weights
TOL_5DP = 5e-6 + TIE

## The relative tolerance for values printed with 10 significant figures, e.g. polynomial coefficients
REL_10SF = 5e-10 + TIE

## A coefficient-name pair, as in the composition of a species
PAIR = re.compile(r"(-?\d+\.\d*)\s+(\S+)")


@dataclass
class Species:
    """A species block of a `.d1f` file."""

    ## The name of the species
    name: str
    ## The molecular weight of the species
    molar_mass: float
    ## The electrical charge of the species
    charge: float
    ## The elemental composition, mapping element names to counts
    composition: dict[str, float]
    ## The number of species in the species' reaction; zero for strict basis species
    reaction_size: int


@dataclass
class D1F:
    """The reference values read from a `.d1f` file."""

    ## The chemical elements, mapping names to atomic weights, in file order
    elements: dict[str, float] = field(default_factory=dict)
    ## The nominal minimum and maximum temperatures (Celsius)
    temperature_limits: tuple[float, float] = (0.0, 0.0)
    ## The maximum temperature (Celsius) of each temperature range
    range_maxima: list[float] = field(default_factory=list)
    ## The coefficients of the pressure polynomial of each temperature range
    pressure_coefficients: list[list[float]] = field(default_factory=list)
    ## The aqueous species, in file order
    aqueous: list[Species] = field(default_factory=list)
    ## The pure minerals, in file order
    minerals: list[Species] = field(default_factory=list)
    ## The gas species, in file order
    gases: list[Species] = field(default_factory=list)
    ## The solid solutions, mapping names to the names of their end members
    solid_solutions: dict[str, list[str]] = field(default_factory=dict)


def read_lines(path: Path) -> list[str]:
    """
    Read the lines of a data file, without trailing whitespace.

    @param path The path to the file

    @return The lines
    """
    return [line.rstrip() for line in path.read_text(encoding=ENCODING).splitlines()]


def block_after(lines: list[str], header: str, start: int = 0) -> list[str]:
    """
    Get the lines following a header, up to the next separator.

    A separator immediately following the header is skipped.

    @param lines  The lines of the file
    @param header The header line
    @param start  The index from which to search for the header

    @return The lines between the header and the next separator

    @throws ValueError if the header is not found
    """
    i = lines.index(header, start) + 1
    if lines[i].startswith(SEPARATOR):
        i += 1
    block: list[str] = []
    while i < len(lines) and not lines[i].startswith(SEPARATOR):
        block.append(lines[i])
        i += 1
    return block


def parse_coefficients(lines: list[str]) -> list[float]:
    """
    Parse fixed-width floating-point fields, which need not be separated by whitespace.

    @param lines The lines containing the fields

    @return The values of the fields, in order
    """
    return [float(line[i : i + COEFFICIENT_WIDTH]) for line in lines for i in range(0, len(line), COEFFICIENT_WIDTH)]


def parse_species(block: list[str]) -> Species:
    """
    Parse a species block of a `.d1f` file.

    The block consists of a header line (the name followed by the number of
    elements in the composition and the number of species in the reaction), a
    line with the molecular weight and charge, and the composition, two
    elements per line. Any reaction and log K lines that follow are ignored.

    @param block The lines of the block

    @return The species
    """
    header = block[0]
    composition_size, reaction_size = (int(float(n)) for n in header[NAME_WIDTH:].split()[:2])
    molar_mass, charge = (float(x) for x in block[1].split()[:2])
    composition_lines = block[2 : 2 + math.ceil(composition_size / 2)]
    composition = {element: float(count) for line in composition_lines for count, element in PAIR.findall(line)}
    return Species(
        name=header[:NAME_WIDTH].strip(),
        molar_mass=molar_mass,
        charge=charge,
        composition=composition,
        reaction_size=reaction_size,
    )


def blocks_after(lines: list[str], header: str) -> list[list[str]]:
    """
    Get the blocks of a superblock, e.g. the species blocks following `aqueous`.

    @param lines  The lines of the file
    @param header The header of the superblock

    @return The lines of each block, up to the terminating `endit.`
    """
    i = lines.index(header) + 2
    blocks: list[list[str]] = []
    block: list[str] = []
    while not lines[i].startswith(ENDIT):
        if lines[i].startswith(SEPARATOR):
            blocks.append(block)
            block = []
        else:
            block.append(lines[i])
        i += 1
    return blocks


def parse_solid_solution(block: list[str]) -> tuple[str, list[str]]:
    """
    Parse a solid-solution block of a `.d1f` file.

    The block consists of a header line (the name followed by the number of end
    members) and the end member names, two per line in fixed-width columns.
    Any model parameters that follow are ignored.

    @param block The lines of the block

    @return The name of the solid solution and the names of its end members
    """
    header = block[0]
    size = int(header[NAME_WIDTH:].split()[0])
    names = [
        name
        for line in block[1 : 1 + math.ceil(size / 2)]
        for name in (line[5 : 5 + NAME_WIDTH].strip(), line[34 : 34 + NAME_WIDTH].strip())
        if name
    ]
    return header[:NAME_WIDTH].strip(), names


def read_d1f(path: Path) -> D1F:
    """
    Read the reference values from a `.d1f` file.

    @param path The path to the file

    @return The reference values
    """
    lines = read_lines(path)
    d1f = D1F()

    for line in block_after(lines, "elements"):
        name, weight = line.split()
        d1f.elements[name] = float(weight)

    low, high = (float(x) for x in block_after(lines, "Data file maximum and minimum temperatures (C)")[0].split())
    d1f.temperature_limits = (min(low, high), max(low, high))
    d1f.range_maxima = [float(x) for x in block_after(lines, "Maximum temperature (C) by range")]

    points = [int(lines[i + 1]) for i, line in enumerate(lines) if line.startswith("Number of points in range")]
    coefficients = parse_coefficients(block_after(lines, "presg"))
    offsets = [sum(points[:i]) for i in range(len(points) + 1)]
    d1f.pressure_coefficients = [coefficients[a:b] for a, b in pairwise(offsets)]

    d1f.aqueous = [parse_species(block) for block in blocks_after(lines, "aqueous")]
    d1f.minerals = [parse_species(block) for block in blocks_after(lines, "minerals")]
    d1f.gases = [parse_species(block) for block in blocks_after(lines, "gases")]
    d1f.solid_solutions = dict(parse_solid_solution(block) for block in blocks_after(lines, "solid solutions"))
    return d1f


def read_d0_grid(path: Path) -> list[tuple[float, float]]:
    """
    Read the temperature-pressure grid from a `.d0` file.

    Two layouts are supported: `temperatures` and `pressures` blocks, and
    `Temperature grid (degC)` and `Pressure grid (bars)` blocks. Comment lines
    (beginning with `*`) are skipped.

    @param path The path to the file

    @return The `(temperature, pressure)` points of the grid

    @throws ValueError if neither layout is found
    """
    lines = read_lines(path)
    for temperature_header, pressure_header in [
        ("temperatures", "pressures"),
        ("Temperature grid (degC)", "Pressure grid (bars)"),
    ]:
        if temperature_header in lines and pressure_header in lines:
            temperatures = grid_values(lines, temperature_header)
            pressures = grid_values(lines, pressure_header)
            return list(zip(temperatures, pressures, strict=True))
    msg = f"no temperature-pressure grid found in {path}"
    raise ValueError(msg)


def grid_values(lines: list[str], header: str) -> list[float]:
    """
    Read the values of a grid block of a `.d0` file.

    The block continues, skipping comment lines, while the lines contain only
    numbers.

    @param lines  The lines of the file
    @param header The header of the block

    @return The values
    """
    values: list[float] = []
    for line in lines[lines.index(header) + 1 :]:
        if line.startswith("*"):
            continue
        try:
            values.extend(float(x) for x in line.split())
        except ValueError:
            break
    return values
