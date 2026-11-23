"""Answer the questions about the race: pace, tyre strategy, degradation."""

import pandas as pd

# A driver needs at least this share of the clean laps of the driver who has
# the most of them, to be compared fairly (a driver who retired early is out).
MIN_LAP_SHARE = 0.7

# A driver is classified if he completed at least this share of the laps of
# the driver who completed the most (the official rule of the championship).
CLASSIFIED_SHARE = 0.9


# A stint is compared at its start and at its end: this is the number of
# clean laps averaged at each end.
FIRST_LAST_LAPS = 3

# Stints with fewer clean laps are left out: on Bahrain 2022 they gave
# extreme values (from -0.40 to +0.31 s per lap) because the two ends of the
# stint are too close in tyre age.
MIN_CLEAN_LAPS = 10


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
    for example ``"SOFT-MEDIUM-SOFT"``. The outcome is the finishing order,
    built like the official classification: the driver who completed more
    laps is ahead, and drivers with the same number of laps are ordered by
    their last position. A driver who retired stays in the table, at the
    place his laps give him; ``classified`` tells whether he completed enough
    laps to be classified.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``mark_clean_laps`` (or ``prepare_laps``), with
        the columns ``drv``, ``team``, ``stint``, ``compound``, ``lap``,
        ``life``, ``time`` and ``pos``. All the laps are used, not only the
        clean ones.

    Returns
    -------
    pandas.DataFrame
        One row per driver, ordered by ``final_pos``, with the columns:

        - ``drv``: driver code;
        - ``team``: team name;
        - ``strategy``: compounds of the stints, in order, joined by ``-``;
        - ``stops``: number of pit stops (number of stints minus one);
        - ``laps_completed``: number of laps with a lap time (a final lap
          that was not completed has none);
        - ``classified``: True if ``laps_completed`` is at least
          ``CLASSIFIED_SHARE`` of the highest ``laps_completed``;
        - ``pos_lap1``: position at the end of lap 1. This is **not** the
          starting grid, which is not in the lap data;
        - ``final_pos``: place in the finishing order, 1 to the number of
          drivers, without ties;
        - ``positions_gained``: ``pos_lap1 - final_pos``, positive when the
          driver moved up since lap 1. For a driver who retired it includes
          the effect of the retirement.

        The input table is not modified.

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
    summary["team"] = ordered.groupby("drv")["team"].first()
    summary["pos_lap1"] = ordered[ordered["lap"] == 1].set_index("drv")["pos"]

    completed = ordered.dropna(subset=["time"])
    summary["laps_completed"] = completed.groupby("drv")["lap"].count()

    with_position = ordered.dropna(subset=["pos"])
    last_pos = with_position.groupby("drv")["pos"].last()

    most_laps = summary["laps_completed"].max()
    summary["classified"] = summary["laps_completed"] >= CLASSIFIED_SHARE * most_laps

    # More laps first; the same number of laps: the better last position.
    summary["last_pos"] = last_pos
    summary = summary.sort_values(
        ["laps_completed", "last_pos"], ascending=[False, True]
    )
    summary["final_pos"] = range(1, len(summary) + 1)
    summary["positions_gained"] = summary["pos_lap1"] - summary["final_pos"]

    columns = [
        "team",
        "strategy",
        "stops",
        "laps_completed",
        "classified",
        "pos_lap1",
        "final_pos",
        "positions_gained",
    ]
    return summary[columns].reset_index()


