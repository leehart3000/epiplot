from epiplot.epicurve import count_cases

__version__ = "0.1.0"

__all__ = ["count_cases", "info"]


def info() -> None:
    print("epiplot: Data plotting for epidemiological research. Under development.")
