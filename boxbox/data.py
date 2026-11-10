"""Download and load the lap data of a race from TracingInsights."""

import difflib

import pandas as pd
import requests

CONTENTS_URL = "https://api.github.com/repos/TracingInsights/{year}/contents"
DRIVERS_URL = (
    "https://raw.githubusercontent.com/TracingInsights/{year}/main/"
    "{race}/{session}/drivers.json"
)
DRIVER_LAPS_URL = (
    "https://raw.githubusercontent.com/TracingInsights/{year}/main/"
    "{race}/{session}/{driver}/laptimes.json"
)

TIMEOUT_SECONDS = 20

GRAND_PRIX_SUFFIX = " Grand Prix"

SESSION_FOLDERS = {
    "R": "Race",
    "Q": "Qualifying",
    "S": "Sprint",
    "P1": "Practice 1",
    "P2": "Practice 2",
    "P3": "Practice 3",
}


class DataLoadError(Exception):
    """Raised when data cannot be downloaded or read."""


def fetch_json(url):
    """
    Download a URL and return its content parsed as JSON.

    Parameters
    ----------
    url : str
        Address of a JSON file.

    Returns
    -------
    dict or list
        The parsed JSON content.

    Raises
    ------
    DataLoadError
        If the request fails, the server answers with an error status,
        or the response is not valid JSON.
    """
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as error:
        raise DataLoadError(f"Could not download {url}: {error}") from error


def list_races(year):
    """
    List the Grand Prix folders available for a season.

    A year without a repository makes ``fetch_json`` raise a
    ``DataLoadError``, which is not caught here.

    Parameters
    ----------
    year : int
        Season, for example 2022.

    Returns
    -------
    list of str
        Folder names such as ``"Bahrain Grand Prix"``, in the alphabetical
        order returned by GitHub.
    """
    entries = fetch_json(CONTENTS_URL.format(year=year))
    return [
        entry["name"]
        for entry in entries
        if entry["type"] == "dir" and entry["name"].endswith("Grand Prix")
    ]


def find_race(year, name):
    """
    Find the folder name of a race from the text typed by the user.

    The match ignores upper and lower case and accepts any text contained
    in the folder name, so ``"bahrain"`` finds ``"Bahrain Grand Prix"``.
    Accents are not ignored: ``"sao paulo"`` does not match
    ``"São Paulo Grand Prix"``, but it is suggested in the error message.

    Parameters
    ----------
    year : int
        Season, for example 2022.
    name : str
        Full or partial name of the race.

    Returns
    -------
    str
        The folder name of the race, for example ``"Bahrain Grand Prix"``.

    Raises
    ------
    ValueError
        If no race matches the name, or if more than one does.
    """
    races = list_races(year)
    matches = [race for race in races if name.lower() in race.lower()]

    if len(matches) == 0:
        short_names = [race.removesuffix(GRAND_PRIX_SUFFIX).lower() for race in races]
        close = difflib.get_close_matches(name.lower(), short_names, n=3)
        hint = f" Did you mean: {close}?" if close else ""
        raise ValueError(f"No {year} race matches '{name}'.{hint}")
    if len(matches) > 1:
        raise ValueError(
            f"'{name}' matches {len(matches)} races in {year}: {matches}. "
            "Be more specific."
        )
    return matches[0]


def get_session_folder(session):
    """
    Translate a session code into the name of its folder on GitHub.

    Parameters
    ----------
    session : str
        Session code, one of the keys of ``SESSION_FOLDERS`` (``"R"`` for the
        race, ``"Q"`` for qualifying, ...). Upper and lower case are accepted.

    Returns
    -------
    str
        The folder name, for example ``"Race"`` for ``"R"``.

    Raises
    ------
    ValueError
        If the session code is not one of ``SESSION_FOLDERS``.
    """
    session_folder = SESSION_FOLDERS.get(session.upper())
    if session_folder is None:
        valid = ", ".join(SESSION_FOLDERS)
        raise ValueError(f"Invalid session '{session}'. Use one of: {valid}.")
    return session_folder


def list_drivers(year, race, session):
    """
    List the driver codes of a session.

    Parameters
    ----------
    year : int
        Season, for example 2022.
    race : str
        Folder name of the race, as returned by ``find_race``, for example
        ``"Bahrain Grand Prix"``.
    session : str
        Session code, one of the keys of ``SESSION_FOLDERS`` (``"R"`` for the
        race, ``"Q"`` for qualifying, ...). Upper and lower case are accepted.

    Returns
    -------
    list of str
        Three-letter driver codes, for example ``["VER", "GAS", ...]``.

    Raises
    ------
    ValueError
        If the session code is not one of ``SESSION_FOLDERS``.
    """
    session_folder = get_session_folder(session)
    url = DRIVERS_URL.format(year=year, race=race, session=session_folder)
    data = fetch_json(url)
    return [entry["driver"] for entry in data["drivers"]]


def load_driver_laps(year, race, session, driver):
    """
    Download the laps of one driver in a session as a table.

    The table has one row per lap and one column per field of
    ``laptimes.json``. The values are returned as downloaded: missing values
    are still the text ``"None"``.

    Parameters
    ----------
    year : int
        Season, for example 2022.
    race : str
        Folder name of the race, as returned by ``find_race``, for example
        ``"Bahrain Grand Prix"``.
    session : str
        Session code, one of the keys of ``SESSION_FOLDERS``. Upper and lower
        case are accepted.
    driver : str
        Three-letter driver code, for example ``"LEC"``.

    Returns
    -------
    pandas.DataFrame
        One row per lap of the driver.

    Raises
    ------
    ValueError
        If the session code is not one of ``SESSION_FOLDERS``.
    """
    session_folder = get_session_folder(session)
    url = DRIVER_LAPS_URL.format(
        year=year, race=race, session=session_folder, driver=driver
    )
    data = fetch_json(url)
    return pd.DataFrame(data)


def load_laps(year, race, session="R"):
    """
    Load the laps of all the drivers of a session as one table.

    The race name can be partial and in any case (``"bahrain"``). The result
    has one row per lap per driver, in the order of ``list_drivers``, with the
    values as downloaded (missing values are still the text ``"None"``).

    Parameters
    ----------
    year : int
        Season, for example 2022.
    race : str
        Full or partial name of the race, as typed by the user.
    session : str, optional
        Session code, one of the keys of ``SESSION_FOLDERS``. Defaults to
        ``"R"`` (the race).

    Returns
    -------
    pandas.DataFrame
        One row per lap of every driver. The column ``drv`` tells which
        driver a row belongs to.

    Raises
    ------
    ValueError
        If the race name matches no race or several races, or if the session
        code is not valid.
    DataLoadError
        If any of the downloads fails: the table is never returned with a
        driver missing.
    """
    race_folder = find_race(year, race)
    driver_codes = list_drivers(year, race_folder, session)
    tables = [
        load_driver_laps(year, race_folder, session, driver) for driver in driver_codes
    ]
    return pd.concat(tables, ignore_index=True)
