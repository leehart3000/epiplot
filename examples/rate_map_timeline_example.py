"""Draw an example timeline of rate maps, for a made-up spreading outbreak.

Run with:  pixi run python examples/rate_map_timeline_example.py
"""

import geopandas
import numpy as np
import pandas as pd
from shapely.geometry import box

import epiplot

# A pretend country of 6 by 5 square districts.
codes = [f"D{row}{col}" for row in range(5) for col in range(6)]
shapes = [box(col, row, col + 1, row + 1) for row in range(5) for col in range(6)]
regions = geopandas.GeoDataFrame({"district": codes}, geometry=shapes)

# An outbreak that starts in the north-east corner and spreads south-west.
rng = np.random.default_rng(seed=3)
population = rng.integers(2_000, 80_000, size=len(codes))
rows = np.repeat(np.arange(5), 6)
cols = np.tile(np.arange(6), 5)
distance = np.hypot(4 - rows, 5 - cols)

tables = []
for month_number, month in enumerate(["2026-01", "2026-02", "2026-03", "2026-04"]):
    spread = 1.5 * (month_number + 1)
    risk_per_person = 15e-5 + 60e-5 * np.exp(-((distance / spread) ** 2))
    tables.append(
        pd.DataFrame(
            {
                "district": codes,
                "month": pd.Timestamp(month),
                "cases": rng.poisson(population * risk_per_person),
                "population": population,
            }
        )
    )
data = pd.concat(tables, ignore_index=True)
data["month"] = data["month"].dt.strftime("%b %Y")  # labels such as "Jan 2026"
data["month"] = pd.Categorical(data["month"], categories=data["month"].unique())

figure = epiplot.rate_map_timeline(
    regions,
    data,
    "district",
    "month",
    cases_col="cases",
    population_col="population",
)
figure.suptitle("Cases by district and month")

output = "/tmp/rate_map_timeline_example.png"
figure.savefig(output, dpi=150)
print(f"Saved {output}")
