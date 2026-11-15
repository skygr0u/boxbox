"""Decide which laps are representative of the race pace."""

import pandas as pd

FIRST_LAP = 1
# Track status code for a clear track (see the notes on the status column).
GREEN_STATUS = "1"


def mark_clean_laps(laps):
    """
    Add a column ``is_clean`` that marks the laps usable for pace analysis.

    Every row is kept. A lap is not clean (``is_clean`` is False) if at least
    one of these six rules applies:

    - pit lap: an in-lap or an out-lap (``pin`` or ``pout`` is not missing);
    - lap 1: standing start, with the cars bunched up;
    - not green: the status is not ``"1"`` (safety car, virtual safety car or
      yellow flag at some point of the lap);
    - deleted: the stewards deleted the lap (``del`` is True);
    - inaccurate: the timing is not accurate (``iacc`` is False);
    - no time: the lap time is missing.

    Parameters
    ----------
    laps : pandas.DataFrame
        Table as returned by ``prepare_laps``, with the columns ``lap``,
        ``time``, ``status``, ``pin``, ``pout``, ``del`` (bool) and ``iacc``
        (bool).

    Returns
    -------
    pandas.DataFrame
        A copy of ``laps`` with the extra boolean column ``is_clean``. The
        input table is not modified.

    Raises
    ------
    KeyError
        If one of the columns listed above is missing.
    """
    results = laps.copy()

    rules = {
        "pit lap": results["pin"].notna() | results["pout"].notna(),
        "lap 1": results["lap"] == FIRST_LAP,
        "not green": results["status"] != GREEN_STATUS,
        "deleted": results["del"],
        "inaccurate": ~results["iacc"],
        "no time": results["time"].isna(),
    }

    bad_lap = pd.concat(rules, axis=1).any(axis=1)
    results["is_clean"] = ~bad_lap
    return results
