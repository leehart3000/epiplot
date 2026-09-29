from importlib.metadata import version

from epiplot._warnings import EpiplotWarning
from epiplot.epicurve import count_cases, epicurve
from epiplot.rates import calculate_rates

# The version is set in pyproject.toml, and read from the installed package.
__version__ = version("epiplot")

__all__ = ["EpiplotWarning", "calculate_rates", "count_cases", "epicurve", "info"]


def info() -> None:
    print("epiplot: Data plotting for epidemiological research. Under development.")
