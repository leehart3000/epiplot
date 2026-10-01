"""Prepare the H7N9 line list used in the case study.

The original file comes from Dryad (CC0):
Kucharski A, Mills HL, Pinsent A, et al. (2015). Data from: Distinguishing
between reservoir exposure and human-to-human transmission for emerging
pathogens using case onset data. https://doi.org/10.5061/dryad.2g43n

Download "Supplementary_information_H7N9_linelist.csv" from that page, save
it next to this script as "h7n9_china_2013_raw.csv", then run:

    pixi run python docs/case-studies/data/prepare_h7n9.py

Only the columns the case study needs are kept. Free-text notes about
individual patients are left out (data minimisation), and the raw file is
not stored in the repository.
"""

from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "h7n9_china_2013_raw.csv"
OUTPUT = HERE / "h7n9_china_2013.csv"

raw = pd.read_csv(RAW)

cases = pd.DataFrame(
    {
        "id": raw["ID"],
        "sex": raw["gender"].map({"m": "Male", "f": "Female"}),  # "?" -> missing
        "province": raw["province"].str.strip(),
        "onset_date": pd.to_datetime(
            raw["date_of_onset"], format="%d-%b-%Y", errors="coerce"
        ).dt.date,
        "outcome": raw["outcome"].map(
            {"death": "Died", "died": "Died", "cleared": "Recovered"}
        ),  # blank -> missing (outcome not known when the data were collated)
    }
)

cases.to_csv(OUTPUT, index=False)
print(f"Wrote {len(cases)} cases to {OUTPUT.name}")
print(cases.isna().sum().to_string())
