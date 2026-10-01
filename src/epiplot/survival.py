"""Kaplan-Meier survival estimates, with confidence intervals."""

import numpy as np
import numpy.typing as npt
import pandas as pd
from scipy import stats

_MISSING_GROUP = "Missing"
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
