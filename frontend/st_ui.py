import streamlit as st
from datetime import datetime, timedelta
from helpers import (
    get_movies_with_screenings,
    format_day,
    fuzzy_match_titles,
    load_image,
    get_watchlist_titles,
    round_to_quarter_hour,
)
import logging
import time
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")
st.title("Amsterdam Screening Finder")

movies_df = get_movies_with_screenings()
movies_df["formatted_day"] = movies_df["show_datetime"].apply(format_day)

ordered_days = ["Today", "Tomorrow"] + sorted(
    [
        day
        for day in movies_df["formatted_day"].unique()
        if day not in ["Today", "Tomorrow"]
    ],
    key=lambda d: datetime.strptime(d.split(" (")[0], "%A").weekday(),
)
ordered_days.insert(0, "All Days")

col1, col2 = st.columns([2, 1])


# Default index for the time selector, to reset time to 10:00 when a new day is selected
def reset_time_on_day_change():
    if selected_day != st.session_state.get("last_selected_day", None):
        st.session_state["selected_time"] = (
            "10:00"  # Reset time to 10:00 when day changes
        )
    st.session_state["last_selected_day"] = selected_day


with col1:
    selected_day = st.selectbox(
        "Select a Day", ordered_days, index=1, key="day_select", disabled=False
    )
    reset_time_on_day_change()  # Call function to reset the time selector

# Set time range from 10:00 to 01:00
time_options = [
    f"{hour:02d}:00" for hour in range(10, 2 + 24)
]  # Time range 10:00 to 01:00
with col2:
    selected_time = st.selectbox(
        "Select Start Time",
        time_options,
        index=time_options.index("10:00"),  # Default to 10:00
        key="time_select",
        disabled=False,
    )

with st.expander("Advanced Filters"):
    letterboxd_username = st.text_input("Enter your Letterboxd username")

    @st.cache_data(show_spinner=False)
    def get_cached_watchlist_titles(username):
        if username:
            return get_watchlist_titles(username)
        return []

    # If username is provided, fetch the watchlist titles and perform fuzzy matching only once
    if letterboxd_username:
        logger.info(f"User provided Letterboxd username: {letterboxd_username}")

        # Fetch watchlist titles only once per username
        watchlist_titles = get_cached_watchlist_titles(letterboxd_username)

        if watchlist_titles:
            logger.info(f"Matching movies against watchlist...")
            # Start timing the fuzzy matching process
            match_start_time = time.time()
            movies_df["in_watchlist"] = movies_df["title"].apply(
                lambda title: fuzzy_match_titles(title, watchlist_titles)
            )
            match_end_time = time.time()
            match_elapsed_time = match_end_time - match_start_time
            logger.info(
                f"Fuzzy matching completed in {match_elapsed_time:.2f} seconds."
            )
        else:
            movies_df["in_watchlist"] = False
    else:
        watchlist_titles = []

    # Move the 'Only Show My Letterboxd Watchlist' toggle here
    only_watchlist = st.checkbox("Only show my Letterboxd watchlist", value=False)

col3, col4 = st.columns([1, 1])

with col3:
    only_cineville = st.checkbox("Only show Cineville theaters", value=True)

if selected_day != "All Days":
    movies_df = movies_df[movies_df["formatted_day"] == selected_day]

# Filter by the selected time
movies_df = movies_df[movies_df["show_datetime"].dt.strftime("%H:00") >= selected_time]

# Apply the filters for Cineville and watchlist
if only_cineville:
    movies_df = movies_df[movies_df["partnered_with_cineville"] == 1]
if only_watchlist:
    movies_df = movies_df[movies_df["in_watchlist"]]

grouped = movies_df.groupby(
    ["title", "year", "rating", "plot", "poster_url", "movie_id", "duration"]
)
sorted_movies = sorted(grouped, key=lambda x: x[0][2], reverse=True)

columns = st.columns(6)

for index, (movie, screenings) in enumerate(sorted_movies):
    title, year, rating, plot, poster_url, movie_id, duration = movie

    # Parse the duration (e.g., PT1H58M)
    match = re.match(r"PT(\d+H)?(\d+M)?", duration)
    hours = int(match.group(1).replace("H", "") if match.group(1) else 0)
    minutes = int(match.group(2).replace("M", "") if match.group(2) else 0)
    total_duration = timedelta(hours=hours, minutes=minutes)

    screenings_list = []
    for _, row in screenings.iterrows():
        start_time = row["show_datetime"]
        finish_time = round_to_quarter_hour(start_time + total_duration)

        # Format the screening time with the rounded finish time
        screenings_list.append(
            f"[{row['cinema']} - {start_time.strftime('%H:%M')}   (~ {finish_time.strftime('%H:%M')})]({row['ticket_url']})"
        )

    with columns[index % 6]:
        with st.container():
            # Load and cache the poster image using the movie_id
            poster_image = load_image(poster_url, movie_id)

            # Display the poster image if available
            if poster_image:
                st.image(poster_image, use_container_width=True)
            else:
                st.image(
                    "fallback_image.jpg", width=200
                )  # Show a fallback image if not available

            st.markdown(
                f"<h3 style='margin-bottom:0;'>{title} ({int(year)})</h3>",
                unsafe_allow_html=True,
            )
            if plot:
                st.write(f"{plot}")
            # Format the rating as (8.7/10)
            if rating:
                st.write(f"Rating: ({rating:.1f}/10)")
            with st.expander("Screenings"):
                for screening in screenings_list:
                    st.write(f"- {screening}")
            st.markdown("---")
