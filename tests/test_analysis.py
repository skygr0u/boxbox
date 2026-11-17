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


# get_stints


def make_stint_laps(*stints):
    """
    One row per lap. Each stint is a tuple
    ``(drv, stint, compound, first_lap, number_of_laps, life_start)``.

    The age of the set (``life``) goes up by one on every lap of the stint.
    """
    rows = [
        {
            "drv": drv,
            "stint": stint,
            "compound": compound,
            "lap": first_lap + number,
            "life": life_start + number,
        }
        for drv, stint, compound, first_lap, laps, life_start in stints
        for number in range(laps)
    ]
    return pd.DataFrame(rows)


def test_get_stints_describes_a_stint():
    laps = make_stint_laps(("AAA", 1, "SOFT", 10, 5, 3))

    stints = analysis.get_stints(laps)

    assert stints.loc[0, "compound"] == "SOFT"
    assert stints.loc[0, "start_lap"] == 10
    assert stints.loc[0, "end_lap"] == 14
    assert stints.loc[0, "laps"] == 5
    assert stints.loc[0, "life_start"] == 3


def test_get_stints_has_the_documented_columns():
    stints = analysis.get_stints(make_stint_laps(("AAA", 1, "SOFT", 1, 3, 1)))

    assert list(stints.columns) == [
        "drv",
        "stint",
        "compound",
        "start_lap",
        "end_lap",
        "laps",
        "life_start",
    ]


def test_get_stints_gives_one_row_per_driver_and_stint():
    laps = make_stint_laps(
        ("AAA", 1, "SOFT", 1, 10, 1),
        ("AAA", 2, "HARD", 11, 10, 1),
        ("BBB", 1, "MEDIUM", 1, 15, 1),
    )

    stints = analysis.get_stints(laps)

    assert len(stints) == 3
    assert stints["laps"].tolist() == [10, 10, 15]


def test_get_stints_tells_a_used_set_from_a_new_one():
    laps = make_stint_laps(
        ("AAA", 1, "SOFT", 1, 5, 4),
        ("AAA", 2, "HARD", 6, 5, 1),
    )

    stints = analysis.get_stints(laps)

    assert stints["life_start"].tolist() == [4, 1]


def test_get_stints_is_sorted_by_driver_then_stint():
    laps = make_stint_laps(
        ("BBB", 2, "HARD", 11, 5, 1),
        ("BBB", 1, "SOFT", 1, 10, 1),
        ("AAA", 1, "MEDIUM", 1, 15, 1),
    )

    stints = analysis.get_stints(laps)

    assert stints["drv"].tolist() == ["AAA", "BBB", "BBB"]
    assert stints["stint"].tolist() == [1, 1, 2]
    assert stints.index.tolist() == [0, 1, 2]


def test_get_stints_labels_a_missing_compound_unknown():
    laps = make_stint_laps(("AAA", 1, "SOFT", 1, 3, 1), ("AAA", 2, None, 4, 3, 1))

    stints = analysis.get_stints(laps)

    assert stints["compound"].tolist() == ["SOFT", "UNKNOWN"]


def test_get_stints_keeps_the_compound_when_only_one_lap_is_missing():
    laps = make_stint_laps(("AAA", 1, "HARD", 1, 4, 1))
    laps.loc[1, "compound"] = None

    stints = analysis.get_stints(laps)

    assert stints["compound"].tolist() == ["HARD"]


def test_get_stints_uses_all_the_laps_not_only_the_clean_ones():
    laps = make_stint_laps(("AAA", 1, "SOFT", 1, 4, 1))
    laps["is_clean"] = [False, True, True, False]

    stints = analysis.get_stints(laps)

    assert stints["laps"].tolist() == [4]


def test_get_stints_does_not_modify_its_input():
    laps = make_stint_laps(("AAA", 1, "SOFT", 1, 3, 1))

    analysis.get_stints(laps)

    assert list(laps.columns) == ["drv", "stint", "compound", "lap", "life"]
    assert len(laps) == 3


def test_get_stints_missing_column_raises():
    laps = make_stint_laps(("AAA", 1, "SOFT", 1, 3, 1)).drop(columns=["life"])

    with pytest.raises(KeyError):
        analysis.get_stints(laps)
