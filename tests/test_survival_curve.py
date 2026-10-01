import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.legend import Legend
from matplotlib.text import Annotation

from epiplot import EpiplotWarning, survival_curve

# The leukaemia remission trial (Freireich et al., 1963): weeks in remission,
# and whether the child relapsed (1) or was still in remission (0).
TRIAL = pd.DataFrame(
    {
        "arm": ["6-MP"] * 21 + ["Placebo"] * 21,
        "weeks": [6, 6, 6, 6, 7, 9, 10, 10, 11, 13, 16, 17, 19, 20, 22, 23, 25,
                  32, 32, 34, 35,
                  1, 1, 2, 2, 3, 4, 4, 5, 5, 8, 8, 8, 8, 11, 11, 12, 12, 15,
                  17, 22, 23],
        "relapsed": [1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0,
                     0, 0, 0, 0] + [1] * 21,
    }
)  # fmt: skip
SIX_MP = TRIAL[TRIAL["arm"] == "6-MP"]


def legends(ax: Axes) -> list[Legend]:
    return [child for child in ax.get_children() if isinstance(child, Legend)]


def legend_labels(legend: Legend) -> list[str]:
    return [text.get_text() for text in legend.get_texts()]


def legend_title(legend: Legend) -> str:
    return legend.get_title().get_text()


def at_risk_rows(ax: Axes) -> dict[str, list[str]]:
    """Return the number-at-risk table, as {row label: numbers}.

    A single curve has no row label, so its numbers are under "".
    """
    labels: dict[float, str] = {}
    numbers: dict[float, list[tuple[float, str]]] = {}
    for text in ax.texts:
        if not isinstance(text, Annotation) or text.get_text() == "Number at risk:":
            continue
        x, _ = text.xy
        _, y = text.xyann
        if isinstance(text.xycoords, tuple) and text.xycoords[0] == "data":
            numbers.setdefault(y, []).append((x, text.get_text()))
        else:
            labels[y] = text.get_text()
    return {
        labels.get(y, ""): [n for _, n in sorted(row)] for y, row in numbers.items()
    }


def censor_marks(ax: Axes) -> list[int]:
    """Return how many censoring tick marks each curve has."""
    return [
        np.asarray(line.get_xdata()).size
        for line in ax.lines
        if line.get_marker() == "|"
    ]


def all_text(ax: Axes) -> str:
    return " ".join(text.get_text() for text in ax.texts)


def test_returns_the_axes() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")

    assert isinstance(ax, Axes)


def test_draws_on_given_axes() -> None:
    _, given = plt.subplots()

    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks", ax=given)

    assert ax is given


def test_time_unit_labels_the_x_axis() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")

    assert ax.get_xlabel() == "Time (weeks)"


def test_other_time_unit_gives_a_plain_label() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="other")

    assert ax.get_xlabel() == "Time"


def test_missing_time_unit_warns_and_says_so() -> None:
    with pytest.warns(EpiplotWarning, match="time_unit"):
        ax = survival_curve(SIX_MP, "weeks", "relapsed")

    assert ax.get_xlabel() == "Time (unit not specified)"


def test_no_warning_when_time_unit_given() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")


def test_unknown_time_unit_raises_an_error() -> None:
    with pytest.raises(ValueError, match="time_unit"):
        survival_curve(SIX_MP, "weeks", "relapsed", time_unit="hours")  # type: ignore[arg-type]


def test_y_axis_always_runs_from_zero_to_one_hundred_percent() -> None:
    data = pd.DataFrame({"t": [1, 2, 3, 4], "event": [0, 0, 1, 0]})

    ax = survival_curve(data, "t", "event", time_unit="days")

    bottom, top = ax.get_ylim()
    assert bottom == 0
    assert top >= 1


def test_number_at_risk_table_follows_the_time_labels() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")

    assert list(ax.get_xticks()) == [0, 5, 10, 15, 20, 25, 30, 35]
    assert at_risk_rows(ax) == {"": ["21", "21", "15", "11", "8", "5", "4", "1"]}
    assert "Number at risk:" in all_text(ax)


def test_number_at_risk_can_be_shown_at_chosen_times() -> None:
    ax = survival_curve(
        SIX_MP, "weeks", "relapsed", time_unit="weeks", at_risk_times=[20, 0, 10]
    )

    assert list(ax.get_xticks()) == [0, 10, 20]
    assert at_risk_rows(ax) == {"": ["21", "15", "8"]}


def test_groups_get_a_curve_a_legend_entry_and_a_table_row() -> None:
    ax = survival_curve(TRIAL, "weeks", "relapsed", time_unit="weeks", group_col="arm")

    groups_legend, marks_legend = legends(ax)
    assert legend_title(groups_legend) == "Arm"
    assert legend_labels(groups_legend) == ["6-MP", "Placebo"]
    assert legend_title(marks_legend) == "Shading and ticks"
    rows = at_risk_rows(ax)
    assert rows["6-MP"] == ["21", "21", "15", "11", "8", "5", "4", "1"]
    assert rows["Placebo"] == ["21", "14", "8", "4", "2", "0", "0", "0"]


def test_single_curve_has_only_the_shading_and_ticks_legend() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")

    (marks_legend,) = legends(ax)
    assert legend_labels(marks_legend) == ["95% confidence\ninterval", "Censored"]


def test_legend_shows_the_chosen_confidence_level() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks", confidence=0.9)

    (marks_legend,) = legends(ax)
    assert legend_labels(marks_legend)[0] == "90% confidence\ninterval"


def test_censored_people_are_marked_on_their_curve() -> None:
    ax = survival_curve(TRIAL, "weeks", "relapsed", time_unit="weeks", group_col="arm")

    # 6-MP has 11 different censoring times; nobody on placebo was censored.
    assert censor_marks(ax) == [11, 0]


def test_people_left_out_are_noted() -> None:
    data = pd.concat(
        [SIX_MP, pd.DataFrame({"weeks": [None, 4], "relapsed": [1, None]})]
    )

    ax = survival_curve(data, "weeks", "relapsed", time_unit="weeks")

    assert "2 people with missing time or event not shown." in all_text(ax)


def test_no_note_when_nobody_is_left_out() -> None:
    ax = survival_curve(SIX_MP, "weeks", "relapsed", time_unit="weeks")

    assert "not shown" not in all_text(ax)


def test_no_follow_up_time_shows_a_message() -> None:
    data = pd.DataFrame({"t": [None], "event": [1]})

    ax = survival_curve(data, "t", "event", time_unit="days")

    assert "No follow-up time to show" in all_text(ax)


def test_too_many_groups_raise_an_error() -> None:
    data = pd.DataFrame(
        {"t": range(1, 10), "event": [1] * 9, "group": list("ABCDEFGHI")}
    )

    with pytest.raises(ValueError, match="at most 8"):
        survival_curve(data, "t", "event", time_unit="days", group_col="group")
