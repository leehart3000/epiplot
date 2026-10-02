# Case study data

## h7n9_china_2013.csv

Human cases of influenza A(H7N9) in China, 2013: one row per case.

- **Source:** Kucharski A, Mills HL, Pinsent A, Fraser C, Van Kerkhove M,
  Donnelly CA, Riley S (2015). Data from: Distinguishing between reservoir
  exposure and human-to-human transmission for emerging pathogens using case
  onset data. Dryad. https://doi.org/10.5061/dryad.2g43n
- **Licence:** CC0 1.0 (public domain dedication), as for all Dryad data.
- **Changes:** made by `prepare_h7n9.py`. Only `id`, `sex`, `province`,
  `onset_date` and `outcome` are kept; free-text notes, ages and other
  details about individual patients are left out. "death" and "died" are
  combined as "Died", "cleared" becomes "Recovered", and unknown values are
  left blank.

## covid_england_2020_21.csv and england_lad_2020.geojson

COVID-19 cases in England by lower-tier local authority, in four 28-day
periods from 2 November 2020 to 21 February 2021, with mid-2020 populations
and matching boundaries (312 areas).

- **Cases:** UKHSA COVID-19 archive data download, "Cases" (new cases by
  specimen date, lower-tier local authority).
  https://ukhsa-dashboard.data.gov.uk/covid-19-archive-data-download
  Contains public sector information licensed under the Open Government
  Licence v3.0.
- **Boundaries:** ONS, Local Authority Districts (December 2020) Boundaries
  UK BUC. Source: Office for National Statistics licensed under the Open
  Government Licence v3.0. Contains OS data © Crown copyright and database
  right 2020.
- **Population:** ONS mid-2020 population estimates (2020 geography). Source:
  Office for National Statistics licensed under the Open Government Licence
  v3.0.
- **Changes:** made by `prepare_covid_england.py`. England only; cases added
  up in 28-day periods; the four old Buckinghamshire districts combined as
  Buckinghamshire; the Isles of Scilly joined to Cornwall and the City of
  London to Hackney (on the map and in the populations), because UKHSA
  reported their cases together.