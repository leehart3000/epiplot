"""Draw an example epicurve from a made-up outbreak.

Run with:  pixi run python examples/epicurve_example.py
"""

import numpy as np
import pandas as pd

import epiplot

# Make a pretend line list: one row per case. The random "seed" means the
# same pretend outbreak is made every time.
rng = np.random.default_rng(seed=1)
n_cases = 220
days_after_start = rng.gamma(shape=6, scale=7, size=n_cases).astype(int)
onset = pd.Timestamp("2026-01-05") + pd.to_timedelta(days_after_start, unit="D")
origin = rng.choice(["Local", "Travel"], size=n_cases, p=[0.7, 0.3])

cases = pd.DataFrame({"onset_date": onset, "origin": origin})
# Make a few dates and origins unknown, as in real data.
cases.loc[rng.random(n_cases) < 0.05, "onset_date"] = pd.NaT
cases.loc[rng.random(n_cases) < 0.06, "origin"] = None

# The counts behind the plot, as a table.
print(epiplot.count_cases(cases, "onset_date", group_col="origin").head(9))

# Pretend the data was extracted on 6 May 2026, and that cases can take up
# to two weeks after symptoms start to be reported. So the last two weeks
# are likely to be incomplete.
extracted = pd.Timestamp("2026-05-06")
reporting_delay = pd.Timedelta(weeks=2)

ax = epiplot.epicurve(
    cases,
    "onset_date",
    date_type="onset",
    group_col="origin",
    incomplete_after=extracted - reporting_delay,
)
ax.set_title("Cases by week of symptom onset")

output = "/tmp/epicurve_example.png"
ax.figure.savefig(output, dpi=150)
print(f"Saved {output}")
