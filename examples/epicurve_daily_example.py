"""Draw an example daily epicurve from a made-up point-source outbreak.

Run with:  pixi run python examples/epicurve_daily_example.py
"""

import numpy as np
import pandas as pd

import epiplot

# Make a pretend line list: one row per case. Everyone was exposed at the
# same event on 2 March 2026, and symptoms started a few days to two weeks
# later (usually after about 6 days). The random "seed" means the same
# pretend outbreak is made every time.
rng = np.random.default_rng(seed=3)
n_cases = 85
days_after_event = rng.lognormal(mean=np.log(6), sigma=0.35, size=n_cases).round()
onset = pd.Timestamp("2026-03-02") + pd.to_timedelta(days_after_event, unit="D")

cases = pd.DataFrame({"onset_date": onset})

# The counts behind the plot, as a table.
print(epiplot.count_cases(cases, "onset_date", interval="day"))

ax = epiplot.epicurve(cases, "onset_date", date_type="onset", interval="day")
ax.set_title("Cases by day of symptom onset")

output = "/tmp/epicurve_daily_example.png"
ax.figure.savefig(output, dpi=150)
print(f"Saved {output}")
