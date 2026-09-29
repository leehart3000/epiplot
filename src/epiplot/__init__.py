from epiplot._warnings import EpiplotWarning
from epiplot.epicurve import count_cases, epicurve

__version__ = "0.1.0"

__all__ = ["EpiplotWarning", "count_cases", "epicurve", "info"]


def info() -> None:
    print("epiplot: Data plotting for epidemiological research. Under development.")
