"""Epidemic curves (epicurves): counts of cases over time."""

import warnings
from typing import Literal

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.patches import Patch
from matplotlib.ticker import Formatter, MaxNLocator

from epiplot._warnings import EpiplotWarning

Interval = Literal["day", "week", "month"]
WeekStart = Literal["monday", "sunday"]
DateType = Literal["onset", "report", "specimen", "diagnosis", "other"]

MISSING_GROUP = "Missing"
"""Label used for cases whose group value is missing."""

_INTERVALS = ("day", "week", "month")
_WEEK_STARTS = ("monday", "sunday")
_FREQUENCIES = {"day": "D", "month": "MS"}
_WEEK_FREQUENCIES = {"monday": "W-MON", "sunday": "W-SUN"}

_DATE_TYPE_WORDS = {
    "onset": "symptom onset",
    "report": "report",
    "specimen": "specimen collection",
    "diagnosis": "diagnosis",
}
_INTERVAL_WORDS = {"day": "Date", "week": "Week", "month": "Month"}

# Colour-blind-safe colours, always used in this order so a group keeps its
# colour. Adjacent pairs are checked for colour-vision-deficiency separation.
_GROUP_COLORS = (
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
)
_MISSING_COLOR = "#a3a29d"  # neutral grey, so "Missing" never looks like data
_INCOMPLETE_COLOR = "#ecebe7"
_GRID_COLOR = "#e4e3de"
_TEXT_COLOR = "#52514e"


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
        count of zero where there were no cases. The number of cases left
        out because their date was missing is stored in
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

    if count_col is None:
        counts = pd.Series(1, index=data.index)
    else:
        counts = data[count_col]
        if counts.isna().any() or (counts < 0).any() or (counts % 1 != 0).any():
            raise ValueError(
                f"Column {count_col!r} must contain whole numbers of zero or "
                "more, with no missing values"
            )
    n_missing = int(counts[~has_date].sum())

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


def epicurve(
    data: pd.DataFrame,
    date_col: str,
    *,
    date_type: DateType | None = None,
    interval: Interval = "week",
    week_start: WeekStart = "monday",
    group_col: str | None = None,
    count_col: str | None = None,
    incomplete_after: str | pd.Timestamp | None = None,
    ax: Axes | None = None,
) -> Axes:
    """Plot an epidemic curve: the number of cases in each time period.

    Parameters
    ----------
    data
        A table with one row per case (a line list), or one row per count
        if ``count_col`` is given.
    date_col
        Name of the column holding the dates.
    date_type
        What the dates mean: ``"onset"``, ``"report"``, ``"specimen"`` or
        ``"diagnosis"``. This sets the x-axis label. Use ``"other"`` to get a
        plain label you can replace with ``ax.set_xlabel()``. If not given,
        an :class:`~epiplot.EpiplotWarning` is shown and the axis says the
        date type was not specified.
    interval
        Length of each bar: ``"day"``, ``"week"`` or ``"month"``.
    week_start
        First day of each week when ``interval="week"``: ``"monday"`` for
        ISO weeks or ``"sunday"`` for US CDC (MMWR) weeks.
    group_col
        Optional column to split each bar by, such as travel history. Up to
        eight groups are shown in colour-blind-safe colours, plus a grey
        ``"Missing"`` group for cases with no value.
    count_col
        Optional column holding a count for each row. If not given, each row
        counts as one case.
    incomplete_after
        Optional date after which data may be incomplete, for example
        because of reporting delays. That part of the plot is shaded and
        explained in the legend.
    ax
        Optional Matplotlib axes to draw on. If not given, a new figure is
        created.

    Returns
    -------
    matplotlib.axes.Axes
        The axes the epicurve was drawn on, for further customisation.

    Raises
    ------
    ValueError
        If an option is not recognised, or if there are more than eight
        groups (combine smaller groups into an "Other" group first).

    See Also
    --------
    count_cases : The counts behind the plot, as a table.
    """
    valid_date_types = (*_DATE_TYPE_WORDS, "other")
    if date_type is not None and date_type not in valid_date_types:
        raise ValueError(
            f"date_type must be one of {valid_date_types}, not {date_type!r}"
        )
    if date_type is None:
        warnings.warn(
            "date_type not given. Epicurves should state what the dates mean, "
            "for example date_type='onset', 'report', 'specimen' or 'diagnosis'. "
            "Use date_type='other' to label the axis yourself.",
            EpiplotWarning,
            stacklevel=2,
        )

    counts = count_cases(
        data,
        date_col,
        interval=interval,
        week_start=week_start,
        group_col=group_col,
        count_col=count_col,
    )

    groups: list[str] = []
    if group_col is not None:
        groups = [str(g) for g in counts[group_col].cat.categories]
        n_data_groups = sum(g != MISSING_GROUP for g in groups)
        if n_data_groups > len(_GROUP_COLORS):
            raise ValueError(
                f"group_col has {n_data_groups} groups, but at most "
                f"{len(_GROUP_COLORS)} can be told apart by colour. Combine "
                "smaller groups into an 'Other' group first."
            )

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    _style_axes(ax)
    ax.set_xlabel(
        _x_label(date_type, interval, week_start, counts.attrs["n_missing_dates"])
    )
    ax.set_ylabel("Number of cases")

    if counts.empty:
        ax.text(
            0.5,
            0.5,
            "No cases with a known date",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=_TEXT_COLOR,
        )
        return ax

    # Each bar runs from the start of its period to the start of the next.
    frequency = (
        _WEEK_FREQUENCIES[week_start] if interval == "week" else _FREQUENCIES[interval]
    )
    starts = pd.DatetimeIndex(counts["period_start"].unique())
    edges = pd.date_range(starts[0], periods=len(starts) + 1, freq=frequency)
    edge_nums = np.asarray(mdates.date2num(edges.to_numpy()), dtype=np.float64)
    left = edge_nums[:-1]
    widths = np.diff(edge_nums)

    handles: list[Patch] = []
    if group_col is None:
        ax.bar(
            left,
            counts["cases"].to_numpy(),
            width=widths,
            align="edge",
            color=_GROUP_COLORS[0],
            edgecolor="white",
            linewidth=0.8,
            zorder=2,
        )
    else:
        bottom = np.zeros(len(left))
        colors = iter(_GROUP_COLORS)
        for group in groups:
            heights = counts.loc[counts[group_col] == group, "cases"].to_numpy()
            color = _MISSING_COLOR if group == MISSING_GROUP else next(colors)
            ax.bar(
                left,
                heights,
                width=widths,
                bottom=bottom,
                align="edge",
                color=color,
                edgecolor="white",
                linewidth=0.8,
                label=group,
                zorder=2,
            )
            bottom = bottom + heights
            handles.append(Patch(facecolor=color, label=group))
        # List groups top to bottom, in the same order as the stacked bars.
        handles.reverse()

    if incomplete_after is not None:
        cutoff = pd.Timestamp(incomplete_after)
        if cutoff < edges[-1]:
            ax.axvspan(
                float(mdates.date2num(max(cutoff, edges[0]))),
                float(edge_nums[-1]),
                color=_INCOMPLETE_COLOR,
                linewidth=0,
                zorder=0,
            )
            handles.append(
                Patch(
                    facecolor=_INCOMPLETE_COLOR, label="Recent data may be incomplete"
                )
            )

    if handles:
        ax.legend(
            handles=handles,
            title=group_col,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            frameon=False,
            alignment="left",
        )

    locator = _date_locator(interval, week_start, len(starts))
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(
        _DateTickFormatter("%b" if interval == "month" else "%d %b")
    )
    ax.set_xlim(float(edge_nums[0]), float(edge_nums[-1]))
    ax.set_ylim(bottom=0)
    return ax


