"""Box, Box: a small web app to explore the lap data of a Formula 1 race."""

import streamlit as st

from boxbox.analysis import (
    driver_strategies,
    get_stints,
    race_pace,
    race_results,
    tyre_degradation,
)
from boxbox.cleaning import mark_clean_laps
from boxbox.data import (
    GRAND_PRIX_SUFFIX,
    DataLoadError,
    get_laps,
    list_races,
    prepare_laps,
)
from boxbox.plots import plot_degradation, plot_race_pace, plot_strategies

# Compounds used in the rain.
WET_COMPOUNDS = ["INTERMEDIATE", "WET"]

st.set_page_config(page_title="Box, Box", layout="wide")


@st.cache_data(show_spinner=False)
def race_names(year):
    """Return the official names of the Grand Prix of a season."""
    return list_races(year)


@st.cache_data(show_spinner="Loading the race...")
def load_race(year, race):
    """Return the prepared laps of a race, with the column ``is_clean``."""
    return mark_clean_laps(prepare_laps(get_laps(year, race)))


st.title("Box, Box")
st.caption("Pace, tyre strategy and tyre degradation of a Formula 1 race.")

st.sidebar.header("Race")
year = st.sidebar.selectbox("Season", [2022, 2023, 2024, 2025, 2026])

try:
    names = race_names(year)
except DataLoadError as error:
    st.error(str(error))
    st.stop()

default = names.index("Bahrain Grand Prix") if "Bahrain Grand Prix" in names else 0
official_name = st.sidebar.selectbox("Grand Prix", names, index=default)
if official_name is None:  # a season without races has nothing to choose
    st.warning(f"No races found for {year}.")
    st.stop()

# The snapshot file is named after the short name ("Bahrain"), so a race is
# always saved under the same name, whatever the user does.
race = official_name.removesuffix(GRAND_PRIX_SUFFIX)

try:
    laps = load_race(year, race)
except (ValueError, DataLoadError) as error:
    st.error(str(error))
    st.stop()

st.subheader(f"{official_name} {year}")
laps_column, drivers_column, clean_column = st.columns(3)
laps_column.metric("Laps", len(laps))
drivers_column.metric("Drivers", laps["drv"].nunique())
clean_column.metric("Clean laps", int(laps["is_clean"].sum()))

wet_share = laps.loc[laps["is_clean"], "compound"].isin(WET_COMPOUNDS).mean()
dry_only = False
if wet_share > 0.95:
    st.info(
        "This was a wet race. Pace is compared between drivers in the same "
        "conditions, but lap times are not comparable with a dry race."
    )
elif wet_share > 0.05:
    st.warning(
        f"{wet_share:.0%} of the clean laps were on wet-weather tyres. "
        "The median pace mixes wet and dry laps: tick the box in the sidebar "
        "to compute the pace on dry-tyre laps only."
    )
    dry_only = st.sidebar.checkbox("Pace on dry-tyre laps only")

results_tab, pace_tab, strategy_tab, degradation_tab = st.tabs(
    ["Results", "Pace", "Strategy", "Degradation"]
)

with results_tab:
    st.dataframe(race_results(laps), hide_index=True)
    st.caption(
        "Order and gaps are rebuilt from the lap times, so they can differ "
        "from the official result by a few tenths of a second. Penalties given "
        "after the race are not included. A time shows n/a when the data has "
        "no lap time for the first lap, and after a red flag the gaps are not "
        "reliable."
    )

with pace_tab:
    pace_laps = laps[~laps["compound"].isin(WET_COMPOUNDS)] if dry_only else laps
    pace = race_pace(pace_laps)
    st.pyplot(plot_race_pace(pace))
    st.dataframe(pace, hide_index=True)

with strategy_tab:
    strategies = driver_strategies(laps)
    stints = get_stints(laps)
    all_drivers = strategies["drv"].tolist()
    chosen = st.multiselect("Drivers", all_drivers, default=all_drivers)
    # Keep the finishing order, whatever the order of the clicks.
    shown = [driver for driver in all_drivers if driver in chosen]
    if shown:
        st.pyplot(plot_strategies(stints, drivers=shown))
    else:
        st.info("Choose at least one driver.")
    st.dataframe(strategies, hide_index=True)

with degradation_tab:
    degradation = tyre_degradation(laps)
    if degradation.empty:
        st.info("No stint is long enough to measure tyre degradation in this race.")
    else:
        st.pyplot(plot_degradation(degradation))
        st.caption(
            "Each dot is one stint: the time gained or lost per lap as the tyre "
            "ages. Fuel burn is not removed, so real wear is underestimated."
        )
        if wet_share > 0.05:
            st.caption(
                "In wet or mixed races these values mostly reflect the changing "
                "track conditions, not tyre wear."
            )
        st.dataframe(degradation, hide_index=True)
