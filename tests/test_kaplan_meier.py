import numpy as np
import pandas as pd
import pytest

from epiplot import kaplan_meier

# The 6-MP group of the leukaemia remission trial (Freireich et al., 1963),
# a standard textbook example. Times are weeks in remission; 0 means the
# person was still in remission when last seen (censored).
SIX_MP = pd.DataFrame(
    {
        "weeks": [6, 6, 6, 6, 7, 9, 10, 10, 11, 13, 16, 17, 19, 20, 22, 23, 25, 32,
                  32, 34, 35],
        "relapsed": [1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0],
    }
)  # fmt: skip


def event_rows(result: pd.DataFrame) -> pd.DataFrame:
    return result[result["events"] > 0].reset_index(drop=True)


def test_matches_published_estimates() -> None:
    # Published values, as given by R's survival package with the
    # log-log confidence interval.
    result = event_rows(kaplan_meier(SIX_MP, "weeks", "relapsed"))

    assert result["time"].tolist() == [6, 7, 10, 13, 16, 22, 23]
    assert result["at_risk"].tolist() == [21, 17, 15, 12, 11, 7, 6]
    np.testing.assert_allclose(
        result["survival"], [0.857, 0.807, 0.753, 0.690, 0.627, 0.538, 0.448],
        atol=0.0005,
    )  # fmt: skip
    np.testing.assert_allclose(
        result["survival_lower"], [0.620, 0.563, 0.503, 0.432, 0.368, 0.268, 0.188],
        atol=0.0005,
    )  # fmt: skip
    np.testing.assert_allclose(
        result["survival_upper"], [0.952, 0.923, 0.889, 0.849, 0.805, 0.747, 0.680],
        atol=0.0005,
    )  # fmt: skip


def test_starts_at_time_zero_with_everyone_at_risk() -> None:
    result = kaplan_meier(SIX_MP, "weeks", "relapsed")

    first = result.iloc[0]
    assert first["time"] == 0
    assert first["at_risk"] == 21
    assert first["survival"] == 1
    assert first["survival_lower"] == 1
    assert first["survival_upper"] == 1


def test_censored_times_are_kept_for_tick_marks() -> None:
    result = kaplan_meier(SIX_MP, "weeks", "relapsed")

    censored_times = result.loc[result["censored"] > 0, "time"].tolist()
    assert censored_times == [6, 9, 10, 11, 17, 19, 20, 25, 32, 34, 35]
    assert result["censored"].sum() == 12
    assert result["events"].sum() == 9


def test_survival_does_not_change_at_censored_times() -> None:
    result = kaplan_meier(SIX_MP, "weeks", "relapsed")

    week_9 = result.loc[result["time"] == 9, "survival"].item()
    week_7 = result.loc[result["time"] == 7, "survival"].item()
    assert week_9 == week_7


def test_true_and_false_work_as_events() -> None:
    data = SIX_MP.assign(relapsed=SIX_MP["relapsed"].astype(bool))

    pd.testing.assert_frame_equal(
        kaplan_meier(data, "weeks", "relapsed"),
        kaplan_meier(SIX_MP, "weeks", "relapsed"),
    )


def test_interval_is_missing_once_survival_reaches_zero() -> None:
    data = pd.DataFrame({"t": [1, 2], "event": [1, 1]})

    result = kaplan_meier(data, "t", "event")

    last = result.iloc[-1]
    assert last["survival"] == 0
    assert np.isnan(last["survival_lower"])
    assert np.isnan(last["survival_upper"])


def test_rows_with_missing_values_are_counted_not_silently_dropped() -> None:
    data = pd.DataFrame({"t": [1, None, 3], "event": [1, 1, None]})

    result = kaplan_meier(data, "t", "event")

    assert result.attrs["n_missing"] == 2
    assert result["at_risk"].iloc[0] == 1


def test_groups_get_separate_curves_in_order() -> None:
    data = pd.DataFrame(
        {
            "t": [1, 2, 3, 1, 2],
            "event": [1, 0, 1, 0, 1],
            "arm": ["B", "B", "B", "A", None],
        }
    )

    result = kaplan_meier(data, "t", "event", group_col="arm")

    assert list(result.columns)[0] == "arm"
    assert list(result["arm"].unique()) == ["A", "B", "Missing"]
    b = result[result["arm"] == "B"]
    assert b["at_risk"].iloc[0] == 3
    assert b["survival"].iloc[-1] == pytest.approx(0)


def test_categorical_group_order_is_kept() -> None:
    arm = pd.Categorical(["A", "B"], categories=["B", "A"])
    data = pd.DataFrame({"t": [1, 2], "event": [1, 1], "arm": arm})

    result = kaplan_meier(data, "t", "event", group_col="arm")

    assert list(result["arm"].unique()) == ["B", "A"]


def test_negative_times_raise_an_error() -> None:
    data = pd.DataFrame({"t": [1, -2], "event": [1, 1]})

    with pytest.raises(ValueError, match="negative"):
        kaplan_meier(data, "t", "event")


@pytest.mark.parametrize("bad_event", [2, -1, 0.5])
def test_invalid_events_raise_an_error(bad_event: float) -> None:
    data = pd.DataFrame({"t": [1, 2], "event": [1, bad_event]})

    with pytest.raises(ValueError, match="censored"):
        kaplan_meier(data, "t", "event")


def test_missing_column_raises_an_error() -> None:
    with pytest.raises(KeyError, match="time"):
        kaplan_meier(SIX_MP, "time", "relapsed")


def test_invalid_confidence_raises_an_error() -> None:
    with pytest.raises(ValueError, match="confidence"):
        kaplan_meier(SIX_MP, "weeks", "relapsed", confidence=95)
