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
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")
st.title("Amsterdam Screening Finder")

@st.cache_resource(show_spinner=False)
def load_movies():
    df = get_movies_with_screenings()
    df["formatted_day"] = df["show_datetime"].apply(format_day)
    return df


movies_df = load_movies()

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

with col1:
    selected_day = st.selectbox("Select a Day", ordered_days, index=1, key="day_select")

# Default time selection and persistence
if "selected_time" not in st.session_state:
    st.session_state["selected_time"] = "10:00"

# Time selection
time_options = [f"{hour:02d}:00" for hour in range(10, 26)]
with col2:
    selected_time = st.selectbox("Select Start Time", time_options, index=time_options.index("10:00"), key="time_select")

with st.expander("Advanced Filters"):
    letterboxd_username = st.text_input("Enter your Letterboxd username")
    
    @st.cache_data(show_spinner=False)
    def get_watchlist(username):
        return get_watchlist_titles(username) if username else []
    
    watchlist_titles = get_watchlist(letterboxd_username)
    only_watchlist = st.checkbox("Only show my Letterboxd watchlist", value=False)

col3, col4 = st.columns([1, 1])
with col3:
    only_cineville = st.checkbox("Only show Cineville theaters", value=True)

# Apply filters
if selected_day != "All Days":
    movies_df = movies_df[movies_df["formatted_day"] == selected_day]

movies_df = movies_df[movies_df["show_datetime"].dt.strftime("%H:00") >= selected_time]

if only_cineville:
    movies_df = movies_df[movies_df["partnered_with_cineville"] == 1]

if only_watchlist and watchlist_titles:
    movies_df["in_watchlist"] = movies_df["title"].apply(lambda title: fuzzy_match_titles(title, watchlist_titles))
    movies_df = movies_df[movies_df["in_watchlist"]]

# Group and sort
grouped = movies_df.groupby(["title", "year", "rating", "plot", "poster_url", "movie_id", "duration"])
sorted_movies = sorted(grouped, key=lambda x: x[0][2], reverse=True)

columns = st.columns(6)

for index, (movie, screenings) in enumerate(sorted_movies):
    title, year, rating, plot, poster_url, movie_id, duration = movie
    
    match = re.match(r"PT(\d+H)?(\d+M)?", duration)
    hours = int(match.group(1).replace("H", "") if match.group(1) else 0)
    minutes = int(match.group(2).replace("M", "") if match.group(2) else 0)
    total_duration = timedelta(hours=hours, minutes=minutes)
    
    screenings_list = [
        f"[{row['cinema']} - {row['show_datetime'].strftime('%H:%M')} (~ {round_to_quarter_hour(row['show_datetime'] + total_duration).strftime('%H:%M')})]({row['ticket_url']})"
        for _, row in screenings.iterrows()
    ]
    
    with columns[index % 6]:
        with st.container():
            poster_image = load_image(poster_url, movie_id)
            if poster_image:
                st.image(poster_image, use_container_width=True)
            
            st.markdown(f"<h3 style='margin-bottom:0;'>{title} ({int(year)})</h3>", unsafe_allow_html=True)
            if plot:
                st.write(plot)
            if rating:
                st.write(f"Rating: ({rating:.1f}/10)")
            
            with st.expander("Screenings"):
                for screening in screenings_list:
                    st.write(f"- {screening}")
            
            st.markdown("---")
