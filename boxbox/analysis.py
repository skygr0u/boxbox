"""Answer the questions about the race: pace, tyre strategy, degradation."""

# A driver needs at least this share of the clean laps of the driver who has
# the most of them, to be compared fairly (a driver who retired early is out).
MIN_LAP_SHARE = 0.7


def race_pace(laps):
    """
    Compare the race pace of the drivers.

    The pace of a driver is the median time of their clean laps. The median
    is used instead of the mean because a few odd laps (traffic, a mistake)
    do not move it. Only the laps with ``is_clean`` True are used, and a
    driver is left out if they have fewer clean laps than ``MIN_LAP_SHARE``
    of the driver with the most clean laps.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``mark_clean_laps``, with the columns ``drv``,
        ``team``, ``time`` and ``is_clean``.

    Returns
    -------
    pandas.DataFrame
        One row per driver, from the fastest to the slowest, with the columns:

        - ``drv``: driver code;
        - ``team``: team name;
        - ``clean_laps``: number of clean laps used;
        - ``median_lap_time``: median lap time in seconds;
        - ``gap``: seconds behind the fastest median (0 for the fastest).

        The input table is not modified.

    Raises
    ------
    KeyError
        If one of the columns listed above is missing.
    """
    clean = laps[laps["is_clean"]]
    pace = clean.groupby(["drv", "team"]).agg(
        clean_laps=("time", "count"),
        median_lap_time=("time", "median"),
    )

    threshold = pace["clean_laps"].max() * MIN_LAP_SHARE
    pace = pace[pace["clean_laps"] >= threshold]

    pace["gap"] = pace["median_lap_time"] - pace["median_lap_time"].min()
    return pace.sort_values("median_lap_time").reset_index()
