"""Tests for boxbox.cleaning. The tables are small and made by hand."""

import pandas as pd
import pytest

from boxbox import cleaning

NAN = float("nan")


def make_laps(*changes):
    """
    One row per dictionary in ``changes``.

    Each row starts as a normal clean lap and takes the values of its
    dictionary, so a test only writes what makes the lap special.
    """
    normal = {
        "time": 95.0,
        "lap": 10,
        "status": "1",
        "pin": NAN,
        "pout": NAN,
        "del": False,
        "iacc": True,
    }
    return pd.DataFrame([{**normal, **change} for change in changes])


def test_a_normal_lap_is_clean():
    laps = cleaning.mark_clean_laps(make_laps({}))

    assert laps["is_clean"].tolist() == [True]


@pytest.mark.parametrize(
    "change",
    [
        {"pin": 80.0},
        {"pout": 75.0},
        {"lap": 1},
        {"status": "4"},
        {"status": "12"},
        {"del": True},
        {"iacc": False},
        {"time": NAN},
    ],
    ids=[
        "in-lap",
        "out-lap",
        "lap 1",
        "safety car",
        "yellow flag",
        "deleted",
        "inaccurate",
        "no time",
    ],
)
def test_each_rule_makes_a_lap_not_clean(change):
    laps = cleaning.mark_clean_laps(make_laps(change))

    assert laps["is_clean"].tolist() == [False]


def test_each_lap_is_marked_separately():
    laps = make_laps({}, {"pin": 80.0}, {}, {"status": "4"})

    result = cleaning.mark_clean_laps(laps)

    assert result["is_clean"].tolist() == [True, False, True, False]


def test_every_row_and_column_is_kept():
    laps = make_laps({}, {"lap": 1}, {"del": True})

    result = cleaning.mark_clean_laps(laps)

    assert len(result) == 3
    assert list(result.columns) == list(laps.columns) + ["is_clean"]
    assert result["time"].tolist() == laps["time"].tolist()


def test_is_clean_is_a_boolean_column():
    result = cleaning.mark_clean_laps(make_laps({}, {"lap": 1}))

    assert result["is_clean"].dtype == bool


def test_mark_clean_laps_does_not_modify_its_input():
    laps = make_laps({}, {"lap": 1})

    cleaning.mark_clean_laps(laps)

    assert "is_clean" not in laps.columns


def test_mark_clean_laps_missing_column_raises():
    laps = make_laps({}).drop(columns=["iacc"])

    with pytest.raises(KeyError):
        cleaning.mark_clean_laps(laps)
