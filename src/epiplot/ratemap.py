"""Maps of rates by region (choropleth maps), for one period or several."""

import importlib
import math
import warnings
from collections.abc import Sequence
from types import ModuleType
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from numpy.typing import NDArray

from epiplot._warnings import EpiplotWarning
from epiplot.rates import HIDDEN, NO_DATA, SHOWN, STATUSES, calculate_rates

# One colour, from very light to dark: darker simply means a higher rate.
RATE_COLORS = LinearSegmentedColormap.from_list(
    "epiplot_rates", ["#eaf2fc", "#2a78d6", "#0f3566"]
)
MAX_PERIODS = 24
"""The most small maps a timeline can show, so each stays readable."""

_BORDER_COLOR = "white"
_HIDDEN_FACE = "#e4e3de"
_HIDDEN_EDGE = "#8f8e89"
_NO_DATA_FACE = "white"
_NO_DATA_EDGE = "#b5b4af"


def rate_map(
    regions: pd.DataFrame,
    data: pd.DataFrame,
    region_col: str,
    *,
    cases_col: str | None = None,
    population_col: str | None = None,
    rate_col: str | None = None,
    rate_label: str | None = None,
    counted_over: str | None = None,
    per: float = 100_000,
    min_cases: int = 5,
    bands: int | Sequence[float] | None = None,
    ax: Axes | None = None,
) -> Axes:
    """Map rates by region, shading each region by its rate.

    Give either ``cases_col`` and ``population_col``, so crude rates are
    calculated, or ``rate_col`` and ``rate_label`` for rates you have already
    calculated, such as age-standardised rates.

    Parameters
    ----------
    regions
        A GeoPandas GeoDataFrame with one shape per region, and a
        ``region_col`` column identifying each region.
    data
        A table with one row per region.
    region_col
        Name of the column identifying each region, in both ``regions``
        and ``data``.
    cases_col
        Name of the column in ``data`` holding the number of cases. Also used
        with ``rate_col``, to hide regions with small numbers of cases.
    population_col
        Name of the column in ``data`` holding the population.
    rate_col
        Name of a column in ``data`` holding rates already calculated.
    rate_label
        What the rates are, for the colour scale, for example
        ``"Age-standardised rate per 100,000 people"``. Needed with
        ``rate_col``.
    counted_over
        The length of time the cases were counted over, such as ``"28 days"``
        or ``"1 year"``. It is added to the colour scale label, for example
        "Crude rate per 100,000 people over 28 days". This only labels the
        plot: epiplot can't check it, so make sure it matches your data.
    per
        The rate is given per this many people, for example 100,000.
    min_cases
        Regions with fewer cases than this are hidden, because rates from
        very small numbers are unreliable and may identify individuals.
    bands
        Leave out for a smooth colour scale starting at zero. Give a number,
        such as 5, to group rates into about that many colour bands, or a
        list of band boundaries, such as ``[0, 10, 20, 50]``.
    ax
        Optional Matplotlib axes to draw on. If not given, a new figure is
        created.

    Returns
    -------
    matplotlib.axes.Axes
        The axes the map was drawn on, for further customisation.

    Raises
    ------
    ImportError
        If GeoPandas is not installed. Install it with
        ``pip install "epiplot[maps]"``.
    ValueError
        If neither ``cases_col`` and ``population_col`` nor ``rate_col`` is
        given, or if ``rate_col`` is given without ``rate_label``.

    See Also
    --------
    calculate_rates : The crude rates behind the map, as a table.
    rate_map_timeline : One small map per period, sharing one colour scale.
    """
    geo = _check_regions(regions, region_col)
    table, label = _rate_table(
        data,
        region_col,
        cases_col=cases_col,
        population_col=population_col,
        rate_col=rate_col,
        rate_label=rate_label,
        per=per,
        min_cases=min_cases,
    )
    label = _add_period(label, counted_over)
    _warn_unmatched(table, geo, region_col)

    merged = _merge(geo, table, region_col)
    shown_rates = merged.loc[merged["status"] == SHOWN, "rate"]
    norm = _make_norm(shown_rates.to_numpy(dtype=np.float64), bands)

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6), layout="constrained")
    handles = _draw_regions(ax, merged, norm, min_cases)
    ax.set_axis_off()
    ax.margins(0)  # no gap around the map, so the legend lines up with it
    ax.figure.colorbar(
        ScalarMappable(norm=norm, cmap=RATE_COLORS), ax=ax, shrink=0.7, label=label
    )
    if handles:
        ax.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(0, -0.03),
            borderaxespad=0,
            borderpad=0,
            frameon=False,
            ncols=len(handles),
            handleheight=1.5,
        )
    return ax


