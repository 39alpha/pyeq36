"""Test the temperature-pressure curve `eq36.data1.TPCurve`."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, cast

import numpy as np
import pytest

from eq36.data1 import TPCurve

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from eq36.data1 import CartesianCoord, FloatRange
    from eq36.typing import Array1D

## The type of the pressure polynomials of a `TPCurve`
Pressure: TypeAlias = "tuple[Array1D[np.float64], Array1D[np.float64]]"


def temperatures() -> dict[str, np.float64]:
    """
    Construct the bounding temperatures, `0`, `5` and `10`, used by the curves in these tests.

    @return The bounding temperatures, keyed by `"min"`, `"mid"` and `"max"`
    """
    return {"min": np.float64(0.0), "mid": np.float64(5.0), "max": np.float64(10.0)}


def constant_curve(domain: list[FloatRange] | None = None) -> TPCurve:
    """
    Construct a curve with a constant pressure of `1` on `[0, 10]`.

    @param domain The domain to which the curve is restricted, if any

    @return The curve
    """
    curve = TPCurve(temperatures(), (np.array([1.0]), np.array([1.0])))
    if domain is not None:
        curve.domain = domain
    return curve


def interval(lower: float, upper: float) -> FloatRange:
    """
    Construct a temperature or pressure interval.

    @param lower The lower bound
    @param upper The upper bound

    @return The interval
    """
    return (np.float64(lower), np.float64(upper))


@pytest.mark.parametrize(
    ("temperature", "pressure", "match"),
    [
        (
            {"min": np.float64(0.0), "max": np.float64(10.0)},
            (np.array([1.0]), np.array([1.0])),
            "must have min, mid and max",
        ),
        (temperatures(), (np.array([1.0]),), "not enough values to unpack"),
        (temperatures(), (np.array([]), np.array([1.0])), "no coefficients"),
        (temperatures(), (np.array([1.0]), np.array([2.0])), "differ at the common temperature"),
        (
            {"min": np.float64(5.0), "mid": np.float64(0.0), "max": np.float64(10.0)},
            (np.array([1.0]), np.array([1.0])),
            "min <= mid <= max",
        ),
        (
            {"min": np.float64(0.0), "mid": np.float64(10.0), "max": np.float64(5.0)},
            (np.array([1.0]), np.array([1.0])),
            "min <= mid <= max",
        ),
    ],
    ids=["missing-mid", "one-polynomial", "empty-polynomial", "discontinuous", "mid-below-min", "max-below-mid"],
)
def test_init_rejects_invalid_arguments(temperature: object, pressure: object, match: str) -> None:
    """
    Ensure that `TPCurve` raises a `ValueError` for invalid temperatures or polynomials.

    @param temperature The bounding temperatures
    @param pressure    The pressure polynomials
    @param match       A pattern matching the expected error message
    """
    with pytest.raises(ValueError, match=match):
        _ = TPCurve(cast("dict[str, np.float64]", temperature), cast("Pressure", pressure))


@pytest.mark.parametrize(
    "dot_results",
    [[1.0, np.float64(1.0)], [np.float64(1.0), 1.0]],
    ids=["left", "right"],
)
def test_init_requires_float64_evaluations(mocker: MockerFixture, dot_results: list[object]) -> None:
    """
    Ensure that `TPCurve` raises a `TypeError` if either polynomial does not evaluate to an `np.float64`.

    @param mocker      The pytest-mock mocker fixture
    @param dot_results The successive results of `np.dot`
    """
    _ = mocker.patch("numpy.dot", side_effect=dot_results)
    with pytest.raises(TypeError):
        _ = constant_curve()


def test_reset_domain_returns_curve() -> None:
    """Ensure that `reset_domain` restores the full domain and returns the curve."""
    curve = constant_curve([interval(1.0, 2.0)])
    assert curve.reset_domain() is curve
    assert curve.domain == [interval(0.0, 10.0)]


@pytest.mark.parametrize(("temperature", "expected"), [(1.0, True), (20.0, False)])
def test_temperature_in_domain(temperature: float, *, expected: bool) -> None:
    """
    Ensure that `temperature_in_domain` determines whether a temperature is in the domain.

    @param temperature The temperature to check
    @param expected    Whether the temperature is in the domain
    """
    assert constant_curve().temperature_in_domain(np.float64(temperature)) is expected


@pytest.mark.parametrize(("temperature", "pressure"), [(0.0, 2.0), (10.0, 12.0)])
def test_call_evaluates_polynomial(temperature: float, pressure: float) -> None:
    """
    Ensure that calling a curve evaluates its polynomial.

    @param temperature The temperature at which to evaluate the curve
    @param pressure    The expected pressure
    """
    curve = TPCurve(temperatures(), (np.array([2.0, 1.0]), np.array([2.0, 1.0])))
    assert curve(np.float64(temperature)) == np.float64(pressure)


def test_call_rejects_temperature_outside_domain() -> None:
    """Ensure that calling a curve raises a `ValueError` for a temperature outside of its domain."""
    with pytest.raises(ValueError, match="not in the restricted domain"):
        _ = constant_curve()(np.float64(99.0))


def test_call_requires_float64_evaluation(mocker: MockerFixture) -> None:
    """
    Ensure that calling a curve raises a `TypeError` if the polynomial does not evaluate to an `np.float64`.

    @param mocker The pytest-mock mocker fixture
    """
    curve = constant_curve()
    _ = mocker.patch("numpy.dot", return_value=1.0)
    with pytest.raises(TypeError):
        _ = curve(np.float64(1.0))


def mock_intersections(mocker: MockerFixture, intersections: list[CartesianCoord]) -> None:
    """
    Replace `TPCurve.find_boundary_intersections` with a mock returning fixed intersections.

    @param mocker        The pytest-mock mocker fixture
    @param intersections The intersections to return
    """
    _ = mocker.patch.object(TPCurve, "find_boundary_intersections", return_value=intersections)


def test_set_domain_without_intersections_outside_region(mocker: MockerFixture) -> None:
    """
    Ensure that `set_domain` empties the domain and returns `False` if the curve lies outside of the region.

    @param mocker The pytest-mock mocker fixture
    """
    mock_intersections(mocker, [])
    curve = constant_curve()
    assert not curve.set_domain(interval(20.0, 30.0), interval(0.0, 2.0))
    assert curve.domain == []


def test_set_domain_without_intersections_inside_region(mocker: MockerFixture) -> None:
    """
    Ensure that `set_domain` keeps the full domain and returns `True` if the curve lies inside the region.

    @param mocker The pytest-mock mocker fixture
    """
    mock_intersections(mocker, [])
    curve = constant_curve()
    assert curve.set_domain(interval(-1.0, 11.0), interval(0.0, 2.0))
    assert curve.domain == [interval(0.0, 10.0)]


def test_set_domain_without_intersections_rejects_one_endpoint_inside(mocker: MockerFixture) -> None:
    """
    Ensure that `set_domain` raises if there are no intersections but exactly one endpoint is in the region.

    @param mocker The pytest-mock mocker fixture
    """
    mock_intersections(mocker, [])
    with pytest.raises(Exception, match="expected to find intersections"):
        _ = constant_curve().set_domain(interval(0.0, 3.0), interval(0.0, 2.0))


@pytest.mark.parametrize(
    ("temperature_range", "expected"),
    [
        (interval(5.0, 5.0), [interval(5.0, 5.0)]),
        (interval(0.0, 10.0), [interval(0.0, 5.0), interval(5.0, 10.0)]),
    ],
    ids=["single-point", "both-sides"],
)
def test_set_domain_with_one_intersection(
    mocker: MockerFixture,
    temperature_range: FloatRange,
    expected: list[FloatRange],
) -> None:
    """
    Ensure that `set_domain` builds the domain around a single intersection at the midpoint temperature.

    @param mocker            The pytest-mock mocker fixture
    @param temperature_range The temperature bounds of the region
    @param expected          The expected domain
    """
    mock_intersections(mocker, [(np.float64(5.0), np.float64(1.0))])
    curve = constant_curve()
    assert curve.set_domain(temperature_range, interval(0.0, 2.0))
    assert curve.domain == expected


def test_set_domain_with_multiple_intersections(mocker: MockerFixture) -> None:
    """
    Ensure that `set_domain` keeps the intervals between consecutive intersections that lie in the region.

    @param mocker The pytest-mock mocker fixture
    """
    mock_intersections(mocker, [(np.float64(t), np.float64(1.0)) for t in (1.0, 3.0, 8.0)])
    curve = constant_curve()
    assert curve.set_domain(interval(0.0, 10.0), interval(0.0, 2.0))
    assert curve.domain == [interval(1.0, 3.0), interval(3.0, 8.0)]


def test_find_boundary_intersections_includes_temperature_bounds() -> None:
    """Ensure that `find_boundary_intersections` includes the curve's crossings of the temperature bounds."""
    intersections = constant_curve().find_boundary_intersections(interval(0.0, 10.0), interval(1.0, 2.0))
    assert (0.0, 1.0) in intersections
    assert (10.0, 1.0) in intersections


