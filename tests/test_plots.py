"""Tests for boxbox.plots. The tables are small and made by hand."""

# pylint: disable=missing-function-docstring

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.collections import LineCollection, PathCollection
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


def make_stints():
    """AAA: SOFT laps 1-10, HARD laps 11-30. BBB: MEDIUM laps 1-20."""
    return pd.DataFrame(
        {
            "drv": ["AAA", "AAA", "BBB"],
            "compound": ["SOFT", "HARD", "MEDIUM"],
            "start_lap": [1, 11, 1],
            "end_lap": [10, 30, 20],
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


def test_plot_strategies_draws_one_block_per_stint_at_the_right_place():
    ax = plots.plot_strategies(make_stints()).axes[0]
    places = [(block.get_x(), block.get_width()) for block in get_bars(ax)]
    assert places == [(0, 10), (10, 20), (0, 20)]


def test_plot_strategies_colours_each_block_by_its_compound():
    ax = plots.plot_strategies(make_stints()).axes[0]
    colours = [block.get_facecolor() for block in get_bars(ax)]
    expected = [to_rgba(plots.COMPOUND_COLOURS[c]) for c in ("SOFT", "HARD", "MEDIUM")]
    assert colours == expected


def test_plot_strategies_follows_the_order_of_the_drivers_given():
    fig = plots.plot_strategies(make_stints(), drivers=["BBB", "AAA"])
    ax = fig.axes[0]
    assert [label.get_text() for label in ax.get_yticklabels()] == ["BBB", "AAA"]
    assert get_bars(ax)[0].get_width() == 20  # BBB is now the first row


def make_degradation():
    """Three SOFT stints and one HARD stint, in the order SOFT, HARD, SOFT, SOFT."""
    return pd.DataFrame(
        {
            "compound": ["SOFT", "HARD", "SOFT", "SOFT"],
            "degradation_per_lap": [0.2, 0.05, 0.1, 0.9],
        }
    )


def test_plot_degradation_draws_one_dot_per_stint_grouped_by_compound():
    ax = plots.plot_degradation(make_degradation()).axes[0]
    groups = [c for c in ax.collections if isinstance(c, PathCollection)]
    heights = [list(group.get_offsets()[:, 1]) for group in groups]  # type: ignore
    assert heights == [[0.2, 0.1, 0.9], [0.05]]  # SOFT first, then HARD
    labels = [label.get_text() for label in ax.get_xticklabels()]
    assert labels == ["SOFT\n(n=3)", "HARD\n(n=1)"]


def test_plot_degradation_marks_the_median_of_each_compound():
    ax = plots.plot_degradation(make_degradation()).axes[0]
    lines = [c for c in ax.collections if isinstance(c, LineCollection)]
    medians = [line.get_segments()[0][0][1] for line in lines]
    # the median of 0.2, 0.1, 0.9 is 0.2 (their mean would be 0.4)
    assert medians == pytest.approx([0.2, 0.05])


def test_plot_degradation_missing_column_raises():
    with pytest.raises(KeyError):
        plots.plot_degradation(make_degradation().drop(columns="compound"))