def rate_map_timeline(
    regions: pd.DataFrame,
    data: pd.DataFrame,
    region_col: str,
    period_col: str,
    *,
    cases_col: str | None = None,
    population_col: str | None = None,
    rate_col: str | None = None,
    rate_label: str | None = None,
    counted_over: str | None = None,
    per: float = 100_000,
    min_cases: int = 5,
    bands: int | Sequence[float] | None = None,
    ncols: int | None = None,
) -> Figure:
    """Draw one small rate map per period, all sharing one colour scale.

    Every map uses the same colours for the same rates, so maps from
    different periods can be compared fairly. The options are the same as
    for :func:`rate_map`, plus ``period_col`` and ``ncols``.

    Parameters
    ----------
    regions
        A GeoPandas GeoDataFrame with one shape per region, and a
        ``region_col`` column identifying each region.
    data
        A table with one row per region and period.
    region_col
        Name of the column identifying each region, in both ``regions``
        and ``data``.
    period_col
        Name of the column in ``data`` holding the period, such as a year
        or the start of a week. Maps are shown in order of this column.
        Dates are labelled like "02 Mar 2026"; to label them differently,
        convert the column to text or an ordered categorical first.
    cases_col, population_col, rate_col, rate_label, counted_over, per, min_cases, bands
        As for :func:`rate_map`.
    ncols
        Number of maps in each row. If not given, up to 4.

    Returns
    -------
    matplotlib.figure.Figure
        The figure holding all the maps. Each map is in ``figure.axes``.

    Raises
    ------
    ImportError
        If GeoPandas is not installed. Install it with
        ``pip install "epiplot[maps]"``.
    ValueError
        If there are more than 24 periods (combine them into longer periods
        first), or for the same reasons as :func:`rate_map`.

    See Also
    --------
    rate_map : A single map.
    calculate_rates : The crude rates behind the maps, as a table.
    """
    geo = _check_regions(regions, region_col)
    if period_col not in data.columns:
        raise KeyError(f"Column {period_col!r} not found in data")
    table, label = _rate_table(
        data,
        region_col,
        cases_col=cases_col,
        population_col=population_col,
        rate_col=rate_col,
        rate_label=rate_label,
        per=per,
        min_cases=min_cases,
        period_col=period_col,
    )
    label = _add_period(label, counted_over)
    _warn_unmatched(table, geo, region_col)

    periods = _ordered_periods(table[period_col])
    if len(periods) > MAX_PERIODS:
        raise ValueError(
            f"There are {len(periods)} periods, but at most {MAX_PERIODS} maps "
            "can be shown readably. Combine them into longer periods first, "
            "for example months instead of weeks."
        )

    # One colour scale for every map, from the highest shown rate overall.
    shown_rates = table.loc[table["status"] == SHOWN, "rate"]
    norm = _make_norm(shown_rates.to_numpy(dtype=np.float64), bands)

    n = len(periods)
    cols = ncols if ncols is not None else min(n, 4)
    if cols < 1:
        raise ValueError(f"ncols must be 1 or more, not {cols!r}")
    rows = math.ceil(n / cols)
    figure, grid = plt.subplots(
        rows,
        cols,
        figsize=(2.6 * cols + 1.2, 2.6 * rows + 0.8),
        layout="constrained",
        squeeze=False,
    )
    axes = list(grid.flat)

    for ax, period in zip(axes, periods, strict=False):
        period_table = table[table[period_col] == period].drop(columns=period_col)
        merged = _merge(geo, period_table, region_col)
        _draw_regions(ax, merged, norm, min_cases)
        ax.set_title(_period_label(period), fontsize=10)
        ax.set_axis_off()
        ax.margins(0)
    for ax in axes[n:]:
        ax.set_visible(False)

    figure.colorbar(
        ScalarMappable(norm=norm, cmap=RATE_COLORS),
        ax=axes[:n],
        shrink=0.7,
        label=label,
    )
    statuses = set(table["status"].astype(str))
    has_missing_regions = any(
        set(geo[region_col]) - set(table.loc[table[period_col] == p, region_col])
        for p in periods
    )
    handles = _legend_handles(
        min_cases,
        hidden=HIDDEN in statuses,
        no_data=NO_DATA in statuses or has_missing_regions,
    )
    if handles:
        figure.legend(
            handles=handles,
            loc="outside lower left",
            frameon=False,
            ncols=len(handles),
            handleheight=1.5,
        )
    return figure


