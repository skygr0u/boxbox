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


def get_stints(laps):
    """
    Describe every stint of every driver, one row per stint.

    A stint is the run between two pit stops, on one set of tyres. That set
    can be new or already used, so the table says both the compound and the
    age of the set when it was fitted. All the laps are used, not only the
    clean ones: a stint includes its pit laps and its safety-car laps.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``mark_clean_laps`` (or ``prepare_laps``), with
        the columns ``drv``, ``stint``, ``compound``, ``lap`` and ``life``.

    Returns
    -------
    pandas.DataFrame
        One row per driver and stint, sorted by driver code and then by stint
        number (the order of the ``groupby``), with the columns:

        - ``drv``: driver code;
        - ``stint``: stint number, 1 for the first;
        - ``compound``: tyre compound. It is ``"UNKNOWN"`` only if no lap of
          the stint has a compound (a missing value is skipped in favour of
          the first lap that has one);
        - ``start_lap``, ``end_lap``: first and last lap of the stint;
        - ``laps``: number of laps in the stint;
        - ``life_start``: age of the set on the first lap of the stint (1 for
          a new set, more for a used one).

        The input table is not modified.

    Raises
    ------
    KeyError
        If one of the columns listed above is missing.
    """
    stints = laps.groupby(["drv", "stint"]).agg(
        compound=("compound", "first"),
        start_lap=("lap", "min"),
        end_lap=("lap", "max"),
        laps=("lap", "count"),
        life_start=("life", "min"),
    )
    stints = stints.fillna({"compound": "UNKNOWN"})
    return stints.reset_index()

