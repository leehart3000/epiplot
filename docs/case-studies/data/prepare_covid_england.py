"""Prepare COVID-19 cases, populations and boundaries for England, winter 2020-21.

Download these three files into one folder (they are too large, or too
detailed, to store in the repository):

1. UKHSA COVID-19 archive, "Cases" (cases.zip), from
   https://ukhsa-dashboard.data.gov.uk/covid-19-archive-data-download
   Extract Cases/ltla_newCasesBySpecimenDate.csv from it.
2. ONS "Local Authority Districts (December 2020) Boundaries UK BUC", as
   GeoJSON, from https://geoportal.statistics.gov.uk, saved as
   lad_2020_buc.geojson.
3. ONS mid-2020 population estimates on 2020 geography
   (ukpopestimatesmid2020on2020geography.xls), from
   https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland

Then run, giving the folder holding the three files:

    pixi exec --spec python=3.13 --spec pandas --spec geopandas --spec xlrd -- \\
        python docs/case-studies/data/prepare_covid_england.py FOLDER

The script keeps England only, adds up cases in four equal 28-day periods
starting Monday 2 November 2020, and makes the three sources match:

- The four old Buckinghamshire districts are added together under the new
  Buckinghamshire council (formed April 2020), as on the 2020 map.
- The Isles of Scilly are joined to Cornwall, and the City of London to
  Hackney, on the map and in the populations, because UKHSA reported their
  cases together (both have very small populations).
"""

import sys
from pathlib import Path

import geopandas
import pandas as pd

HERE = Path(__file__).parent
CASES_OUT = HERE / "covid_england_2020_21.csv"
REGIONS_OUT = HERE / "england_lad_2020.geojson"

FIRST_DAY = pd.Timestamp("2020-11-02")  # a Monday
N_PERIODS = 4
PERIOD_DAYS = 28

OLD_BUCKS = ["E07000004", "E07000005", "E07000006", "E07000007"]
BUCKS = "E06000060"
JOINED = {"E06000053": "E06000052", "E09000001": "E09000012"}  # small -> big
JOINED_NAMES = {
    "E06000052": "Cornwall and Isles of Scilly",
    "E09000012": "Hackney and City of London",
}


def period_label(start: pd.Timestamp) -> str:
    """Label a 28-day period, such as "30 Nov – 27 Dec"."""
    end = start + pd.Timedelta(days=PERIOD_DAYS - 1)
    if start.month == end.month:
        return f"{start.day}–{end.day} {end:%b}"
    return f"{start.day} {start:%b} – {end.day} {end:%b}"


def prepare_cases(path: Path) -> pd.DataFrame:
    """Cases per area in each 28-day period, England only."""
    raw = pd.read_csv(path)
    raw["date"] = pd.to_datetime(raw["date"], format="%d/%m/%Y")
    last_day = FIRST_DAY + pd.Timedelta(days=N_PERIODS * PERIOD_DAYS)
    cases = raw[
        raw["area_code"].str.startswith("E")
        & (raw["date"] >= FIRST_DAY)
        & (raw["date"] < last_day)
    ].copy()
    cases["area_code"] = cases["area_code"].replace(dict.fromkeys(OLD_BUCKS, BUCKS))
    days = (cases["date"] - FIRST_DAY).dt.days
    cases["period_start"] = FIRST_DAY + pd.to_timedelta(
        days // PERIOD_DAYS * PERIOD_DAYS, unit="D"
    )
    return (
        cases.groupby(["area_code", "period_start"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "cases"})
    )


def prepare_regions(path: Path) -> geopandas.GeoDataFrame:
    """English local authority boundaries, with the small areas joined."""
    raw = geopandas.read_file(path)
    regions = raw[raw["LAD20CD"].str.startswith("E")].copy()
    regions["area_code"] = regions["LAD20CD"].replace(JOINED)
    names = regions.set_index("LAD20CD")["LAD20NM"].to_dict()
    regions = regions[["area_code", "geometry"]].dissolve(by="area_code")
    regions = regions.reset_index()
    regions["area_name"] = [
        JOINED_NAMES.get(code, names[code]) for code in regions["area_code"]
    ]
    return regions[["area_code", "area_name", "geometry"]]


def prepare_population(path: Path) -> pd.Series:
    """Mid-2020 population of each English area, with the small areas joined."""
    sheet = "MYE2 - Persons"
    first_column = pd.read_excel(path, sheet_name=sheet, header=None, usecols=[0])
    is_header = first_column.iloc[:, 0].astype(str).str.strip() == "Code"
    header_row = int(first_column.index[is_header][0])
    pop = pd.read_excel(path, sheet_name=sheet, header=header_row)
    # English local authority districts have codes E06, E07, E08 and E09.
    pop = pop[pop["Code"].astype(str).str.match(r"E0[6-9]")]
    codes = pop["Code"].replace(JOINED)
    return pop.groupby(codes)["All ages"].sum().rename("population")


def main(folder: Path) -> None:
    cases = prepare_cases(folder / "ltla_newCasesBySpecimenDate.csv")
    regions = prepare_regions(folder / "lad_2020_buc.geojson")
    population = prepare_population(folder / "ukpopestimatesmid2020on2020geography.xls")

    # Every source must have exactly the same areas.
    case_codes = set(cases["area_code"])
    map_codes = set(regions["area_code"])
    pop_codes = set(population.index) & map_codes
    if not (case_codes == map_codes == pop_codes):
        raise SystemExit(
            "Areas do not match.\n"
            f"Cases only: {sorted(case_codes - map_codes)}\n"
            f"Map only: {sorted(map_codes - case_codes)}\n"
            f"No population: {sorted(map_codes - pop_codes)}"
        )
    if (cases.groupby("area_code").size() != N_PERIODS).any():
        raise SystemExit("Some areas are missing a period.")

    table = cases.merge(regions[["area_code", "area_name"]], on="area_code")
    table = table.merge(population, left_on="area_code", right_index=True)
    table["period"] = table["period_start"].map(period_label)
    table["period_start"] = table["period_start"].dt.date
    table = table[
        ["area_code", "area_name", "period_start", "period", "cases", "population"]
    ].sort_values(["period_start", "area_code"])
    table.to_csv(CASES_OUT, index=False)

    regions.to_file(REGIONS_OUT, driver="GeoJSON", COORDINATE_PRECISION=5)

    print(f"{regions['area_code'].nunique()} areas, {N_PERIODS} periods:")
    print(table.groupby("period", sort=False)["cases"].sum().to_string())
    print(f"Wrote {CASES_OUT.name} and {REGIONS_OUT.name}")
    print(f"Boundary file size: {REGIONS_OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]))