def _import_geopandas() -> ModuleType:
    """Import GeoPandas, with a helpful message if it is not installed."""
    try:
        return importlib.import_module("geopandas")
    except ImportError as error:
        raise ImportError(
            'Maps need GeoPandas. Install it with: pip install "epiplot[maps]"'
        ) from error


def _check_regions(regions: pd.DataFrame, region_col: str) -> Any:
    """Check the region shapes, and return them for loosely typed use."""
    geopandas = _import_geopandas()
    if not isinstance(regions, geopandas.GeoDataFrame):
        raise TypeError("regions must be a GeoPandas GeoDataFrame")
    geo: Any = regions  # GeoPandas has no type hints, so check it loosely.
    if region_col not in geo.columns:
        raise KeyError(f"Column {region_col!r} not found in regions")
    if geo.crs is not None and geo.crs.is_geographic:
        warnings.warn(
            "regions uses latitude and longitude, which stretches areas away "
            "from the equator. For a fairer map, convert it to a projected "
            "coordinate system first, for example with regions.to_crs().",
            EpiplotWarning,
            stacklevel=3,
        )
    return geo


def _warn_unmatched(table: pd.DataFrame, geo: Any, region_col: str) -> None:
    """Warn about regions in the data that have no shape to draw."""
    unmatched = len(set(table[region_col]) - set(geo[region_col]))
    if unmatched:
        what = "region in data has" if unmatched == 1 else "regions in data have"
        warnings.warn(
            f"{unmatched} {what} no matching shape in regions, so "
            "can't be shown on the map.",
            EpiplotWarning,
            stacklevel=3,
        )


def _merge(geo: Any, table: pd.DataFrame, region_col: str) -> Any:
    """Join rates to shapes. Shapes with no row in the table have no data."""
    shapes = geo[[region_col, geo.geometry.name]]
    merged = shapes.merge(table, on=region_col, how="left")
    merged["status"] = merged["status"].astype("object").fillna(NO_DATA)
    return merged


def _add_period(label: str, counted_over: str | None) -> str:
    """Add how long the cases were counted over to the colour scale label."""
    if counted_over is None:
        return label
    if not counted_over.strip():
        raise ValueError(
            "counted_over must describe a length of time, such as '28 days'"
        )
    first_line, newline, rest = label.partition("\n")
    return f"{first_line} over {counted_over.strip()}{newline}{rest}"


def _rate_table(
    data: pd.DataFrame,
    region_col: str,
    *,
    cases_col: str | None,
    population_col: str | None,
    rate_col: str | None,
    rate_label: str | None,
    per: float,
    min_cases: int,
    period_col: str | None = None,
) -> tuple[pd.DataFrame, str]:
    """Return a table of rates and statuses, and the colour scale label."""
    if rate_col is None:
        if cases_col is None or population_col is None:
            raise ValueError(
                "Give cases_col and population_col, so rates can be "
                "calculated, or rate_col for rates you have already calculated."
            )
        table = calculate_rates(
            data,
            region_col,
            cases_col,
            population_col,
            per=per,
            min_cases=min_cases,
            period_col=period_col,
        )
        return table, f"Crude rate per {per:,g} people"

    if rate_label is None:
        raise ValueError(
            "rate_label is needed with rate_col, for example "
            "'Age-standardised rate per 100,000 people'."
        )
    keys = [region_col] if period_col is None else [region_col, period_col]
    for col in (*keys, rate_col, cases_col):
        if col is not None and col not in data.columns:
            raise KeyError(f"Column {col!r} not found in data")
    if data.duplicated(subset=keys).any():
        per_what = "region" if period_col is None else "region and period"
        raise ValueError(f"Some rows are repeated. Give one row per {per_what}.")

    rate = pd.to_numeric(data[rate_col])
    no_data = rate.isna().to_numpy()
    if cases_col is None:
        warnings.warn(
            "cases_col not given, so regions with small numbers of cases "
            "can't be hidden.",
            EpiplotWarning,
            stacklevel=3,
        )
        hidden = np.zeros(len(data), dtype=bool)
        rate_label += "\n(small numbers not hidden)"
    else:
        cases = pd.to_numeric(data[cases_col]).to_numpy(dtype=np.float64)
        hidden = ~no_data & (np.nan_to_num(cases) < min_cases)

    table = data[keys].copy()
    table["rate"] = rate
    status = np.select([no_data, hidden], [NO_DATA, HIDDEN], default=SHOWN)
    table["status"] = pd.Categorical(status, categories=STATUSES)
    return table.reset_index(drop=True), rate_label