def tyre_degradation(laps):
    """Measure how much lap time a set of tyres loses per lap of age.

    For each stint, the mean of the first clean laps is compared with the
    mean of the last clean laps. The difference in lap time is divided by
    the difference in tyre age (``life``).

    Parameters
    ----------
    laps : pandas.DataFrame
        Prepared laps with the columns ``drv``, ``stint``, ``compound``,
        ``life``, ``time`` and ``is_clean``.

    Returns
    -------
    pandas.DataFrame
        One row per driver and stint with the columns ``drv``, ``stint``,
        ``compound``, ``clean_laps`` and ``degradation_per_lap`` (seconds
        lost per lap of tyre age). Stints with fewer than
        ``MIN_CLEAN_LAPS`` clean laps are left out.

    Raises
    ------
    KeyError
        If a required column is missing.

    Notes
    -----
    The fuel burned during the stint makes the car faster, so the value
    measured here is smaller than the real wear of the tyre.
    """
    clean = laps[laps["is_clean"]].copy()
    clean["compound"] = clean["compound"].fillna("UNKNOWN")
    clean = clean.sort_values(["drv", "stint", "life"])

    rows = []
    for (drv, stint), group in clean.groupby(["drv", "stint"]):
        if len(group) < MIN_CLEAN_LAPS:
            continue
        first = group.head(FIRST_LAST_LAPS)
        last = group.tail(FIRST_LAST_LAPS)
        time_change = last["time"].mean() - first["time"].mean()
        age_change = last["life"].mean() - first["life"].mean()
        rows.append(
            {
                "drv": drv,
                "stint": stint,
                "compound": group["compound"].iloc[0],
                "clean_laps": len(group),
                "degradation_per_lap": time_change / age_change,
            }
        )
    columns = ["drv", "stint", "compound", "clean_laps", "degradation_per_lap"]
    return pd.DataFrame(rows, columns=columns)


def format_race_time(seconds):
    """
    Write a time in seconds as ``h:mm:ss.mmm``, like ``1:27:39.624``.

    Parameters
    ----------
    seconds : float
        Time in seconds.

    Returns
    -------
    str
        The time as hours, minutes, seconds and milliseconds.
    """
    total_ms = round(seconds * 1000)
    hours, rest = divmod(total_ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    return f"{hours}:{minutes:02d}:{rest / 1000:06.3f}"


def race_results(laps):
    """
    Build the results table of the race, like the one of the F1 website.

    The order is the finishing order of ``driver_strategies``. The winner
    gets his race time, the sum of his lap times. The other drivers get the
    gap to the winner, ``+0.639s``, if they completed the same number of
    laps, or ``+1 lap`` / ``+2 laps`` if they are lapped. A driver who was
    not classified gets ``DNF``. When a time cannot be trusted, the table
    says ``n/a``: see the notes.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``mark_clean_laps`` (or ``prepare_laps``), with
        the columns needed by ``driver_strategies`` (``drv``, ``team``,
        ``stint``, ``compound``, ``lap``, ``life``, ``time`` and ``pos``).
        All the laps are used, not only the clean ones.

    Returns
    -------
    pandas.DataFrame
        One row per driver, ordered by ``final_pos``, with the columns
        ``final_pos``, ``drv``, ``team``, ``laps`` and ``time`` (text, as
        described above).

    Notes
    -----
    ``laps`` is the highest lap number that has a lap time, not the number of
    lap times, because the first lap sometimes has none.

    The race time is the sum of the lap times, so it can differ from the
    official time by a few tenths of a second. A time is trusted only if the
    driver has a lap time for every lap up to his last one; if a lap time is
    missing, the sum is too short and the time is ``n/a``. A gap needs the
    times of both drivers. After a red flag the time spent in the pits is not
    in the lap times, so the gaps are not reliable. The order is the order on
    the track, without penalties given after the race.
    """
    results = driver_strategies(laps)
    with_time = laps.dropna(subset=["time"])
    last_lap = with_time.groupby("drv")["lap"].max()
    race_time = with_time.groupby("drv")["time"].sum()
    complete = with_time.groupby("drv")["time"].count() == last_lap

    results["laps"] = results["drv"].map(last_lap)
    winner = results.iloc[0]

    texts = []
    for row in results.itertuples():
        behind = winner["laps"] - row.laps
        if not row.classified:
            texts.append("DNF")
        elif behind > 0:
            texts.append(f"+{behind} lap" + ("s" if behind > 1 else ""))
        elif not (complete[row.drv] and complete[winner["drv"]]):
            texts.append("n/a")
        elif row.Index == 0:
            texts.append(format_race_time(race_time[row.drv]))
        else:
            texts.append(f"+{race_time[row.drv] - race_time[winner['drv']]:.3f}s")

    results["time"] = texts
    return results[["final_pos", "drv", "team", "laps", "time"]]