def test_find_boundary_intersections_skips_temperatures_outside_domain() -> None:
    """Ensure that `find_boundary_intersections` skips temperature bounds outside of the curve's domain."""
    curve = constant_curve([interval(1.0, 2.0)])
    intersections = curve.find_boundary_intersections(interval(0.0, 2.0), interval(1.0, 1.0))
    assert all(t != 0.0 for t, _ in intersections)


def test_find_boundary_intersections_includes_right_polynomial_roots(mocker: MockerFixture) -> None:
    """
    Ensure that `find_boundary_intersections` includes roots of the polynomial on `[mid, max]`.

    @param mocker The pytest-mock mocker fixture
    """
    _ = mocker.patch("numpy.roots", return_value=np.array([8.0]))
    intersections = constant_curve().find_boundary_intersections(interval(0.0, 10.0), interval(1.0, 1.0))
    assert (8.0, 1.0) in intersections


def test_find_boundary_intersections_skips_roots_outside_domain() -> None:
    """Ensure that `find_boundary_intersections` skips roots outside of the curve's domain."""
    curve = TPCurve(temperatures(), (np.array([-2.0]), np.array([-7.0, 1.0])))
    curve.domain = [interval(0.0, 3.0)]
    assert curve.find_boundary_intersections(interval(0.0, 10.0), interval(0.0, 0.0)) == []


