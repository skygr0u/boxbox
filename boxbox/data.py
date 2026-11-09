"""Download and load the lap data of a race from TracingInsights."""

import requests

CONTENTS_URL = "https://api.github.com/repos/TracingInsights/{year}/contents"
TIMEOUT_SECONDS = 20


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
