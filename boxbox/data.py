"""Download and load the lap data of a race from TracingInsights."""

import requests
import difflib
import requests


CONTENTS_URL = "https://api.github.com/repos/TracingInsights/{year}/contents"
TIMEOUT_SECONDS = 20
GRAND_PRIX_SUFFIX = " Grand Prix"


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
