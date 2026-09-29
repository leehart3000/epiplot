# epiplot

[![CI](https://github.com/leehart3000/epiplot/actions/workflows/ci.yml/badge.svg)](https://github.com/leehart3000/epiplot/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/epiplot)](https://pypi.org/project/epiplot/)

Plots for epidemiology and public health research, with good practice
built in.

![An epidemic curve made with epiplot](https://raw.githubusercontent.com/leehart3000/epiplot/main/docs/images/epicurve_example.png)

## Status

Early development (alpha). The first plot, the **epidemic curve**, is
ready to try. Rate maps and survival curves are planned.

## Install

```bash
pip install epiplot
```

Requires Python 3.13 or newer. Works in Google Colab.

## Example

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
A fuller example is in
[`examples/epicurve_example.py`](https://github.com/leehart3000/epiplot/blob/main/examples/epicurve_example.py).

## Good practice built in

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

## License

BSD 3-Clause. See [LICENSE](LICENSE).
