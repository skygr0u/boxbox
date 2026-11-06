"""Download and load the lap data of a race from TracingInsights."""

import requests

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