def _x_label(
    date_type: DateType | None,
    interval: Interval,
    week_start: WeekStart,
    n_missing: int,
) -> str:
    """Build the x-axis label, including any notes the reader needs."""
    label = _INTERVAL_WORDS[interval]
    if date_type in _DATE_TYPE_WORDS:
        label += f" of {_DATE_TYPE_WORDS[date_type]}"

    notes = []
    if date_type is None:
        notes.append("date type not specified")
    if interval == "week":
        notes.append(f"weeks start on {week_start.capitalize()}")
    if notes:
        label += f" ({'; '.join(notes)})"

    if n_missing:
        what = _DATE_TYPE_WORDS.get(date_type or "", "")
        missing_date = f"missing {what} date" if what else "missing date"
        cases = "case" if n_missing == 1 else "cases"
        label += f"\n{n_missing} {cases} with {missing_date} not shown"
    return label


def _date_locator(
    interval: Interval, week_start: WeekStart, n_periods: int, max_ticks: int = 12
) -> mdates.DateLocator:
    """Place ticks at the start of periods, so they line up with the bars."""
    step = max(1, -(-n_periods // max_ticks))  # round up
    if interval == "day":
        return mdates.DayLocator(interval=step)
    if interval == "week":
        weekday = mdates.MO if week_start == "monday" else mdates.SU
        return mdates.WeekdayLocator(byweekday=weekday, interval=step)
    return mdates.MonthLocator(interval=step)


class _DateTickFormatter(Formatter):
    """Label ticks with the day and month, adding the year below the first
    tick and wherever the year changes, so every date is unambiguous."""

    def __init__(self, date_format: str) -> None:
        self.date_format = date_format

    def __call__(self, x: float, pos: int | None = None) -> str:
        return str(mdates.num2date(x).strftime(self.date_format))

    def format_ticks(self, values: list[float]) -> list[str]:
        labels = []
        previous_year = None
        for value in values:
            date = mdates.num2date(value)
            label = str(date.strftime(self.date_format))
            if date.year != previous_year:
                label += f"\n{date.year}"
                previous_year = date.year
            labels.append(label)
        return labels


def _style_axes(ax: Axes) -> None:
    """Apply a quiet style, so the data stands out."""
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(_TEXT_COLOR)
    ax.tick_params(colors=_TEXT_COLOR, length=3)
    ax.tick_params(axis="y", length=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.grid(True, color=_GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(_TEXT_COLOR)
    ax.yaxis.label.set_color(_TEXT_COLOR)
