"""Draw the charts of the project. Every function returns a figure."""

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# The colours of the tyres in the races (the white of HARD gets a black edge).
COMPOUND_COLOURS = {
    "SOFT": "#e8002d",
    "MEDIUM": "#ffd12e",
    "HARD": "#f0f0f0",
    "INTERMEDIATE": "#43b02a",
    "WET": "#0067ad",
    "UNKNOWN": "#999999",
}

# The colours of the teams of the 2022 season, as named in the lap data. A team
# that is not listed (a new or renamed team) is drawn in UNKNOWN_TEAM_COLOUR.
TEAM_COLOURS = {
    "Alfa Romeo": "#900000",
    "AlphaTauri": "#2b4562",
    "Alpine": "#0093cc",
    "Aston Martin": "#006f62",
    "Ferrari": "#dc0000",
    "Haas F1 Team": "#c8c8c8",
    "McLaren": "#ff8700",
    "Mercedes": "#00d2be",
    "Red Bull Racing": "#1e41ff",
    "Williams": "#64c4ff",
}
UNKNOWN_TEAM_COLOUR = "#555555"


def plot_race_pace(pace):
    """
    Draw the race pace of the drivers as horizontal bars, coloured by team.

    Each bar is the gap in seconds between the driver's median clean lap and
    the fastest driver's, so the fastest driver has no bar. The fastest
    driver is at the top. A team that has no colour in ``TEAM_COLOURS`` is
    drawn in ``UNKNOWN_TEAM_COLOUR``.

    Parameters
    ----------
    pace : pandas.DataFrame
        Table as returned by ``race_pace``, with the columns ``drv``,
        ``team`` and ``gap``, from the fastest to the slowest driver.

    Returns
    -------
    matplotlib.figure.Figure
        The figure. It is not shown and not saved: the caller decides.

    Raises
    ------
    KeyError
        If ``drv``, ``team`` or ``gap`` is missing.
    """
    colours = [TEAM_COLOURS.get(team, UNKNOWN_TEAM_COLOUR) for team in pace["team"]]

    fig, ax = plt.subplots(figsize=(10, 0.4 * len(pace) + 1.5))
    ax.barh(pace["drv"], pace["gap"], color=colours, edgecolor="black")
    ax.invert_yaxis()
    ax.set_xlabel("Gap to the fastest driver (seconds)")
    ax.set_title("Race pace: median clean lap")

    teams = list(dict.fromkeys(pace["team"]))
    handles = [
        Patch(
            facecolor=TEAM_COLOURS.get(team, UNKNOWN_TEAM_COLOUR),
            edgecolor="black",
            label=team,
        )
        for team in teams
    ]
    ax.legend(handles=handles, title="Team", loc="upper left", bbox_to_anchor=(1.01, 1))
    return fig


def plot_strategies(stints, drivers=None):
    """
    Draw the tyre strategy of every driver as one row of coloured blocks.

    Each block is a stint: it starts at the first lap of the stint and is as
    long as the stint, in the colour of its compound.

    Parameters
    ----------
    stints : pandas.DataFrame
        Table as returned by ``get_stints``, with the columns ``drv``,
        ``compound``, ``start_lap`` and ``end_lap``.
    drivers : list of str, optional
        The drivers to draw, from the top row to the bottom row, for example
        in finishing order. By default, the order of ``stints``.

    Returns
    -------
    matplotlib.figure.Figure
        The figure. It is not shown and not saved: the caller decides.

    Raises
    ------
    KeyError
        If one of the columns listed above is missing.
    """
    if drivers is None:
        drivers = list(stints["drv"].unique())

    fig, ax = plt.subplots(figsize=(10, 0.4 * len(drivers) + 1.5))
    for row, drv in enumerate(drivers):
        for _, stint in stints[stints["drv"] == drv].iterrows():
            colour = COMPOUND_COLOURS.get(
                stint["compound"], COMPOUND_COLOURS["UNKNOWN"]
            )
            ax.barh(
                row,
                stint["end_lap"] - stint["start_lap"] + 1,
                left=stint["start_lap"] - 1,
                color=colour,
                edgecolor="black",
            )

    ax.set_yticks(range(len(drivers)))
    ax.set_yticklabels(drivers)
    ax.invert_yaxis()
    ax.set_xlabel("Lap")
    ax.set_title("Tyre strategies")

    used = set(stints["compound"])
    handles = [
        Patch(facecolor=colour, edgecolor="black", label=compound)
        for compound, colour in COMPOUND_COLOURS.items()
        if compound in used
    ]
    ax.legend(
        handles=handles, title="Compound", loc="upper left", bbox_to_anchor=(1.01, 1)
    )
    return fig
