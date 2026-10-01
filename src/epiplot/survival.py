"""Survival curves: Kaplan-Meier estimates, with confidence intervals."""

import warnings
from collections.abc import Sequence
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator, MultipleLocator, PercentFormatter
from scipy import stats

from epiplot._warnings import EpiplotWarning
from epiplot.epicurve import (
    _GRID_COLOR,
    _GROUP_COLORS,
    _MISSING_COLOR,
    _TEXT_COLOR,
    MISSING_GROUP,
    _style_axes,
)

TimeUnit = Literal["days", "weeks", "months", "years", "other"]

_MISSING_GROUP = MISSING_GROUP
_TIME_UNITS = ("days", "weeks", "months", "years", "other")
_BAND_ALPHA = 0.18
_ROW_HEIGHT = 12  # points between rows of the number-at-risk table
_COLUMNS = [
    "time",
    "at_risk",
    "events",
    "censored",
    "survival",
    "survival_lower",
    "survival_upper",
]


def kaplan_meier(
    data: pd.DataFrame,
    time_col: str,
    event_col: str,
    *,
    group_col: str | None = None,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Estimate the share of people still free of the event over time.

    Uses the Kaplan-Meier method, which allows for people who leave the
    study early or have not had the event by the end ("censored" people).

    Parameters
    ----------
    data
        A table with one row per person.
    time_col
        Name of the column holding each person's follow-up time, such as
        days from diagnosis to the event or to the end of follow-up.
    event_col
        Name of the column saying whether the event happened (1 or True)
        or the person was censored (0 or False).
    group_col
        Optional column to estimate a separate curve for each group, such
        as treatment. Missing values are grouped as ``"Missing"``.
    confidence
        Confidence level for the interval, for example 0.95 for 95%.

    Returns
    -------
    pandas.DataFrame
        One row per time at which something happened, plus a first row at
        time 0, with the columns ``group_col`` (if given), ``time``,
        ``at_risk``, ``events``, ``censored``, ``survival``,
        ``survival_lower`` and ``survival_upper``. ``at_risk`` counts the
        people still being followed just before that time. People censored
        at the same time as an event are counted as at risk of it. The
        confidence interval uses the log-log method, which keeps it between
        0 and 1. It is missing once survival reaches 0. The number of rows
        left out because the time or event was missing is in
        ``result.attrs["n_missing"]``.

    Raises
    ------
    KeyError
        If a named column is not in ``data``.
    ValueError
        If a time is negative, if an event is not 0, 1, True or False, or
        if ``confidence`` is out of range.
    """
    for col in (time_col, event_col, group_col):
        if col is not None and col not in data.columns:
            raise KeyError(f"Column {col!r} not found in data")
    if not 0 < confidence < 1:
        raise ValueError(f"confidence must be between 0 and 1, not {confidence!r}")

    time = pd.to_numeric(data[time_col])
    event = data[event_col]
    missing = time.isna() | event.isna()

    time = time[~missing].astype(np.float64)
    event = event[~missing]
    if (time < 0).any():
        raise ValueError(f"Column {time_col!r} must not contain negative times")
    if not event.isin([0, 1]).all():
        raise ValueError(
            f"Column {event_col!r} must contain only 1 or True (event) "
            "and 0 or False (censored)"
        )
    time_values = np.asarray(time, dtype=np.float64)
    event_values = np.asarray(event, dtype=np.bool_)

    if group_col is None:
        result = _estimate(time_values, event_values, confidence)
    else:
        groups = _group_labels(data.loc[~missing, group_col])
        parts = []
        for name in groups.cat.categories:
            in_group = (groups == name).to_numpy()
            if not in_group.any():
                continue
            part = _estimate(time_values[in_group], event_values[in_group], confidence)
            part.insert(0, group_col, name)
            parts.append(part)
        if parts:
            result = pd.concat(parts, ignore_index=True)
        else:
            result = pd.DataFrame(columns=[group_col, *_COLUMNS])
        result[group_col] = pd.Categorical(
            result[group_col], categories=groups.cat.categories
        )

    result.attrs["n_missing"] = int(missing.sum())
    result.attrs["confidence"] = confidence
    return result


def _group_labels(groups: pd.Series) -> pd.Series:
    """Return the groups as a categorical, with missing values last."""
    if isinstance(groups.dtype, pd.CategoricalDtype):
        categories = list(groups.cat.categories)
        groups = groups.astype(object)
    else:
        categories = sorted(groups.dropna().unique().tolist())
    if groups.isna().any():
        categories.append(_MISSING_GROUP)
        groups = groups.where(groups.notna(), _MISSING_GROUP)
    return pd.Series(pd.Categorical(groups, categories=categories))


def _estimate(
    time: npt.NDArray[np.float64], event: npt.NDArray[np.bool_], confidence: float
) -> pd.DataFrame:
    """Kaplan-Meier estimate for one group."""
    times = np.unique(time)
    events = np.array([np.sum(event & (time == t)) for t in times])
    censored = np.array([np.sum(~event & (time == t)) for t in times])
    at_risk = np.array([np.sum(time >= t) for t in times])

    survival = np.cumprod(1 - events / at_risk)

    # Greenwood's sum, used for the log-log confidence interval.
    with np.errstate(divide="ignore", invalid="ignore"):
        greenwood = np.cumsum(events / (at_risk * (at_risk - events)))
        se_loglog = np.sqrt(greenwood) / np.abs(np.log(survival))
        z = stats.norm.ppf(1 - (1 - confidence) / 2)
        lower = survival ** np.exp(z * se_loglog)
        upper = survival ** np.exp(-z * se_loglog)
    no_events_yet = survival == 1
    lower[no_events_yet] = 1.0
    upper[no_events_yet] = 1.0
    lower[survival == 0] = np.nan
    upper[survival == 0] = np.nan

    table = pd.DataFrame(
        {
            "time": times,
            "at_risk": at_risk,
            "events": events,
            "censored": censored,
            "survival": survival,
            "survival_lower": lower,
            "survival_upper": upper,
        }
    )
    if len(times) == 0 or times[0] > 0:
        start = pd.DataFrame(
            {
                "time": [0.0],
                "at_risk": [len(time)],
                "events": [0],
                "censored": [0],
                "survival": [1.0],
                "survival_lower": [1.0],
                "survival_upper": [1.0],
            }
        )
        table = pd.concat([start, table], ignore_index=True)
    return table


def survival_curve(
    data: pd.DataFrame,
    time_col: str,
    event_col: str,
    *,
    time_unit: TimeUnit | None = None,
    group_col: str | None = None,
    confidence: float = 0.95,
    at_risk_times: Sequence[float] | None = None,
    ax: Axes | None = None,
) -> Axes:
    """Plot Kaplan-Meier survival curves, with a number-at-risk table.

    Each curve shows the share of people still free of the event over time,
    with a shaded confidence band. Small tick marks show when people were
    censored. The table under the plot shows how many people were still
    being followed at each labelled time, because the right-hand end of a
    curve often rests on very few people.

    Parameters
    ----------
    data
        A table with one row per person.
    time_col
        Name of the column holding each person's follow-up time.
    event_col
        Name of the column saying whether the event happened (1 or True)
        or the person was censored (0 or False).
    time_unit
        What the times are measured in: ``"days"``, ``"weeks"``,
        ``"months"`` or ``"years"``. This sets the x-axis label. Use
        ``"other"`` to get a plain label you can replace with
        ``ax.set_xlabel()``. If not given, an :class:`~epiplot.EpiplotWarning`
        is shown and the axis says the unit was not specified.
    group_col
        Optional column to draw a separate curve for each group, such as
        treatment. Up to eight groups are shown in colour-blind-safe
        colours, plus a grey ``"Missing"`` group for people with no value.
    confidence
        Confidence level for the shaded band, for example 0.95 for 95%.
    at_risk_times
        Optional times at which to show the number at risk. If not given,
        the labelled times on the x axis are used.
    ax
        Optional Matplotlib axes to draw on. If not given, a new figure is
        created.

    Returns
    -------
    matplotlib.axes.Axes
        The axes the curves were drawn on, for further customisation.

    Raises
    ------
    ValueError
        If an option is not recognised, or if there are more than eight
        groups.

    See Also
    --------
    kaplan_meier : The estimates behind the plot, as a table.
    """
    if time_unit is not None and time_unit not in _TIME_UNITS:
        raise ValueError(f"time_unit must be one of {_TIME_UNITS}, not {time_unit!r}")
    if time_unit is None:
        warnings.warn(
            "time_unit not given. Survival curves should state what the times "
            "are measured in, for example time_unit='days', 'weeks', 'months' "
            "or 'years'. Use time_unit='other' to label the axis yourself.",
            EpiplotWarning,
            stacklevel=2,
        )

    estimates = kaplan_meier(
        data, time_col, event_col, group_col=group_col, confidence=confidence
    )

    groups: list[str | None] = [None]
    if group_col is not None:
        groups = [str(g) for g in estimates[group_col].cat.categories]
        n_data_groups = sum(g != _MISSING_GROUP for g in groups)
        if n_data_groups > len(_GROUP_COLORS):
            raise ValueError(
                f"group_col has {n_data_groups} groups, but at most "
                f"{len(_GROUP_COLORS)} can be told apart by colour. Combine "
                "smaller groups into an 'Other' group first."
            )
        present = set(estimates[group_col].astype(str))
        groups = [g for g in groups if g in present]

    if ax is None:
        height = 4.5 + 0.18 * (len(groups) + 1)
        _, ax = plt.subplots(figsize=(8, height), layout="constrained")
    _style_axes(ax)
    ax.set_xlabel(_time_label(time_unit))
    ax.set_ylabel("Survival")
    ax.yaxis.set_major_locator(MultipleLocator(0.2))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    ax.set_ylim(0, 1.02)

    max_time = float(estimates["time"].max()) if len(estimates) else 0.0
    if max_time <= 0:
        ax.text(
            0.5,
            0.5,
            "No follow-up time to show",
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=_TEXT_COLOR,
        )
        return ax

    if at_risk_times is None:
        ticks = MaxNLocator(nbins=7, steps=[1, 2, 2.5, 5, 10]).tick_values(0, max_time)
        times = [float(t) for t in ticks if 0 <= t <= max_time]
    else:
        times = sorted(float(t) for t in at_risk_times)
    ax.set_xticks(times)
    ax.set_xlim(0, max_time)
    # Faint lines at each labelled time, to lead the eye down to the table.
    ax.xaxis.grid(True, color=_GRID_COLOR, linewidth=0.8)

    colors = iter(_GROUP_COLORS)
    handles: list[Line2D | Patch] = []
    rows: list[tuple[str | None, str, list[int]]] = []
    for group in groups:
        if group is None:
            table = estimates
            color = _GROUP_COLORS[0]
        else:
            table = estimates[estimates[group_col].astype(str) == group]
            color = _MISSING_COLOR if group == _MISSING_GROUP else next(colors)
        _draw_curve(ax, table, color)
        if group is not None:
            handles.append(Line2D([], [], color=color, linewidth=2, label=group))
        rows.append((group, color, _numbers_at_risk(table, times)))

    if handles:
        groups_legend = ax.legend(
            handles=handles,
            title=group_col[:1].upper() + group_col[1:] if group_col else None,
            loc="upper left",
            bbox_to_anchor=(1.01, 1),
            frameon=False,
            alignment="left",
        )
        ax.add_artist(groups_legend)  # keep it when the second legend is added

    # A separate key for the shading and tick marks, in neutral grey because
    # they apply to every curve.
    marks: list[Line2D | Patch] = []
    marks.append(
        Patch(
            facecolor=_TEXT_COLOR,
            alpha=_BAND_ALPHA,
            label=f"{confidence:.0%} confidence\ninterval",
        )
    )
    marks.append(
        Line2D(
            [],
            [],
            linestyle="none",
            marker="|",
            markersize=7,
            markeredgewidth=1.2,
            color=_TEXT_COLOR,
            label="Censored",
        )
    )
    ax.legend(
        handles=marks,
        title="Shading and ticks",
        loc="lower left",
        bbox_to_anchor=(1.01, 0),
        frameon=False,
        alignment="left",
    )

    _draw_at_risk_table(ax, times, rows)
    _draw_notes(ax, estimates.attrs["n_missing"], len(rows))
    return ax


def _time_label(time_unit: TimeUnit | None) -> str:
    """Build the x-axis title, saying what the times are measured in."""
    if time_unit is None:
        return "Time (unit not specified)"
    if time_unit == "other":
        return "Time"
    return f"Time ({time_unit})"


def _draw_curve(ax: Axes, table: pd.DataFrame, color: str) -> None:
    """Draw one Kaplan-Meier curve, its band and its censoring ticks."""
    time = np.concatenate([[0.0], table["time"].to_numpy(dtype=np.float64)])
    survival = np.concatenate([[1.0], table["survival"].to_numpy(dtype=np.float64)])
    lower = np.concatenate([[1.0], table["survival_lower"].to_numpy(dtype=np.float64)])
    upper = np.concatenate([[1.0], table["survival_upper"].to_numpy(dtype=np.float64)])

    ax.fill_between(
        time, lower, upper, step="post", color=color, alpha=_BAND_ALPHA, linewidth=0
    )
    ax.step(time, survival, where="post", color=color, linewidth=2, zorder=3)

    censored = table["censored"].to_numpy() > 0
    ax.plot(
        table["time"].to_numpy()[censored],
        table["survival"].to_numpy()[censored],
        linestyle="none",
        marker="|",
        markersize=7,
        markeredgewidth=1.2,
        color=color,
        zorder=4,
    )


def _numbers_at_risk(table: pd.DataFrame, times: list[float]) -> list[int]:
    """Count the people still being followed just before each time."""
    left = table["events"] + table["censored"]
    return [int(left[table["time"] >= t].sum()) for t in times]


def _draw_at_risk_table(
    ax: Axes, times: list[float], rows: list[tuple[str | None, str, list[int]]]
) -> None:
    """Write the number-at-risk table under the x-axis title."""

    def write(text: str, x: float, row: int, coords: str, ha: str, color: str) -> None:
        ax.annotate(
            text,
            xy=(x, 0),
            xycoords=(coords, ax.xaxis.label),
            xytext=(-8 if coords == "axes fraction" else 0, -6 - _ROW_HEIGHT * row),
            textcoords="offset points",
            va="top",
            fontsize=8,
            ha=ha,
            color=color,
        )

    write("Number at risk:", 0, 0, "axes fraction", "right", _TEXT_COLOR)
    for row, (group, color, numbers) in enumerate(rows, start=1):
        if group is not None:
            write(group, 0, row, "axes fraction", "right", color)
        for t, n in zip(times, numbers, strict=True):
            write(str(n), t, row, "data", "center", _TEXT_COLOR)


def _draw_notes(ax: Axes, n_missing: int, n_rows: int) -> None:
    """Write a note under the number-at-risk table about people left out."""
    if not n_missing:
        return
    people = "person" if n_missing == 1 else "people"
    ax.annotate(
        f"{n_missing} {people} with missing time or event not shown.",
        xy=(0.5, 0),
        xycoords=("axes fraction", ax.xaxis.label),
        xytext=(0, -10 - _ROW_HEIGHT * (n_rows + 1)),
        textcoords="offset points",
        ha="center",
        va="top",
        fontsize=8,
        color=_TEXT_COLOR,
    )
