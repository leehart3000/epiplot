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