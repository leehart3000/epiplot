import pandas as pd
import pytest

from epiplot import count_cases


def as_dates(result: pd.DataFrame) -> list[str]:
    """Return the period start dates as text, to compare easily."""
    return [d.strftime("%Y-%m-%d") for d in result["period_start"]]


def test_daily_counts_include_days_with_no_cases() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", "2026-03-02", "2026-03-04"]})

    result = count_cases(data, "onset", interval="day")

    assert as_dates(result) == ["2026-03-02", "2026-03-03", "2026-03-04"]
    assert result["cases"].tolist() == [2, 0, 1]


def test_weeks_start_on_monday_by_default() -> None:
    # 2026-03-01 is a Sunday, 2026-03-02 a Monday, 2026-03-15 a Sunday.
    data = pd.DataFrame({"onset": ["2026-03-01", "2026-03-02", "2026-03-15"]})

    result = count_cases(data, "onset")

    assert as_dates(result) == ["2026-02-23", "2026-03-02", "2026-03-09"]
    assert result["cases"].tolist() == [1, 1, 1]


def test_weeks_can_start_on_sunday() -> None:
    data = pd.DataFrame({"onset": ["2026-03-01", "2026-03-02", "2026-03-15"]})

    result = count_cases(data, "onset", week_start="sunday")

    assert as_dates(result) == ["2026-03-01", "2026-03-08", "2026-03-15"]
    assert result["cases"].tolist() == [2, 0, 1]


def test_monthly_counts_include_months_with_no_cases() -> None:
    data = pd.DataFrame({"onset": ["2026-01-31", "2026-03-01", "2026-03-20"]})

    result = count_cases(data, "onset", interval="month")

    assert as_dates(result) == ["2026-01-01", "2026-02-01", "2026-03-01"]
    assert result["cases"].tolist() == [1, 0, 2]


def test_missing_dates_are_counted_not_silently_dropped() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", None, None]})

    result = count_cases(data, "onset", interval="day")

    assert result["cases"].tolist() == [1]
    assert result.attrs["n_missing_dates"] == 2


def test_all_dates_missing_gives_empty_table() -> None:
    data = pd.DataFrame({"onset": [None, None]})

    result = count_cases(data, "onset")

    assert result.empty
    assert list(result.columns) == ["period_start", "cases"]
    assert result.attrs["n_missing_dates"] == 2


def test_times_of_day_are_ignored() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02 08:00", "2026-03-02 23:59"]})

    result = count_cases(data, "onset", interval="day")

    assert as_dates(result) == ["2026-03-02"]
    assert result["cases"].tolist() == [2]


def test_count_column_is_used_as_weights() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", "2026-03-04"], "n": [5, 3]})

    result = count_cases(data, "onset", interval="day", count_col="n")

    assert result["cases"].tolist() == [5, 0, 3]


@pytest.mark.parametrize("bad_count", [-1, 1.5, None])
def test_invalid_counts_raise_an_error(bad_count: float | None) -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", "2026-03-04"], "n": [1, bad_count]})

    with pytest.raises(ValueError, match="whole numbers"):
        count_cases(data, "onset", count_col="n")


def test_groups_include_zero_counts_for_every_period() -> None:
    data = pd.DataFrame(
        {
            "onset": ["2026-03-02", "2026-03-02", "2026-03-03"],
            "origin": ["local", "travel", "local"],
        }
    )

    result = count_cases(data, "onset", interval="day", group_col="origin")

    assert list(result.columns) == ["period_start", "origin", "cases"]
    assert as_dates(result) == [
        "2026-03-02",
        "2026-03-02",
        "2026-03-03",
        "2026-03-03",
    ]
    assert result["origin"].tolist() == ["local", "travel", "local", "travel"]
    assert result["cases"].tolist() == [1, 1, 1, 0]


def test_missing_group_values_are_counted_as_missing() -> None:
    data = pd.DataFrame(
        {"onset": ["2026-03-02", "2026-03-02"], "origin": ["local", None]}
    )

    result = count_cases(data, "onset", interval="day", group_col="origin")

    assert result["origin"].tolist() == ["local", "Missing"]
    assert result["cases"].tolist() == [1, 1]


def test_categorical_group_order_is_kept() -> None:
    origin = pd.Categorical(["local", "travel"], categories=["travel", "local"])
    data = pd.DataFrame({"onset": ["2026-03-02", "2026-03-02"], "origin": origin})

    result = count_cases(data, "onset", interval="day", group_col="origin")

    assert result["origin"].tolist() == ["travel", "local"]


def test_unknown_interval_raises_an_error() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02"]})

    with pytest.raises(ValueError, match="interval"):
        count_cases(data, "onset", interval="year")  # type: ignore[arg-type]


def test_missing_column_raises_an_error() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02"]})

    with pytest.raises(KeyError, match="onset_date"):
        count_cases(data, "onset_date")


def test_missing_dates_count_cases_not_rows() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", None], "n": [1, 4]})

    result = count_cases(data, "onset", count_col="n")

    assert result.attrs["n_missing_dates"] == 4
