"""Tests for boxbox.data. No test uses the internet: downloads are faked."""

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
