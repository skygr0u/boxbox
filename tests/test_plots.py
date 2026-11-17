"""Tests for boxbox.plots. The tables are small and made by hand."""

# pylint: disable=missing-function-docstring

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.colors import to_rgba
from matplotlib.patches import Rectangle

from boxbox import plots


@pytest.fixture(autouse=True)
def close_figures():
    """Close every figure after each test, so they do not pile up."""
    yield
    plt.close("all")


def get_bars(ax):
    """Return the bars drawn on the axes (the legend is not among them)."""
    return [patch for patch in ax.patches if isinstance(patch, Rectangle)]


def make_pace():
    """Three drivers, from the fastest to the slowest."""
    return pd.DataFrame(
        {
            "drv": ["FAS", "MID", "SLO"],
            "team": ["Ferrari", "Mercedes", "Ferrari"],
            "gap": [0.0, 0.5, 2.0],
        }
    )


def test_plot_race_pace_draws_the_gaps_with_the_fastest_driver_on_top():
    ax = plots.plot_race_pace(make_pace()).axes[0]
    assert [rect.get_width() for rect in get_bars(ax)] == [0.0, 0.5, 2.0]
    assert [label.get_text() for label in ax.get_yticklabels()] == ["FAS", "MID", "SLO"]
    assert ax.yaxis_inverted()


def test_plot_race_pace_colours_each_bar_by_its_team():
    ax = plots.plot_race_pace(make_pace()).axes[0]
    colours = [rect.get_facecolor() for rect in get_bars(ax)]
    ferrari = to_rgba(plots.TEAM_COLOURS["Ferrari"])
    mercedes = to_rgba(plots.TEAM_COLOURS["Mercedes"])
    assert colours == [ferrari, mercedes, ferrari]


def test_plot_race_pace_missing_column_raises():
    with pytest.raises(KeyError):
        plots.plot_race_pace(make_pace().drop(columns="team"))