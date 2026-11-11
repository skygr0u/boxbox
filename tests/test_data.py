"""Tests for boxbox.data. No test uses the internet: downloads are faked."""

import pandas as pd
import pytest
import requests

from boxbox import data

RACES = ["Bahrain Grand Prix", "Monaco Grand Prix", "Miami Grand Prix"]


class FakeResponse:
    """A minimal stand-in for a requests response."""

    def __init__(self, payload=None, status_error=False):
        self.payload = payload
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise requests.exceptions.HTTPError("404 Client Error")

    def json(self):
        return self.payload


# fetch_json


def test_fetch_json_returns_parsed_content(monkeypatch):
    monkeypatch.setattr(
        data.requests, "get", lambda url, timeout: FakeResponse({"a": 1})
    )

    assert data.fetch_json("https://example.org/x.json") == {"a": 1}


def test_fetch_json_bad_status_raises_dataloaderror(monkeypatch):
    monkeypatch.setattr(
        data.requests,
        "get",
        lambda url, timeout: FakeResponse(status_error=True),
    )

    with pytest.raises(data.DataLoadError):
        data.fetch_json("https://example.org/missing.json")


def test_fetch_json_network_error_raises_dataloaderror(monkeypatch):
    def broken_get(url, timeout):
        raise requests.exceptions.ConnectionError("no internet")

    monkeypatch.setattr(data.requests, "get", broken_get)

    with pytest.raises(data.DataLoadError):
        data.fetch_json("https://example.org/x.json")


# list_races


def test_list_races_keeps_only_grand_prix_folders(monkeypatch):
    listing = [
        {"name": "Bahrain Grand Prix", "type": "dir"},
        {"name": "cache", "type": "dir"},
        {"name": "utils.py", "type": "file"},
        {"name": "Monaco Grand Prix", "type": "dir"},
    ]
    monkeypatch.setattr(data, "fetch_json", lambda url: listing)

    assert data.list_races(2022) == ["Bahrain Grand Prix", "Monaco Grand Prix"]


def test_list_races_uses_the_given_year(monkeypatch):
    seen = []

    def fake_fetch(url):
        seen.append(url)
        return []

    monkeypatch.setattr(data, "fetch_json", fake_fetch)

    data.list_races(2023)

    assert "/TracingInsights/2023/" in seen[0]


# find_race


def test_find_race_ignores_case_and_accepts_partial_name(monkeypatch):
    monkeypatch.setattr(data, "list_races", lambda year: RACES)

    assert data.find_race(2022, "MONACO") == "Monaco Grand Prix"
    assert data.find_race(2022, "bahr") == "Bahrain Grand Prix"


def test_find_race_no_match_raises_and_suggests(monkeypatch):
    monkeypatch.setattr(data, "list_races", lambda year: RACES)

    with pytest.raises(ValueError, match="Did you mean"):
        data.find_race(2022, "bahrian")


def test_find_race_no_match_without_suggestion(monkeypatch):
    monkeypatch.setattr(data, "list_races", lambda year: RACES)

    with pytest.raises(ValueError, match="No 2022 race matches 'xyz'"):
        data.find_race(2022, "xyz")


def test_find_race_several_matches_raises(monkeypatch):
    monkeypatch.setattr(data, "list_races", lambda year: RACES)

    with pytest.raises(ValueError, match="Be more specific"):
        data.find_race(2022, "grand")


# get_session_folder


def test_get_session_folder_translates_code_ignoring_case():
    assert data.get_session_folder("r") == "Race"
    assert data.get_session_folder("Q") == "Qualifying"


def test_get_session_folder_invalid_code_raises():
    with pytest.raises(ValueError, match="Invalid session 'x'"):
        data.get_session_folder("x")


# list_drivers


def test_list_drivers_returns_flat_list_of_codes(monkeypatch):
    payload = {"drivers": [{"driver": "VER"}, {"driver": "GAS"}]}
    monkeypatch.setattr(data, "fetch_json", lambda url: payload)

    assert data.list_drivers(2022, "Bahrain Grand Prix", "R") == ["VER", "GAS"]


