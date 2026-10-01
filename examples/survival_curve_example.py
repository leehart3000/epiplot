"""Draw example survival curves from a real clinical trial.

The data come from a 1963 trial of the drug 6-mercaptopurine (6-MP) for
acute leukaemia in children (Freireich et al., Blood 21:699-716). Each
child was in remission at the start; the event is relapse, and "weeks" is
the time in remission. Children still in remission when last seen are
censored. The data are widely used to teach survival analysis.

Run with:  pixi run python examples/survival_curve_example.py
"""

import pandas as pd

import epiplot

six_mp_weeks = [6, 6, 6, 6, 7, 9, 10, 10, 11, 13, 16, 17, 19, 20, 22, 23, 25,
                32, 32, 34, 35]  # fmt: skip
six_mp_relapsed = [1, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0,
                   0, 0, 0, 0]  # fmt: skip
placebo_weeks = [1, 1, 2, 2, 3, 4, 4, 5, 5, 8, 8, 8, 8, 11, 11, 12, 12, 15,
                 17, 22, 23]  # fmt: skip

trial = pd.DataFrame(
    {
        "treatment": ["6-MP"] * 21 + ["Placebo"] * 21,
        "weeks": six_mp_weeks + placebo_weeks,
        "relapsed": six_mp_relapsed + [1] * 21,  # every placebo child relapsed
    }
)

# The estimates behind the plot, as a table.
print(epiplot.kaplan_meier(trial, "weeks", "relapsed", group_col="treatment"))

ax = epiplot.survival_curve(
    trial, "weeks", "relapsed", time_unit="weeks", group_col="treatment"
)
ax.set_ylabel("Still in remission")
ax.set_title("Time to relapse, by treatment")

output = "/tmp/survival_curve_example.png"
ax.figure.savefig(output, dpi=150)
print(f"Saved {output}")
