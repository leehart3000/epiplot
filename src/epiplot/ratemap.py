"""Maps of rates by region (choropleth maps)."""

import importlib
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
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator
from numpy.typing import NDArray

from epiplot._warnings import EpiplotWarning
from epiplot.rates import HIDDEN, NO_DATA, SHOWN, STATUSES, calculate_rates

# One colour, from very light to dark: darker simply means a higher rate.
RATE_COLORS = LinearSegmentedColormap.from_list(
    "epiplot_rates", ["#eaf2fc", "#2a78d6", "#0f3566"]
)
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
    """
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
            stacklevel=2,
        )

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

    unmatched = len(set(table[region_col]) - set(geo[region_col]))
    if unmatched:
        what = "region in data has" if unmatched == 1 else "regions in data have"
        warnings.warn(
            f"{unmatched} {what} no matching shape in regions, so "
            "can't be shown on the map.",
            EpiplotWarning,
            stacklevel=2,
        )

    shapes = geo[[region_col, geo.geometry.name]]
    merged = shapes.merge(table, on=region_col, how="left")
    merged["status"] = merged["status"].astype("object").fillna(NO_DATA)

    shown_rates = merged.loc[merged["status"] == SHOWN, "rate"]
    norm = _make_norm(shown_rates.to_numpy(dtype=np.float64), bands)

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6), layout="constrained")
    handles = _draw_regions(ax, merged, norm, min_cases)
    ax.set_axis_off()
    ax.margins(0)  # no gap around the map, so the legend lines up with it
    ax.set_axis_off()
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


def _import_geopandas() -> ModuleType:
    """Import GeoPandas, with a helpful message if it is not installed."""
    try:
        return importlib.import_module("geopandas")
    except ImportError as error:
        raise ImportError(
            'Maps need GeoPandas. Install it with: pip install "epiplot[maps]"'
        ) from error


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
) -> tuple[pd.DataFrame, str]:
    """Return a table of rates and statuses, and the colour scale label."""
    if rate_col is None:
        if cases_col is None or population_col is None:
            raise ValueError(
                "Give cases_col and population_col, so rates can be "
                "calculated, or rate_col for rates you have already calculated."
            )
        table = calculate_rates(
            data, region_col, cases_col, population_col, per=per, min_cases=min_cases
        )
        return table, f"Crude rate per {per:,g} people"

    if rate_label is None:
        raise ValueError(
            "rate_label is needed with rate_col, for example "
            "'Age-standardised rate per 100,000 people'."
        )
    for col in (region_col, rate_col, cases_col):
        if col is not None and col not in data.columns:
            raise KeyError(f"Column {col!r} not found in data")
    if data[region_col].duplicated().any():
        raise ValueError(
            f"Some rows share the same {region_col}. Give one row per region."
        )

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

    table = data[[region_col]].copy()
    table["rate"] = rate
    status = np.select([no_data, hidden], [NO_DATA, HIDDEN], default=SHOWN)
    table["status"] = pd.Categorical(status, categories=STATUSES)
    return table.reset_index(drop=True), rate_label


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
    styles = [
        (HIDDEN, _HIDDEN_FACE, _HIDDEN_EDGE, "////", f"Fewer than {min_cases} cases"),
        (NO_DATA, _NO_DATA_FACE, _NO_DATA_EDGE, "....", "No data"),
    ]
    for status, face, edge, hatch, label in styles:
        group = merged[merged["status"] == status]
        if len(group):
            group.plot(
                ax=ax, facecolor=face, edgecolor=edge, hatch=hatch, linewidth=0.5
            )
            areas = "area" if len(group) == 1 else "areas"
            handles.append(
                Patch(
                    facecolor=face,
                    edgecolor=edge,
                    hatch=hatch,
                    label=f"{label} ({len(group)} {areas})",
                )
            )
    return handles