def test_list_drivers_translates_session_code_in_url(monkeypatch):
    seen = []

    def fake_fetch(url):
        seen.append(url)
        return {"drivers": []}

    monkeypatch.setattr(data, "fetch_json", fake_fetch)

    data.list_drivers(2022, "Bahrain Grand Prix", "q")

    assert "/Bahrain Grand Prix/Qualifying/drivers.json" in seen[0]


def test_list_drivers_invalid_session_raises_before_download(monkeypatch):
    def fail(url):
        raise AssertionError("fetch_json must not be called")

    monkeypatch.setattr(data, "fetch_json", fail)

    with pytest.raises(ValueError, match="Invalid session 'x'"):
        data.list_drivers(2022, "Bahrain Grand Prix", "x")


# load_driver_laps


def test_load_driver_laps_returns_one_row_per_lap(monkeypatch):
    fake_json = {"lap": [1, 2], "time": [99.07, 97.85], "drv": ["LEC", "LEC"]}
    monkeypatch.setattr(data, "fetch_json", lambda url: fake_json)

    laps = data.load_driver_laps(2022, "Bahrain Grand Prix", "R", "LEC")

    assert len(laps) == 2
    assert list(laps.columns) == ["lap", "time", "drv"]
    assert laps["lap"].tolist() == [1, 2]


def test_load_driver_laps_builds_the_url(monkeypatch):
    seen = []

    def fake_fetch(url):
        seen.append(url)
        return {"lap": [1]}

    monkeypatch.setattr(data, "fetch_json", fake_fetch)

    data.load_driver_laps(2022, "Bahrain Grand Prix", "q", "LEC")

    assert "/TracingInsights/2022/" in seen[0]
    assert "/Bahrain Grand Prix/Qualifying/LEC/laptimes.json" in seen[0]


def test_load_driver_laps_invalid_session_raises_before_download(monkeypatch):
    def fail(url):
        raise AssertionError("fetch_json must not be called")

    monkeypatch.setattr(data, "fetch_json", fail)

    with pytest.raises(ValueError, match="Invalid session 'x'"):
        data.load_driver_laps(2022, "Bahrain Grand Prix", "x", "LEC")


def test_load_driver_laps_lets_download_errors_through(monkeypatch):
    def broken_fetch(url):
        raise data.DataLoadError("404")

    monkeypatch.setattr(data, "fetch_json", broken_fetch)

    with pytest.raises(data.DataLoadError):
        data.load_driver_laps(2022, "Bahrain Grand Prix", "R", "XXX")


# load_laps


def fake_driver_table(year, race, session, driver):
    """Two laps for VER, one lap for any other driver."""
    laps = [1, 2] if driver == "VER" else [1]
    return pd.DataFrame({"lap": laps, "drv": [driver] * len(laps)})


def test_load_laps_stacks_the_drivers_in_order(monkeypatch):
    monkeypatch.setattr(data, "find_race", lambda year, race: "Bahrain Grand Prix")
    monkeypatch.setattr(
        data, "list_drivers", lambda year, race, session: ["VER", "GAS"]
    )
    monkeypatch.setattr(data, "load_driver_laps", fake_driver_table)

    laps = data.load_laps(2022, "bahrain")

    assert laps["drv"].tolist() == ["VER", "VER", "GAS"]
    assert laps["lap"].tolist() == [1, 2, 1]
    assert laps.index.tolist() == [0, 1, 2]


