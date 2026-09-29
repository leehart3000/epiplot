"""Crude rates per population, with confidence intervals."""

import numpy as np
import pandas as pd
from scipy import stats

SHOWN = "shown"
HIDDEN = "hidden"
NO_DATA = "no data"
STATUSES = (SHOWN, HIDDEN, NO_DATA)
"""The possible values of the ``status`` column, in order."""


def calculate_rates(
    data: pd.DataFrame,
    region_col: str,
    cases_col: str,
    population_col: str,
    *,
    per: float = 100_000,
    min_cases: int = 5,
    period_col: str | None = None,
    confidence: float = 0.95,
) -> pd.DataFrame:
    """Calculate crude rates per population, with exact confidence intervals.

    Parameters
    ----------
    data
        A table with one row per region, or one row per region and period
        if ``period_col`` is given.
    region_col
        Name of the column identifying each region, such as an area code.
    cases_col
        Name of the column holding the number of cases.
    population_col
        Name of the column holding the population.
    per
        The rate is given per this many people, for example 100,000.
    min_cases
        Regions with fewer cases than this are marked ``"hidden"``, because
        rates from very small numbers are unreliable and may identify
        individuals.
    period_col
        Optional column holding a time period, such as a week or year, for
        rates over time.
    confidence
        Confidence level for the interval, for example 0.95 for 95%.

    Returns
    -------
    pandas.DataFrame
        One row per region (and period), with the columns ``region_col``,
        ``period_col`` (if given), ``cases``, ``population``, ``rate``,
        ``rate_lower``, ``rate_upper`` and ``status``. The confidence
        interval uses the exact Poisson method, which is accurate even for
        small counts. ``status`` is ``"shown"``, ``"hidden"`` (fewer than
        ``min_cases`` cases) or ``"no data"`` (cases or population missing,
        or a population of zero). Rates are still calculated for hidden
        regions, so remove them before publishing the table.

    Raises
    ------
    KeyError
        If a named column is not in ``data``.
    ValueError
        If a region appears more than once (per period), if cases are not
        whole numbers of zero or more, if a population is negative, or if
        ``per``, ``min_cases`` or ``confidence`` is out of range.
    """
    for col in (region_col, cases_col, population_col, period_col):
        if col is not None and col not in data.columns:
            raise KeyError(f"Column {col!r} not found in data")
    if per <= 0:
        raise ValueError(f"per must be more than 0, not {per!r}")
    if min_cases < 0:
        raise ValueError(f"min_cases must be 0 or more, not {min_cases!r}")
    if not 0 < confidence < 1:
        raise ValueError(f"confidence must be between 0 and 1, not {confidence!r}")

    keys = [region_col] if period_col is None else [region_col, period_col]
    duplicated = data.duplicated(subset=keys, keep=False)
    if duplicated.any():
        where = region_col if period_col is None else f"{region_col} and {period_col}"
        raise ValueError(
            f"{int(duplicated.sum())} rows share the same {where}. Combine them "
            "into one row each first (for example with groupby and sum), "
            "adding up populations only if the rows are separate groups."
        )

    cases = pd.to_numeric(data[cases_col])
    population = pd.to_numeric(data[population_col])
    known_cases = cases.dropna()
    if (known_cases < 0).any() or (known_cases % 1 != 0).any():
        raise ValueError(
            f"Column {cases_col!r} must contain whole numbers of 0 or more"
        )
    if (population.dropna() < 0).any():
        raise ValueError(f"Column {population_col!r} must not contain negative numbers")

    no_data = (cases.isna() | population.isna() | (population == 0)).to_numpy()
    k = np.where(no_data, np.nan, cases.to_numpy(dtype=np.float64))
    pop = np.where(no_data, np.nan, population.to_numpy(dtype=np.float64))
    hidden = ~no_data & (np.nan_to_num(k) < min_cases)

    # Exact (Garwood) Poisson confidence interval for the number of cases.
    alpha = 1 - confidence
    k_safe = np.where(np.isnan(k), 0.0, k)
    lower = np.where(
        k_safe > 0, stats.chi2.ppf(alpha / 2, 2 * np.maximum(k_safe, 1)) / 2, 0.0
    )
    upper = stats.chi2.ppf(1 - alpha / 2, 2 * k_safe + 2) / 2

    result = data[keys].copy()
    result["cases"] = cases
    result["population"] = population
    result["rate"] = k / pop * per
    result["rate_lower"] = np.where(no_data, np.nan, lower / pop * per)
    result["rate_upper"] = np.where(no_data, np.nan, upper / pop * per)
    status = np.select([no_data, hidden], [NO_DATA, HIDDEN], default=SHOWN)
    result["status"] = pd.Categorical(status, categories=STATUSES)

    result = result.reset_index(drop=True)
    result.attrs["per"] = per
    result.attrs["min_cases"] = min_cases
    result.attrs["confidence"] = confidence
    return result
