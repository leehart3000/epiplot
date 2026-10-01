# <img src="https://leehart3000.github.io/epiplot/_static/epiplot-logo.svg" alt="" height="36" align="absmiddle"> epiplot

[![CI](https://github.com/leehart3000/epiplot/actions/workflows/ci.yml/badge.svg)](https://github.com/leehart3000/epiplot/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/epiplot)](https://pypi.org/project/epiplot/)

Plots for epidemiology and public health research, with good practice
built in.

📖 **Documentation:** https://leehart3000.github.io/epiplot/

![An epidemic curve made with epiplot](https://raw.githubusercontent.com/leehart3000/epiplot/main/docs/images/epicurve_example.png)

## Status

Early development (alpha). Ready to try:

- **Epidemic curves:** cases over time.
- **Rate maps:** rates by region, for one period or as a timeline.

Survival curves are planned.

## Install

```bash
pip install epiplot
```

For rate maps, which need GeoPandas, install the extra map libraries too:

```bash
pip install "epiplot[maps]"
```

Requires Python 3.13 or newer. Works in Google Colab, which already
includes GeoPandas.

## Epidemic curves

```python
import pandas as pd

import epiplot

# One row per case (a "line list").
cases = pd.DataFrame(
    {
        "onset_date": ["2026-03-02", "2026-03-04", "2026-03-10", "2026-03-11", None],
        "origin": ["Local", "Travel", "Local", "Local", "Travel"],
    }
)

ax = epiplot.epicurve(cases, "onset_date", date_type="onset", group_col="origin")
ax.figure.savefig("epicurve.png")
```

For the counts behind the plot, as a table, use `epiplot.count_cases()`.

Good practice built in:

- **Says what the dates mean.** Onset, report, specimen or diagnosis
  dates tell different stories, so epiplot labels the axis to match, and
  warns if the date type isn't given.
- **Shows empty periods as zero,** so gaps in an outbreak stay visible.
- **Reports cases with missing dates** under the plot, instead of
  silently leaving them out.
- **Shades recent periods that may be incomplete** because of reporting
  delays, if you give it a date.
- **Uses colour-blind-safe colours,** with missing groups in grey.
- **Supports ISO weeks (starting Monday) and US CDC weeks (starting
  Sunday).**

## Rate maps

![A timeline of rate maps made with epiplot, using made-up districts](https://raw.githubusercontent.com/leehart3000/epiplot/main/docs/images/rate_map_timeline_example.png)

```python
# regions: a GeoPandas table of region shapes, with an "area_code" column.
# data: one row per region, with "cases" and "population" columns.
ax = epiplot.rate_map(
    regions, data, "area_code", cases_col="cases", population_col="population"
)

# One small map per period, all sharing one colour scale.
figure = epiplot.rate_map_timeline(
    regions,
    data_by_month,
    "area_code",
    "month",
    cases_col="cases",
    population_col="population",
)
```

For the rates behind the maps, with exact 95% confidence intervals, use
`epiplot.calculate_rates()`. Rates you have already calculated, such as
age-standardised rates, can be mapped with `rate_col` and `rate_label`.

Good practice built in:

- **Maps rates, not raw counts,** since counts mostly show where people
  live. Rates are clearly labelled as crude rates.
- **Hides regions with fewer than 5 cases,** whose rates are unreliable
  and could identify individuals.
- **Shows "no data" differently from zero,** so gaps in reporting aren't
  mistaken for no disease.
- **Uses a single-colour scale starting at zero,** with colour bands as
  an option.
- **Timelines share one colour scale,** so the same shade means the same
  rate in every period.

## Survival curves

![Kaplan-Meier survival curves comparing time to relapse for 6-MP and placebo, made with epiplot](https://raw.githubusercontent.com/leehart3000/epiplot/main/docs/images/survival_curve_example.png)

Start with one row per person, with a follow-up time and whether the
event happened (1) or the person was censored (0):

```python
ax = epiplot.survival_curve(
    trial, "weeks", "relapsed", time_unit="weeks", group_col="treatment"
)
```

Good practice built in:

- **Time unit on the axis.** If `time_unit` is not given, **epiplot** warns
  and says so on the axis.
- **Number at risk.** A table under the plot shows how many people are still
  being followed, because the right-hand end of a curve often rests on very
  few people.
- **Uncertainty and censoring shown.** Shaded 95% confidence bands, and tick
  marks where people were censored.
- **Honest scale.** The y axis always runs from 0% to 100%.

For the estimates behind the plot, as a table, use `epiplot.kaplan_meier()`.
The example uses real data from a 1963 leukaemia trial (Freireich et al.).

## More examples

Fuller examples are in the
[`examples`](https://github.com/leehart3000/epiplot/tree/main/examples)
folder.

## License

BSD 3-Clause. See [LICENSE](LICENSE).
