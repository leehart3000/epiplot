from importlib.metadata import version

from epiplot._warnings import EpiplotWarning
from epiplot.epicurve import count_cases, epicurve
from epiplot.ratemap import rate_map, rate_map_timeline
from epiplot.rates import calculate_rates
from epiplot.survival import kaplan_meier, survival_curve

# The version is set in pyproject.toml, and read from the installed package.
__version__ = version("epiplot")

__all__ = [
    "EpiplotWarning",
    "calculate_rates",
    "count_cases",
    "epicurve",
    "info",
    "rate_map",
    "rate_map_timeline",
    "kaplan_meier",
    "survival_curve",
]


def info() -> None:
    print("epiplot: Data plotting for epidemiological research. Under development.")
