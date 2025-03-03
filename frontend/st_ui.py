import streamlit as st
from datetime import datetime, timedelta
from helpers import (
    get_filtered_movies,
    load_image,
    get_watchlist_titles,
    round_to_quarter_hour,
    get_mood_based_titles
)
from backend.recommendation.vector_search import MovieEmbedder
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")
st.title("Amsterdam Screening Finder")

# Correct ordering of days
ordered_days = ["Today", "Tomorrow"] + [
    (datetime.now() + timedelta(days=i)).strftime("%A (%b %d)") for i in range(2, 7)
]
ordered_days.insert(0, "All Days")

col1, col2 = st.columns([2, 1])

with col1:
    selected_day = st.selectbox("Select a Day", ordered_days, index=1, key="day_select")

if "selected_time" not in st.session_state:
    st.session_state["selected_time"] = "10:00"

time_options = [f"{hour:02d}:00" for hour in range(10, 26)]
with col2:
    selected_time = st.selectbox(
        "Select Start Time",
        time_options,
        index=time_options.index("10:00"),
        key="time_select",
    )

with st.expander("Advanced Filters"):
    letterboxd_username = st.text_input("Enter your Letterboxd username")

    def get_watchlist(username):
        return get_watchlist_titles(username) if username else []

    watchlist_titles = get_watchlist(letterboxd_username)

    only_watchlist = st.checkbox("Only show my Letterboxd watchlist", value=False)

    # New feature: User query for recommendations
    user_query = st.text_input("Describe what kind of movie you’re in the mood for")
    recommend_movies = st.button("Find Recommendations")
    recommended_titles = []

    if user_query:
        
        # TODO: only compute embeddings for titles currently showing!
        recommended_titles = get_mood_based_titles(user_query)

        logger.info(recommended_titles)
    
    only_cineville = st.checkbox("Only show Cineville theaters", value=True)

col3, col4 = st.columns([1, 0.3])
# with col3:
#     only_cineville = st.checkbox("Only show Cineville theaters", value=True)

# Fetch filtered movies
movies_df = get_filtered_movies(
    selected_day,
    selected_time,
    only_cineville,
    watchlist_titles if only_watchlist else None,
    recommended_titles if recommended_titles else None,
)

with col3:
    st.write(f'Found {len(movies_df)} screenings for {len(movies_df.title.unique())} films')

# here for some reason not all the movies are retrieved
# so its not in the display logic but probably in the matching logic
# Found by algo:
# INFO:__main__:['bottoms', 'velvet goldmine', 'miséricorde', 'queer', 'wicked (ov)', 'polarized']
# found after querying db:
# titles:  ['Miséricorde' 'Queer' 'Wicked (Ov)' 'Polarized']
print('titles: ', movies_df.title.unique())

# Group and sort
if not movies_df.empty:
    grouped = movies_df.groupby(
        ["title", "year", "rating", "plot", "poster_url", "movie_id", "duration"]
    )
    sorted_movies = sorted(grouped, key=lambda x: x[0][2], reverse=True)
    columns = st.columns(6)

    for index, (movie, screenings) in enumerate(sorted_movies):
        title, year, rating, plot, poster_url, movie_id, duration = movie

        match = re.match(r"PT(\d+H)?(\d+M)?", duration)
        hours = int(match.group(1).replace("H", "") if match.group(1) else 0)
        minutes = int(match.group(2).replace("M", "") if match.group(2) else 0)
        total_duration = timedelta(hours=hours, minutes=minutes)

        screenings_by_day = {}
        for _, row in screenings.iterrows():
            show_date = row["show_datetime"].date()
            if show_date == datetime.now().date():
                day_label = "Today"
            elif show_date == (datetime.now() + timedelta(days=1)).date():
                day_label = "Tomorrow"
            else:
                day_label = row["show_datetime"].strftime("%A (%b %d)")

            screening_info = f"[{row['cinema']} - {row['show_datetime'].strftime('%H:%M')} (~ {round_to_quarter_hour(row['show_datetime'] + total_duration).strftime('%H:%M')})]({row['ticket_url']})"

            if day_label not in screenings_by_day:
                screenings_by_day[day_label] = []
            screenings_by_day[day_label].append(screening_info)

        sorted_screenings_by_day = {
            day: screenings_by_day[day]
            for day in ordered_days[1:]
            if day in screenings_by_day
        }

        with columns[index % 6]:
            with st.container():
                poster_image = load_image(poster_url, movie_id)
                if poster_image:
                    st.image(poster_image, use_container_width=True)

                st.markdown(
                    f"<h3 style='margin-bottom:0;'>{title} ({int(year)})</h3>",
                    unsafe_allow_html=True,
                )

                if plot:
                    st.write(plot)
                if rating:
                    st.write(f"Rating: ({rating:.1f}/10)")
                if title.lower() in watchlist_titles:
                    st.write("_On your Letterboxd watchlist_.")
                if title in recommended_titles:
                    st.write("_Recommended based on your query_.")

                with st.expander("Screenings"):
                    for day, screenings_list in sorted_screenings_by_day.items():
                        st.markdown(f"{day}")
                        for screening in screenings_list:
                            st.write(f"- {screening}")

                st.markdown("---")