@pytest.mark.parametrize(
    ("domains", "expected"),
    [
        ([], []),
        ([[interval(0.0, 2.0), interval(3.0, 4.0)], [interval(1.0, 3.5)]], [interval(0.0, 4.0)]),
        ([[interval(0.0, 1.0)], [interval(3.0, 4.0)]], [interval(0.0, 1.0), interval(3.0, 4.0)]),
    ],
    ids=["no-curves", "overlapping", "disjoint"],
)
def test_union_domains(domains: list[list[FloatRange]], expected: list[FloatRange]) -> None:
    """
    Ensure that `union_domains` merges overlapping subdomains and preserves disjoint ones.

    @param domains  The domains of the curves
    @param expected The expected union
    """
    assert TPCurve.union_domains([constant_curve(domain) for domain in domains]) == expected


@pytest.mark.parametrize(
    ("domains", "uniform", "temps", "selected"),
    [
        ([[interval(0.0, 2.0)]], [0.5, 1.5], [0.5, 1.5], [0, 0]),
        ([[interval(0.0, 1.0)], [interval(3.0, 4.0)]], [0.2, 1.8], [0.2, 3.8], [0, 1]),
    ],
    ids=["one-subdomain", "across-gap"],
)
def test_sample(
    mocker: MockerFixture,
    domains: list[list[FloatRange]],
    uniform: list[float],
    temps: list[float],
    selected: list[int],
) -> None:
    """
    Ensure that `sample` maps uniform draws onto the union of the domains, skipping gaps between subdomains.

    @param mocker   The pytest-mock mocker fixture
    @param domains  The domains of the curves
    @param uniform  The draws returned by the mocked `rng.uniform`
    @param temps    The expected sampled temperatures
    @param selected The indices of the curves expected to be selected
    """
    curves = [constant_curve(domain) for domain in domains]
    rng = mocker.create_autospec(
        np.random.Generator,
        instance=True,
        **{"uniform.return_value": np.array(uniform), "integers.return_value": 0},
    )

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(curves, len(uniform), rng=rng)

    assert list(sampled_temps) == temps
    assert list(sampled_presses) == [1.0] * len(uniform)
    assert len(sampled_curves) == len(selected)
    assert all(curve is curves[i] for curve, i in zip(sampled_curves, selected, strict=True))


