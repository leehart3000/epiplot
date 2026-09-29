import warnings

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.colors import to_hex

from epiplot import EpiplotWarning, epicurve

# 2026-03-02 and 2026-03-03 are in the same Monday week; 2026-03-17 is two
# weeks later, so there is an empty week in between.
CASES = pd.DataFrame(
    {
        "onset": ["2026-03-02", "2026-03-03", "2026-03-17"],
        "origin": ["local", "travel", None],
    }
)


def bar_heights(ax: Axes) -> list[float]:
    """Return the height of every bar, in drawing order."""
    return [bar.get_height() for container in ax.containers for bar in container]


def legend_labels(ax: Axes) -> list[str]:
    legend = ax.get_legend()
    assert legend is not None
    return [text.get_text() for text in legend.get_texts()]


def test_draws_one_bar_per_week_including_empty_weeks() -> None:
    ax = epicurve(CASES, "onset", date_type="onset")

    assert isinstance(ax, Axes)
    assert bar_heights(ax) == [2, 0, 1]


def test_missing_date_type_warns_and_says_so_on_the_axis() -> None:
    with pytest.warns(EpiplotWarning, match="date_type"):
        ax = epicurve(CASES, "onset")

    assert "date type not specified" in ax.get_xlabel()


def test_date_type_gives_a_clear_label_and_no_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ax = epicurve(CASES, "onset", date_type="onset")

    assert ax.get_xlabel() == "Week of symptom onset (weeks start on Monday)"


def test_other_date_type_gives_a_plain_label() -> None:
    ax = epicurve(CASES, "onset", date_type="other", interval="day")

    assert ax.get_xlabel() == "Date"


def test_unknown_date_type_raises_an_error() -> None:
    with pytest.raises(ValueError, match="date_type"):
        epicurve(CASES, "onset", date_type="death")  # type: ignore[arg-type]


def test_missing_dates_are_reported_on_the_axis() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", None]})

    ax = epicurve(data, "onset", date_type="onset")

    assert "1 case with missing symptom onset date not shown" in ax.get_xlabel()


def test_missing_dates_are_counted_as_cases_not_rows() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02", None], "n": [1, 4]})

    ax = epicurve(data, "onset", date_type="report", count_col="n")

    assert "4 cases with missing report date not shown" in ax.get_xlabel()


def test_groups_are_stacked_with_missing_in_grey() -> None:
    ax = epicurve(CASES, "onset", date_type="onset", group_col="origin")

    # Three groups, each with a bar for each of the three weeks.
    assert len(ax.containers) == 3
    assert bar_heights(ax) == [1, 0, 0, 1, 0, 0, 0, 0, 1]
    # The legend lists groups in the same order as the stack, top first.
    assert legend_labels(ax) == ["Missing", "travel", "local"]
    missing_bar = ax.containers[2][0]
    assert to_hex(missing_bar.get_facecolor()) == "#a3a29d"


def test_too_many_groups_raises_an_error() -> None:
    data = pd.DataFrame({"onset": ["2026-03-02"] * 9, "group": list("abcdefghi")})

    with pytest.raises(ValueError, match="Other"):
        epicurve(data, "onset", date_type="onset", group_col="group")


def test_incomplete_recent_data_is_shaded_and_explained() -> None:
    ax = epicurve(CASES, "onset", date_type="onset", incomplete_after="2026-03-16")

    assert legend_labels(ax) == ["Recent data may be incomplete"]


def test_y_axis_starts_at_zero() -> None:
    ax = epicurve(CASES, "onset", date_type="onset")

    assert ax.get_ylim()[0] == 0


def test_draws_on_the_axes_it_is_given() -> None:
    _, ax = plt.subplots()

    result = epicurve(CASES, "onset", date_type="onset", ax=ax)

    assert result is ax


def test_no_known_dates_gives_an_empty_plot_with_a_message() -> None:
    data = pd.DataFrame({"onset": [None, None]})

    ax = epicurve(data, "onset", date_type="onset")

    assert bar_heights(ax) == []
    assert "No cases with a known date" in [t.get_text() for t in ax.texts]


def test_date_labels_show_month_and_year() -> None:
    ax = epicurve(CASES, "onset", date_type="onset")
    ax.figure.canvas.draw()

    labels = [label.get_text() for label in ax.get_xticklabels()]

    assert labels[0] == "02 Mar\n2026"
    assert "2026" not in labels[1]
