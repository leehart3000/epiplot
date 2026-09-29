"""Draw an example rate map from made-up districts and data.

Run with:  pixi run python examples/rate_map_example.py
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

# Pretend populations and cases, with a higher risk towards the north-east.
rng = np.random.default_rng(seed=2)
population = rng.integers(2_000, 80_000, size=len(codes))
rows = np.repeat(np.arange(5), 6)
cols = np.tile(np.arange(6), 5)
risk_per_person = 20e-5 * (1 + rows / 2 + cols / 3)
cases = rng.poisson(population * risk_per_person)

data = pd.DataFrame({"district": codes, "cases": cases, "population": population})
data = data.drop(index=[8])  # one district sent no data

# The rates behind the map, as a table.
print(epiplot.calculate_rates(data, "district", "cases", "population").round(1).head(8))

ax = epiplot.rate_map(
    regions, data, "district", cases_col="cases", population_col="population"
)
ax.set_title("Cases by district")

output = "/tmp/rate_map_example.png"
ax.figure.savefig(output, dpi=150)
print(f"Saved {output}")
