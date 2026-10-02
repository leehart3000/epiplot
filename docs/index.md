# epiplot

Plots for epidemiology and public health research, with good practice
built in.

## Gallery

````{grid} 1 2 2 2
:gutter: 3

```{grid-item-card} Epicurve by day
:img-top: images/epicurve_daily_example.png
:img-alt: Bar chart of cases by day of symptom onset, with a single peak
:link: api.html#epiplot.epicurve
:link-type: url

A point-source outbreak: everyone was exposed at one event.
```

```{grid-item-card} Epicurve by week, with groups
:img-top: images/epicurve_example.png
:img-alt: Stacked bar chart of cases by week, split into local and travel cases
:link: api.html#epiplot.epicurve
:link-type: url

Cases split by origin, with recent weeks shaded as provisional.
```

```{grid-item-card} Rate map
:img-top: images/rate_map_example.png
:img-alt: Map of districts shaded by rate per 100,000 people
:link: api.html#epiplot.rate_map
:link-type: url

Crude rates per 100,000, with small numbers hidden.
```

```{grid-item-card} Survival curve
:img-top: images/survival_curve_example.png
:img-alt: Two Kaplan-Meier curves comparing time to relapse for 6-MP and placebo, with a number-at-risk table
:link: api.html#epiplot.survival_curve
:link-type: url

Real data from a 1963 leukaemia trial, with a number-at-risk table.
```

```{grid-item-card} Rate map timeline
:columns: 12
:img-top: images/rate_map_timeline_example.png
:img-alt: Four maps showing rates by district, one for each month
:link: api.html#epiplot.rate_map_timeline
:link-type: url

The same regions over time, on one shared colour scale.
```
````

**epiplot** makes standard epidemiological plots easy, and hard to get wrong.
Each plot has sensible defaults based on good practice: clear labels,
honest handling of missing data, and colours that work for colour-blind
readers.

Ready to try:

- **Epidemic curves:** cases over time.
- **Rate maps:** rates by region, for one period or as a timeline.

**epiplot** is in early development (alpha), so details may still change.

```{toctree}
:maxdepth: 2

getting-started
how-it-works
case-studies/index
api
```
