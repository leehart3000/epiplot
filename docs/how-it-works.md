# How epiplot works

Each plot is made in two stages. First, a function works out the numbers
and returns them as a table. Then a plotting function draws them. You can
use the tables on their own, for reports or checking.

```{mermaid}
flowchart LR
    linelist["Line list<br>(one row per case)"] --> count["count_cases()"]
    count --> curve["epicurve()"]
    counts["Cases and population<br>(one row per region)"] --> rates["calculate_rates()"]
    rates --> map["rate_map()"]
    rates --> timeline["rate_map_timeline()"]
    shapes["Region shapes<br>(GeoPandas)"] --> map
    shapes --> timeline
```

## Good practice built in

**Epidemic curves** say what the dates mean, show empty periods as zero,
report cases with missing dates, can shade recent periods that may be
incomplete because of reporting delays, and use colour-blind-safe colours.

**Rate maps** show rates rather than raw counts, hide regions with fewer
than 5 cases (whose rates are unreliable and could identify individuals),
show "no data" differently from zero, and use a single-colour scale that
starts at zero. Timelines share one colour scale, so the same shade means
the same rate in every period.

## Warnings

When a plot is missing something important, such as the meaning of its
dates, **epiplot** shows an {class}`epiplot.EpiplotWarning`. The plot is still
drawn, and the problem is also noted on the plot itself.
