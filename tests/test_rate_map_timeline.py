from typing import Any

import pandas as pd
import pytest
from matplotlib.figure import Figure

from epiplot import rate_map_timeline
from epiplot.ratemap import _ordered_periods, _period_label

# Two years. In 2025, A is 100 and B is 200 per 100,000. In 2026, A is 400,
# B is hidden (2 cases), and C has no data because it has no row at all.
DATA = pd.DataFrame(
    {
        "area": ["A", "B", "C", "A", "B"],
        "year": [2025, 2025, 2025, 2026, 2026],
        "cases": [10, 20, 30, 40, 2],
        "population": [10_000] * 5,
    }
)


@pytest.fixture
def regions() -> Any:
    """Three square regions in a row."""
    geopandas = pytest.importorskip("geopandas")
    box = pytest.importorskip("shapely.geometry").box
    return geopandas.GeoDataFrame(
        {"area": ["A", "B", "C"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(2, 0, 3, 1)],
    )


def timeline(regions: Any, data: pd.DataFrame = DATA, **options: Any) -> Figure:
    return rate_map_timeline(
        regions,
        data,
        "area",
        "year",
        cases_col="cases",
        population_col="population",
        **options,
    )


def maps(figure: Figure) -> list[Any]:
    """The visible map axes, leaving out the colour scale."""
    return [ax for ax in figure.axes if ax.get_visible() and ax.get_title()]


def test_one_map_per_period_in_order(regions: Any) -> None:
    figure = timeline(regions)

    assert [ax.get_title() for ax in maps(figure)] == ["2025", "2026"]


def test_all_maps_share_one_colour_scale(regions: Any) -> None:
    figure = timeline(regions)

    # Each scale runs from 0 to the highest rate shown in any period.
    scales = [
        (ax.collections[0].norm.vmin, ax.collections[0].norm.vmax)
        for ax in maps(figure)
    ]
    assert scales == [(0, 400), (0, 400)]


def test_there_is_one_colour_scale_with_a_label(regions: Any) -> None:
    figure = timeline(regions)

    # The colour scale is the only visible part without a title.
    colour_scales = [
        ax for ax in figure.axes if ax.get_visible() and not ax.get_title()
    ]
    assert [ax.get_ylabel() for ax in colour_scales] == [
        "Crude rate per 100,000 people"
    ]


def test_legend_covers_hidden_and_missing_regions(regions: Any) -> None:
    figure = timeline(regions)

    assert len(figure.legends) == 1
    labels = [text.get_text() for text in figure.legends[0].get_texts()]
    assert labels == ["Fewer than 5 cases", "No data"]


def test_unused_grid_spaces_are_hidden(regions: Any) -> None:
    figure = timeline(regions, ncols=3)

    assert len(maps(figure)) == 2


def test_too_many_periods_raise_an_error(regions: Any) -> None:
    data = pd.DataFrame(
        {"area": "A", "year": range(25), "cases": 10, "population": 1000}
    )

    with pytest.raises(ValueError, match="at most 24"):
        timeline(regions, data)


def test_missing_period_column_raises_an_error(regions: Any) -> None:
    with pytest.raises(KeyError, match="week"):
        rate_map_timeline(
            regions,
            DATA,
            "area",
            "week",
            cases_col="cases",
            population_col="population",
        )


def test_periods_are_sorted() -> None:
    assert _ordered_periods(pd.Series([2026, 2024, 2025, 2024])) == [2024, 2025, 2026]


def test_categorical_period_order_is_kept() -> None:
    periods = pd.Series(
        pd.Categorical(["Summer", "Winter"], categories=["Winter", "Summer"])
    )

    assert _ordered_periods(periods) == ["Winter", "Summer"]


def test_dates_are_labelled_clearly() -> None:
    assert _period_label(pd.Timestamp("2026-03-02")) == "02 Mar 2026"
    assert _period_label(2026) == "2026"
