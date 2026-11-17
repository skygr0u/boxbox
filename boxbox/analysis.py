"""Answer the questions about the race: pace, tyre strategy, degradation."""

# A driver needs at least this share of the clean laps of the driver who has
# the most of them, to be compared fairly (a driver who retired early is out).
MIN_LAP_SHARE = 0.7

# A driver is classified if he completed at least this share of the laps of
# the driver who completed the most (the official rule of the championship).
CLASSIFIED_SHARE = 0.9


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


def driver_strategies(laps):
    """
    Summarise the race of every driver: strategy and outcome.

    The strategy of a driver is the sequence of the compounds of his stints,
    for example ``"SOFT-MEDIUM-SOFT"``. The outcome is the last valid
    position. Drivers who retired stay in the table: ``classified`` tells
    whether their outcome can be compared with the others.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``mark_clean_laps`` (or ``prepare_laps``), with
        the columns ``drv``, ``team``, ``stint``, ``compound``, ``lap``,
        ``life`` and ``pos``. All the laps are used, not only the clean ones.

    Returns
    -------
    pandas.DataFrame
        One row per driver, with the columns:

        - ``drv``: driver code;
        - ``team``: team name;
        - ``strategy``: compounds of the stints, in order, joined by ``-``;
        - ``stops``: number of pit stops (number of stints minus one);
        - ``laps_driven``: number of laps of the driver;
        - ``classified``: True if ``laps_driven`` is at least
          ``CLASSIFIED_SHARE`` of the highest ``laps_driven``;
        - ``pos_lap1``: position at the end of lap 1. This is **not** the
          starting grid, which is not in the lap data;
        - ``final_pos``: last position that is not missing (the position
          before retiring, for a driver who did not finish);
        - ``positions_gained``: ``pos_lap1 - final_pos``, positive when the
          driver moved up since lap 1.

        The classified drivers come first, in order of final position, then
        the others in the same way. The input table is not modified.

    Raises
    ------
    KeyError
        If one of the columns listed above is missing.
    """
    stints = get_stints(laps)
    summary = stints.groupby("drv").agg(
        strategy=("compound", "-".join),
        number_of_stints=("stint", "count"),
    )
    summary["stops"] = summary["number_of_stints"] - 1

    ordered = laps.sort_values(["drv", "lap"])
    by_driver = ordered.groupby("drv")
    summary["team"] = by_driver["team"].first()
    summary["laps_driven"] = by_driver["lap"].count()
    summary["pos_lap1"] = ordered[ordered["lap"] == 1].set_index("drv")["pos"]
    summary["final_pos"] = ordered.dropna(subset=["pos"]).groupby("drv")["pos"].last()

    most_laps = summary["laps_driven"].max()
    summary["classified"] = summary["laps_driven"] >= CLASSIFIED_SHARE * most_laps
    summary["positions_gained"] = summary["pos_lap1"] - summary["final_pos"]

    columns = [
        "team",
        "strategy",
        "stops",
        "laps_driven",
        "classified",
        "pos_lap1",
        "final_pos",
        "positions_gained",
    ]
    summary = summary[columns].sort_values(
        ["classified", "final_pos"], ascending=[False, True]
    )
    return summary.reset_index()