def test_load_laps_passes_the_folder_name_and_session(monkeypatch):
    seen = {}

    def fake_find_race(year, race):
        seen["find_race"] = (year, race)
        return "Bahrain Grand Prix"

    def fake_list_drivers(year, race, session):
        seen["list_drivers"] = (year, race, session)
        return ["VER", "GAS"]

    drivers_asked = []

    def fake_load_driver_laps(year, race, session, driver):
        drivers_asked.append((year, race, session, driver))
        return fake_driver_table(year, race, session, driver)

    monkeypatch.setattr(data, "find_race", fake_find_race)
    monkeypatch.setattr(data, "list_drivers", fake_list_drivers)
    monkeypatch.setattr(data, "load_driver_laps", fake_load_driver_laps)

    data.load_laps(2022, "bahrain", "Q")

    assert seen["find_race"] == (2022, "bahrain")
    assert seen["list_drivers"] == (2022, "Bahrain Grand Prix", "Q")
    assert drivers_asked == [
        (2022, "Bahrain Grand Prix", "Q", "VER"),
        (2022, "Bahrain Grand Prix", "Q", "GAS"),
    ]


def test_load_laps_default_session_is_the_race(monkeypatch):
    seen = []

    def fake_list_drivers(year, race, session):
        seen.append(session)
        return ["VER"]

    monkeypatch.setattr(data, "find_race", lambda year, race: "Bahrain Grand Prix")
    monkeypatch.setattr(data, "list_drivers", fake_list_drivers)
    monkeypatch.setattr(data, "load_driver_laps", fake_driver_table)

    data.load_laps(2022, "bahrain")

    assert seen == ["R"]


def test_load_laps_stops_when_one_download_fails(monkeypatch):
    def fail_for_gas(year, race, session, driver):
        if driver == "GAS":
            raise data.DataLoadError("404")
        return fake_driver_table(year, race, session, driver)

    monkeypatch.setattr(data, "find_race", lambda year, race: "Bahrain Grand Prix")
    monkeypatch.setattr(
        data, "list_drivers", lambda year, race, session: ["VER", "GAS"]
    )
    monkeypatch.setattr(data, "load_driver_laps", fail_for_gas)

    with pytest.raises(data.DataLoadError):
        data.load_laps(2022, "bahrain")


# prepare_laps


def make_raw_laps():
    """Two laps as downloaded: missing values are the text "None"."""
    return pd.DataFrame(
        {
            "time": [95.2, "None"],
            "lap": [1, 2],
            "compound": ["SOFT", "SOFT"],
            "stint": [1, 1],
            "life": [1, 2],
            "pos": [1, "None"],
            "status": ["1", "1"],
            "drv": ["VER", "VER"],
            "pout": ["None", "None"],
            "pin": ["None", 80.0],
            "fresh": [True, True],
            "team": ["Red Bull Racing", "Red Bull Racing"],
            "del": [False, False],
            "iacc": [True, True],
            "s1": [30.1, "None"],
        }
    )


def test_columns_to_convert_are_all_kept():
    assert set(data.COLUMNS_TO_CONVERT) <= set(data.COLUMNS)


def test_prepare_laps_keeps_only_the_chosen_columns():
    laps = data.prepare_laps(make_raw_laps())

    assert list(laps.columns) == data.COLUMNS


def test_prepare_laps_turns_none_text_into_nan():
    laps = data.prepare_laps(make_raw_laps())

    assert laps["pos"].isna().tolist() == [False, True]
    assert laps["pin"].isna().tolist() == [True, False]
    assert laps["pout"].isna().tolist() == [True, True]


def test_prepare_laps_converts_to_numbers():
    laps = data.prepare_laps(make_raw_laps())

    for column in data.COLUMNS_TO_CONVERT:
        assert pd.api.types.is_float_dtype(laps[column])
    assert laps["time"][0] == 95.2


def test_prepare_laps_leaves_the_other_columns_alone():
    laps = data.prepare_laps(make_raw_laps())

    assert laps["lap"].tolist() == [1, 2]
    assert laps["compound"].tolist() == ["SOFT", "SOFT"]
    assert laps["fresh"].tolist() == [True, True]


def test_prepare_laps_does_not_modify_its_input():
    raw = make_raw_laps()

    data.prepare_laps(raw)

    assert raw.shape == (2, 15)
    assert raw["pos"].tolist() == [1, "None"]


def test_prepare_laps_missing_column_raises():
    raw = make_raw_laps().drop(columns=["team"])

    with pytest.raises(KeyError):
        data.prepare_laps(raw)
