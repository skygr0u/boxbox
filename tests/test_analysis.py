"""Tests for boxbox.analysis. The tables are small and made by hand."""

import pandas as pd
import pytest

from boxbox import analysis


def make_laps(drivers):
    """
    One row per lap. ``drivers`` maps a driver code to its list of times.

    Every lap is clean and the team is ``"Team " + the driver code``.
    """
    rows = [
        {"drv": drv, "team": f"Team {drv}", "time": time, "is_clean": True}
        for drv, times in drivers.items()
        for time in times
    ]
    return pd.DataFrame(rows)


def test_race_pace_uses_the_median_not_the_mean():
    # median 91.0, mean 92.0
    laps = make_laps({"AAA": [90.0, 91.0, 95.0]})

    pace = analysis.race_pace(laps)

    assert pace["median_lap_time"].tolist() == [91.0]


def test_race_pace_is_sorted_from_fastest_to_slowest():
    laps = make_laps({"SLO": [95.0] * 3, "FAS": [90.0] * 3, "MID": [92.0] * 3})

    pace = analysis.race_pace(laps)

    assert pace["drv"].tolist() == ["FAS", "MID", "SLO"]
    assert pace.index.tolist() == [0, 1, 2]


def test_race_pace_gap_is_measured_from_the_fastest():
    laps = make_laps({"SLO": [95.0] * 3, "FAS": [90.0] * 3, "MID": [92.0] * 3})

    pace = analysis.race_pace(laps)

    assert pace["gap"].tolist() == [0.0, 2.0, 5.0]


def test_race_pace_has_the_documented_columns():
    pace = analysis.race_pace(make_laps({"AAA": [90.0, 91.0]}))

    assert list(pace.columns) == [
        "drv",
        "team",
        "clean_laps",
        "median_lap_time",
        "gap",
    ]
    assert pace["team"].tolist() == ["Team AAA"]
    assert pace["clean_laps"].tolist() == [2]


def test_race_pace_ignores_laps_that_are_not_clean():
    laps = make_laps({"AAA": [90.0, 91.0, 92.0]})
    bad_lap = pd.DataFrame(
        [{"drv": "AAA", "team": "Team AAA", "time": 500.0, "is_clean": False}]
    )
    laps = pd.concat([laps, bad_lap], ignore_index=True)

    pace = analysis.race_pace(laps)

    assert pace["clean_laps"].tolist() == [3]
    assert pace["median_lap_time"].tolist() == [91.0]


def test_race_pace_leaves_out_a_driver_with_too_few_clean_laps():
    # The best driver has 10 clean laps, so the minimum is 7 (70 %).
    laps = make_laps({"AAA": [90.0] * 10, "BBB": [91.0] * 7, "CCC": [80.0] * 6})

    pace = analysis.race_pace(laps)

    # BBB has exactly 7 laps and stays; CCC has 6 and goes, even if fast.
    assert sorted(pace["drv"].tolist()) == ["AAA", "BBB"]


def test_race_pace_does_not_modify_its_input():
    laps = make_laps({"AAA": [90.0, 91.0], "BBB": [92.0, 93.0]})

    analysis.race_pace(laps)

    assert list(laps.columns) == ["drv", "team", "time", "is_clean"]
    assert len(laps) == 4


def test_race_pace_missing_column_raises():
    laps = make_laps({"AAA": [90.0]}).drop(columns=["is_clean"])

    with pytest.raises(KeyError):
        analysis.race_pace(laps)
