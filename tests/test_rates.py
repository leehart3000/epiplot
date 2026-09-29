import math

import pandas as pd
import pytest

from epiplot import calculate_rates


def one_region(cases: float | None, population: float | None) -> pd.DataFrame:
    """Make a table with a single region."""
    return pd.DataFrame({"area": ["A"], "cases": [cases], "population": [population]})


def test_rate_is_per_100000_by_default() -> None:
    result = calculate_rates(one_region(10, 50_000), "area", "cases", "population")

    assert result["rate"].tolist() == [20.0]
    assert result.attrs["per"] == 100_000


def test_rate_can_be_per_1000() -> None:
    data = one_region(10, 50_000)

    result = calculate_rates(data, "area", "cases", "population", per=1000)

    assert result["rate"].tolist() == [0.2]


def test_confidence_interval_is_exact_poisson() -> None:
    # The exact 95% interval for 10 events is 4.795 to 18.390 events.
    data = one_region(10, 100_000)

    result = calculate_rates(data, "area", "cases", "population")

    assert result["rate_lower"][0] == pytest.approx(4.795, abs=0.001)
    assert result["rate_upper"][0] == pytest.approx(18.390, abs=0.001)


def test_zero_cases_has_a_lower_limit_of_zero() -> None:
    # The exact 95% upper limit for 0 events is 3.689 events.
    data = one_region(0, 100_000)

    result = calculate_rates(data, "area", "cases", "population", min_cases=0)

    assert result["rate"][0] == 0
    assert result["rate_lower"][0] == 0
    assert result["rate_upper"][0] == pytest.approx(3.689, abs=0.001)
    assert result["status"][0] == "shown"


def test_regions_with_fewer_than_5_cases_are_hidden() -> None:
    data = pd.DataFrame(
        {"area": ["A", "B"], "cases": [4, 5], "population": [1000, 1000]}
    )

    result = calculate_rates(data, "area", "cases", "population")

    assert result["status"].tolist() == ["hidden", "shown"]
    # The rate is still calculated, for the analyst's own use.
    assert result["rate"][0] == 400


def test_min_cases_can_be_changed() -> None:
    data = one_region(4, 1000)

    result = calculate_rates(data, "area", "cases", "population", min_cases=3)

    assert result["status"][0] == "shown"


@pytest.mark.parametrize(("cases", "population"), [(None, 1000), (10, None), (10, 0)])
def test_missing_cases_or_population_means_no_data(
    cases: float | None, population: float | None
) -> None:
    result = calculate_rates(
        one_region(cases, population), "area", "cases", "population"
    )

    assert result["status"][0] == "no data"
    assert math.isnan(result["rate"][0])
    assert math.isnan(result["rate_lower"][0])


def test_output_columns_and_order() -> None:
    data = pd.DataFrame(
        {
            "area": ["B", "A"],
            "year": [2026, 2026],
            "cases": [10, 20],
            "population": [1000, 1000],
            "other": ["x", "y"],
        }
    )

    result = calculate_rates(data, "area", "cases", "population", period_col="year")

    assert list(result.columns) == [
        "area",
        "year",
        "cases",
        "population",
        "rate",
        "rate_lower",
        "rate_upper",
        "status",
    ]
    assert result["area"].tolist() == ["B", "A"]


def test_same_region_in_different_periods_is_allowed() -> None:
    data = pd.DataFrame(
        {
            "area": ["A", "A"],
            "year": [2025, 2026],
            "cases": [5, 6],
            "population": [10, 10],
        }
    )

    result = calculate_rates(data, "area", "cases", "population", period_col="year")

    assert len(result) == 2


def test_repeated_regions_raise_an_error() -> None:
    data = pd.DataFrame(
        {"area": ["A", "A"], "cases": [5, 6], "population": [1000, 1000]}
    )

    with pytest.raises(ValueError, match="2 rows share the same area"):
        calculate_rates(data, "area", "cases", "population")


@pytest.mark.parametrize("bad_cases", [-1, 2.5])
def test_invalid_cases_raise_an_error(bad_cases: float) -> None:
    with pytest.raises(ValueError, match="whole numbers"):
        calculate_rates(one_region(bad_cases, 1000), "area", "cases", "population")


def test_negative_population_raises_an_error() -> None:
    with pytest.raises(ValueError, match="negative"):
        calculate_rates(one_region(5, -1000), "area", "cases", "population")


def test_missing_column_raises_an_error() -> None:
    with pytest.raises(KeyError, match="pop"):
        calculate_rates(one_region(5, 1000), "area", "cases", "pop")
