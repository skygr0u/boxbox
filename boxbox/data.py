"""Download and load the lap data of a race from TracingInsights."""

import difflib
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SNAPSHOTS_DIR = PROJECT_ROOT / "data" / "snapshots"

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

COLUMNS = [
    "time",
    "lap",
    "compound",
    "stint",
    "life",
    "pos",
    "status",
    "drv",
    "pout",
    "pin",
    "fresh",
    "team",
    "del",
    "iacc",
]

COLUMNS_TO_CONVERT = ["time", "pos", "pin", "pout"]


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


def prepare_laps(laps):
    """
    Keep the columns used by the analysis and convert the numbers.

    Only the columns in ``COLUMNS`` are kept. In the columns of
    ``COLUMNS_TO_CONVERT`` the text ``"None"`` (and any other text that is not
    a number) becomes ``NaN`` and the column becomes numeric. The input table
    is not modified.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``load_laps``, with the columns of ``COLUMNS``.

    Returns
    -------
    pandas.DataFrame
        A new table with the columns of ``COLUMNS`` only.

    Raises
    ------
    KeyError
        If a column of ``COLUMNS`` is missing from ``laps``.
    """
    laps = laps[COLUMNS].copy()
    for column in COLUMNS_TO_CONVERT:
        laps[column] = pd.to_numeric(laps[column], errors="coerce")
    return laps


def snapshot_path(year, race, session):
    """
    Build the path of the CSV snapshot of a session.

    The name is built from the text given by the user, without any download,
    so it can be computed offline. For example, ``(2022, "Bahrain", "r")``
    gives ``data/snapshots/2022_bahrain_R.csv``.

    Parameters
    ----------
    year : int
        Season, for example 2022.
    race : str
        Race name as typed by the user. It is put in lower case and the
        spaces become ``_``.
    session : str
        Session code, for example ``"R"``. It is put in upper case.

    Returns
    -------
    pathlib.Path
        Path of the file, inside ``SNAPSHOTS_DIR``. The file may not exist.
    """
    race_name = race.lower().replace(" ", "_")
    return SNAPSHOTS_DIR / f"{year}_{race_name}_{session.upper()}.csv"


def save_laps(laps, path):
    """
    Save a table of laps as a CSV file.

    The folder is created if it does not exist, and an existing file is
    overwritten. The row numbers are not written.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table to save, for example the result of ``load_laps``.
    path : str or pathlib.Path
        Destination file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    laps.to_csv(path, index=False)


def read_laps(path):
    """
    Read a CSV file written by ``save_laps``.

    The column ``status`` is read as text: without this, ``"12"`` would
    become the number 12 and ``"1"`` the number 1, and a comparison with
    ``"1"`` would never be true. The text ``"None"`` of the original data
    is read as ``NaN``.

    Parameters
    ----------
    path : str or pathlib.Path
        File to read.

    Returns
    -------
    pandas.DataFrame
        The saved table.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    """
    return pd.read_csv(path, dtype={"status": str})


def get_laps(year, race, session="R", refresh=False):
    """
    Return the laps of a session, downloading them only when needed.

    The table is read from the CSV snapshot of ``snapshot_path``. If the file
    does not exist, or ``refresh`` is true, the laps are first downloaded with
    ``load_laps`` and saved as a snapshot. In both cases the returned table is
    the one read from the file, so it has the same types whether or not a
    download took place.

    The table is the raw one (all the columns). Use ``prepare_laps`` to keep
    the columns of the analysis and convert the numbers.

    Parameters
    ----------
    year : int
        Season, for example 2022.
    race : str
        Full or partial name of the race, for example ``"bahrain"``.
    session : str, optional
        Session code, one of the keys of ``SESSION_FOLDERS``. Defaults to
        ``"R"`` (the race).
    refresh : bool, optional
        If true, download again and overwrite the snapshot. Defaults to
        False.

    Returns
    -------
    pandas.DataFrame
        One row per lap of every driver.

    Raises
    ------
    ValueError
        If a download is needed and the race name or the session is not valid.
    DataLoadError
        If a download is needed and it fails. The existing snapshot, if any,
        is left untouched.
    """
    path = snapshot_path(year, race, session)
    if refresh or not path.exists():
        laps = load_laps(year, race, session)
        save_laps(laps, path)
    return read_laps(path)
