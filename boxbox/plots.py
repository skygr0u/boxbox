"""Draw the charts of the project. Every function returns a figure."""

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

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