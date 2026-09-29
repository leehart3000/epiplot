"""Epidemic curves (epicurves): counts of cases over time."""

from typing import Literal

import pandas as pd

Interval = Literal["day", "week", "month"]
WeekStart = Literal["monday", "sunday"]

MISSING_GROUP = "Missing"
"""Label used for cases whose group value is missing."""

_INTERVALS = ("day", "week", "month")
_WEEK_STARTS = ("monday", "sunday")
_FREQUENCIES = {"day": "D", "month": "MS"}
_WEEK_FREQUENCIES = {"monday": "W-MON", "sunday": "W-SUN"}


def count_cases(
    data: pd.DataFrame,
    date_col: str,
    *,
    interval: Interval = "week",
    week_start: WeekStart = "monday",
    group_col: str | None = None,
    count_col: str | None = None,
) -> pd.DataFrame:
    """Count cases per time period, including periods with no cases.

    Parameters
    ----------
    data
        A table with one row per case (a line list), or one row per count
        if ``count_col`` is given.
    date_col
        Name of the column holding the dates. Dates stored as text are
        converted automatically.
    interval
        Length of each period: ``"day"``, ``"week"`` or ``"month"``.
    week_start
        First day of each week when ``interval="week"``: ``"monday"`` for
        ISO weeks or ``"sunday"`` for US CDC (MMWR) weeks.
    group_col
        Optional column to count separately for each group, such as sex or
        travel history. Cases with a missing group are counted in a group
        called ``"Missing"``, so no cases are silently dropped.
    count_col
        Optional column holding a count for each row. If not given, each row
        counts as one case.

    Returns
    -------
    pandas.DataFrame
        One row per period (and per group, if ``group_col`` is given), with
        the columns ``period_start``, the group column (if any) and ``cases``.
        Every period from the first case to the last is included, with a
        count of zero where there were no cases. The number of rows left out
        because their date was missing is stored in
        ``result.attrs["n_missing_dates"]``.

    Raises
    ------
    KeyError
        If a named column is not in ``data``.
    ValueError
        If ``interval`` or ``week_start`` is not a recognised option, or if
        ``count_col`` contains missing, negative or non-whole numbers.
    """
    if interval not in _INTERVALS:
        raise ValueError(f"interval must be one of {_INTERVALS}, not {interval!r}")
    if week_start not in _WEEK_STARTS:
        raise ValueError(
            f"week_start must be one of {_WEEK_STARTS}, not {week_start!r}"
        )
    for col in (date_col, group_col, count_col):
        if col is not None and col not in data.columns:
            raise KeyError(f"Column {col!r} not found in data")

    dates = pd.to_datetime(data[date_col])
    if dates.dt.tz is not None:
        dates = dates.dt.tz_localize(None)
    has_date = dates.notna()
    n_missing = int((~has_date).sum())

    if count_col is None:
        counts = pd.Series(1, index=data.index)
    else:
        counts = data[count_col]
        if counts.isna().any() or (counts < 0).any() or (counts % 1 != 0).any():
            raise ValueError(
                f"Column {count_col!r} must contain whole numbers of zero or "
                "more, with no missing values"
            )

    output_cols = ["period_start", "cases"]
    if group_col is not None:
        output_cols.insert(1, group_col)

    if not has_date.any():
        empty = pd.DataFrame({col: [] for col in output_cols})
        empty["period_start"] = pd.to_datetime(empty["period_start"])
        empty["cases"] = empty["cases"].astype("int64")
        empty.attrs["n_missing_dates"] = n_missing
        return empty

    # Move each date back to the first day of its period.
    days = dates[has_date].dt.normalize()
    if interval == "week":
        weekday = days.dt.dayofweek
        shift = weekday if week_start == "monday" else (weekday + 1) % 7
    elif interval == "month":
        shift = days.dt.day - 1
    else:
        shift = pd.Series(0, index=days.index)
    starts = days - pd.to_timedelta(shift, unit="D")

    table = pd.DataFrame({"period_start": starts, "cases": counts[has_date]})

    frequency = (
        _WEEK_FREQUENCIES[week_start] if interval == "week" else _FREQUENCIES[interval]
    )
    all_periods = pd.date_range(
        starts.min(), starts.max(), freq=frequency, name="period_start"
    )

    if group_col is None:
        summed = table.groupby("period_start")["cases"].sum()
        result = summed.reindex(all_periods, fill_value=0).reset_index()
    else:
        groups = data.loc[has_date, group_col]
        if isinstance(groups.dtype, pd.CategoricalDtype):
            order = [str(c) for c in groups.cat.categories]
        else:
            order = sorted({str(g) for g in groups.dropna()})
        if groups.isna().any():
            order.append(MISSING_GROUP)
        table[group_col] = groups.astype("string").fillna(MISSING_GROUP).astype(str)

        summed = table.groupby(["period_start", group_col])["cases"].sum()
        full_index = pd.MultiIndex.from_product(
            [all_periods, order], names=["period_start", group_col]
        )
        result = summed.reindex(full_index, fill_value=0).reset_index()
        result[group_col] = pd.Categorical(result[group_col], categories=order)

    result["cases"] = result["cases"].astype("int64")
    result = result[output_cols]
    result.attrs["n_missing_dates"] = n_missing
    return result
