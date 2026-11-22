"""Box, Box: a small web app to explore the lap data of a Formula 1 race."""

import streamlit as st

# Must be the first Streamlit call of the script.
st.set_page_config(page_title="Box, Box", layout="wide")

st.title("Box, Box")
st.caption("Pace, tyre strategy and tyre degradation of a Formula 1 race.")

# The inputs live in the sidebar.
st.sidebar.header("Race")
year = st.sidebar.selectbox("Season", [2022, 2023, 2024, 2025])
race = st.sidebar.text_input("Race name", value="bahrain")

st.write(f"You chose: **{race}**, {year}")