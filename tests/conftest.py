from collections.abc import Iterator

import matplotlib
import matplotlib.pyplot as plt
import pytest

# Draw plots in memory only, so tests never open windows.
matplotlib.use("Agg")


@pytest.fixture(autouse=True)
def close_figures() -> Iterator[None]:
    """Close all figures after each test, to free memory."""
    yield
    plt.close("all")