def _ordered_periods(periods: pd.Series) -> list[Any]:
    """Return the periods present, in order."""
    if isinstance(periods.dtype, pd.CategoricalDtype):
        present = set(periods.dropna())
        return [p for p in periods.cat.categories if p in present]
    return sorted(periods.dropna().unique())


def _period_label(period: Any) -> str:
    """Label a period for a map title."""
    if isinstance(period, pd.Timestamp | np.datetime64):
        return str(pd.Timestamp(period).strftime("%d %b %Y"))
    return str(period)


def _make_norm(
    rates: NDArray[np.float64], bands: int | Sequence[float] | None
) -> Normalize:
    """Map rates to colours: smoothly from zero, or in bands."""
    highest = float(np.nanmax(rates)) if np.any(~np.isnan(rates)) else 0.0
    top = highest if highest > 0 else 1.0
    if bands is None:
        return Normalize(vmin=0, vmax=top)

    if isinstance(bands, int):
        if bands < 1:
            raise ValueError(f"bands must be 1 or more, not {bands!r}")
        # Round boundaries, such as 0, 10, 20, 30, 40.
        ticks = np.asarray(MaxNLocator(nbins=bands).tick_values(0, top))
        boundaries = ticks[ticks >= 0].astype(np.float64)
    else:
        boundaries = np.asarray(bands, dtype=np.float64)
        if len(boundaries) < 2 or np.any(np.diff(boundaries) <= 0):
            raise ValueError("bands must be at least two numbers, in increasing order")
    if highest > boundaries[-1]:
        return BoundaryNorm(boundaries, ncolors=RATE_COLORS.N, extend="max")
    return BoundaryNorm(boundaries, ncolors=RATE_COLORS.N)


# How hidden and no-data regions are drawn: fill colour, edge colour, hatching.
_STYLES = {
    HIDDEN: (_HIDDEN_FACE, _HIDDEN_EDGE, "////"),
    NO_DATA: (_NO_DATA_FACE, _NO_DATA_EDGE, "...."),
}


def _style_patch(status: str, label: str) -> Patch:
    """A legend entry drawn in the style of a status."""
    face, edge, hatch = _STYLES[status]
    return Patch(facecolor=face, edgecolor=edge, hatch=hatch, label=label)


def _draw_regions(
    ax: Axes, merged: Any, norm: Normalize, min_cases: int
) -> list[Patch]:
    """Draw each group of regions in its own style, and return legend entries."""
    shown = merged[merged["status"] == SHOWN]
    if len(shown):
        shown.plot(
            ax=ax,
            column="rate",
            cmap=RATE_COLORS,
            norm=norm,
            edgecolor=_BORDER_COLOR,
            linewidth=0.5,
        )

    handles = []
    labels = {HIDDEN: f"Fewer than {min_cases} cases", NO_DATA: "No data"}
    for status, (face, edge, hatch) in _STYLES.items():
        group = merged[merged["status"] == status]
        if len(group):
            group.plot(
                ax=ax, facecolor=face, edgecolor=edge, hatch=hatch, linewidth=0.5
            )
            areas = "area" if len(group) == 1 else "areas"
            label = f"{labels[status]} ({len(group)} {areas})"
            handles.append(_style_patch(status, label))
    return handles


def _legend_handles(min_cases: int, *, hidden: bool, no_data: bool) -> list[Patch]:
    """Legend entries for a timeline, without counts, which vary by period."""
    handles = []
    if hidden:
        handles.append(_style_patch(HIDDEN, f"Fewer than {min_cases} cases"))
    if no_data:
        handles.append(_style_patch(NO_DATA, "No data"))
    return handles