@pytest.mark.parametrize(
    "domains",
    [
        [[interval(2.0, 2.0)], [interval(7.0, 7.0)]],
        [[interval(2.0, 2.0), interval(7.0, 7.0)]],
        [[interval(2.0, 2.0)], [interval(7.0, 7.0)], []],
    ],
    ids=["one-point-per-curve", "two-points-on-one-curve", "with-empty-domain"],
)
def test_sample_chooses_between_single_point_domains(domains: list[list[FloatRange]]) -> None:
    """
    Ensure that `sample` draws from every point if the union of the domains consists only of single points.

    The union has zero length, so the temperatures cannot be drawn by length;
    instead, each sample should come from one of the points, chosen at random.

    @param domains The domains of the curves, whose union is the points `2` and `7`
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, _, sampled_curves = TPCurve.sample(curves, 100, rng=np.random.default_rng(0))

    assert set(sampled_temps.tolist()) == {2.0, 7.0}
    assert all(
        curve.temperature_in_domain(temp)
        for temp, curve in zip(sampled_temps.tolist(), sampled_curves, strict=True)
    )


@pytest.mark.parametrize("num_samples", [0, 3])
@pytest.mark.parametrize("domains", [[], [[], []]], ids=["no-curves", "empty-domains"])
def test_sample_returns_nothing_to_sample(domains: list[list[FloatRange]], num_samples: int) -> None:
    """
    Ensure that `sample` returns no temperatures, pressures or curves if there is nothing to sample.

    There is nothing to sample if there are no curves, or if every curve's
    domain is empty (e.g. after `set_domain` with a rectangle that no curve
    passes through).

    @param domains     The domains of the curves
    @param num_samples The number of points to sample
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(
        curves,
        num_samples,
        rng=np.random.default_rng(0),
    )

    assert sampled_temps.size == 0
    assert sampled_presses.size == 0
    assert sampled_curves == []


@pytest.mark.parametrize(
    "domains",
    [[[interval(0.0, 10.0)]], [[interval(2.0, 2.0)], [interval(7.0, 7.0)]]],
    ids=["intervals", "single-points"],
)
def test_sample_returns_nothing_for_zero_samples(domains: list[list[FloatRange]]) -> None:
    """
    Ensure that `sample` returns no temperatures, pressures or curves if no samples are requested.

    @param domains The (non-empty) domains of the curves
    """
    curves = [constant_curve(domain) for domain in domains]

    sampled_temps, sampled_presses, sampled_curves = TPCurve.sample(curves, 0, rng=np.random.default_rng(0))

    assert sampled_temps.size == 0
    assert sampled_presses.size == 0
    assert sampled_curves == []
