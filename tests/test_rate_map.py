import sys
from typing import Any

import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.colors import BoundaryNorm

from epiplot import EpiplotWarning, rate_map
from epiplot.ratemap import _make_norm

# Rates per 100,000: A is 100, B is 400, C is hidden (2 cases), D has no data.
DATA = pd.DataFrame(
    {"area": ["A", "B", "C"], "cases": [10, 40, 2], "population": [10_000] * 3}
)


@pytest.fixture
def regions() -> Any:
    """Four square regions, in a 2 by 2 grid."""
    geopandas = pytest.importorskip("geopandas")
    box = pytest.importorskip("shapely.geometry").box
    return geopandas.GeoDataFrame(
        {"area": ["A", "B", "C", "D"]},
        geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1), box(0, 1, 1, 2), box(1, 1, 2, 2)],
    )


def crude_map(regions: Any, data: pd.DataFrame = DATA) -> Axes:
    return rate_map(
        regions, data, "area", cases_col="cases", population_col="population"
    )


def legend_labels(ax: Axes) -> list[str]:
    legend = ax.get_legend()
    assert legend is not None
    return [text.get_text() for text in legend.get_texts()]


def colour_scale_label(ax: Axes) -> str:
    colour_scale = ax.figure.axes[-1]
    return colour_scale.get_ylabel()


def test_draws_a_map_without_axes(regions: Any) -> None:
    ax = crude_map(regions)

    assert isinstance(ax, Axes)
    assert not ax.axison


def test_higher_rates_are_darker(regions: Any) -> None:
    ax = crude_map(regions)
    ax.figure.canvas.draw()  # colours are worked out when the map is drawn

    # The first collection holds the shown regions, A (100) then B (400).
    colours = np.asarray(ax.collections[0].get_facecolor())
    brightness_a, brightness_b = colours[0][:3].sum(), colours[1][:3].sum()
    assert brightness_a > brightness_b


def test_colour_scale_is_labelled_as_crude_rates(regions: Any) -> None:
    ax = crude_map(regions)

    assert colour_scale_label(ax) == "Crude rate per 100,000 people"


def test_hidden_and_no_data_regions_are_in_the_legend(regions: Any) -> None:
    ax = crude_map(regions)

    assert legend_labels(ax) == ["Fewer than 5 cases (1 area)", "No data (1 area)"]


def test_regions_missing_from_the_map_give_a_warning(regions: Any) -> None:
    data = pd.concat(
        [DATA, pd.DataFrame({"area": ["E"], "cases": [9], "population": [100]})]
    )

    with pytest.warns(EpiplotWarning, match="1 region in data has no matching"):
        crude_map(regions, data)


def test_latitude_and_longitude_give_a_warning(regions: Any) -> None:
    with pytest.warns(EpiplotWarning, match="latitude and longitude"):
        crude_map(regions.set_crs("EPSG:4326"))


def test_rates_already_calculated_use_their_own_label(regions: Any) -> None:
    data = DATA.assign(asr=[90.0, 380.0, 50.0])

    ax = rate_map(
        regions,
        data,
        "area",
        cases_col="cases",
        rate_col="asr",
        rate_label="Age-standardised rate per 100,000 people",
    )

    assert colour_scale_label(ax) == "Age-standardised rate per 100,000 people"
    assert legend_labels(ax)[0] == "Fewer than 5 cases (1 area)"


def test_rates_without_cases_warn_that_small_numbers_are_not_hidden(
    regions: Any,
) -> None:
    data = DATA.assign(asr=[90.0, 380.0, 50.0])

    with pytest.warns(EpiplotWarning, match="can't be hidden"):
        ax = rate_map(regions, data, "area", rate_col="asr", rate_label="Rate")

    assert colour_scale_label(ax) == "Rate\n(small numbers not hidden)"


def test_rate_col_needs_a_label(regions: Any) -> None:
    with pytest.raises(ValueError, match="rate_label"):
        rate_map(regions, DATA.assign(asr=1.0), "area", rate_col="asr")


def test_cases_and_population_or_rates_are_needed(regions: Any) -> None:
    with pytest.raises(ValueError, match="population_col"):
        rate_map(regions, DATA, "area", cases_col="cases")


def test_regions_must_be_a_geodataframe() -> None:
    pytest.importorskip("geopandas")

    with pytest.raises(TypeError, match="GeoDataFrame"):
        rate_map(DATA, DATA, "area", cases_col="cases", population_col="population")


def test_missing_geopandas_gives_install_instructions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "geopandas", None)

    with pytest.raises(ImportError, match=r"epiplot\[maps\]"):
        rate_map(DATA, DATA, "area", cases_col="cases", population_col="population")


def test_smooth_colour_scale_starts_at_zero() -> None:
    norm = _make_norm(np.array([5.0, 20.0]), None)

    assert (norm.vmin, norm.vmax) == (0, 20)


def test_colour_bands_are_rounded() -> None:
    norm = _make_norm(np.array([37.0]), 4)

    assert isinstance(norm, BoundaryNorm)
    assert norm.boundaries.tolist() == [0, 10, 20, 30, 40]


def test_colour_bands_can_be_given() -> None:
    norm = _make_norm(np.array([15.0, 50.0]), [0, 10, 20])

    assert isinstance(norm, BoundaryNorm)
    assert norm.boundaries.tolist() == [0, 10, 20]
    assert norm.extend == "max"  # rates above the last band still get a colour


def test_invalid_colour_bands_raise_an_error() -> None:
    with pytest.raises(ValueError, match="increasing"):
        _make_norm(np.array([1.0]), [10, 0])
