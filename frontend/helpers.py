import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
import requests
from io import BytesIO
from PIL import Image
import logging
import time
from backend.data_pipelines.scrapers.letterboxd import LetterboxdScraper
import os
import streamlit as st


# Set up logging
logger = logging.getLogger(__name__)

# Media folder path
MEDIA_FOLDER = "media"

# Ensure media folder exists
if not os.path.exists(MEDIA_FOLDER):
    os.makedirs(MEDIA_FOLDER)


def load_image(image_url, movie_id):
    """Loads and caches an image from a URL. Checks if the image already exists locally before downloading."""
    image_path = os.path.join(MEDIA_FOLDER, f"{movie_id}_poster.jpg")

    # Check if the image already exists in the media folder
    if os.path.exists(image_path):
        # logger.info(f"Image already exists: {image_path}")
        return Image.open(image_path)

    try:
        # Start timing the download
        start_time = time.time()

        # Fetch the image data
        response = requests.get(image_url)
        if response.status_code == 200:
            # Open the image and save it locally
            image = Image.open(BytesIO(response.content))
            image = image.convert(
                "RGB"
            )  # Ensure the image is in RGB format for better quality

            # # Resize image to fit well in the container (ensure it's not too large)
            # max_size = (680, 924)  # Adjust as needed
            # image.thumbnail(max_size)

            # Save the image to the media folder
            image.save(image_path)
            end_time = time.time()

            elapsed_time = end_time - start_time
            logger.info(
                f"Image downloaded and saved as {image_path} in {elapsed_time:.2f} seconds."
            )

            return image
        else:
            logger.warning(
                f"Failed to load image from {image_url}. Status code: {response.status_code}"
            )
            return None
    except Exception as e:
        logger.error(f"Error loading image from {image_url}: {e}")
        return None


# Set up logging
logger = logging.getLogger(__name__)


def get_db_connection():
    return sqlite3.connect("backend/db.sqlite3")


@st.cache_resource(show_spinner=False)
def get_movies_with_screenings():
    """Fetches movies along with their screenings and cinema details."""
    conn = get_db_connection()
    query = """
        SELECT m.movie_id, m.title, m.year, m.rating, m.plot, m.duration,
               m.director, m.genres,
               c.name AS cinema, c.partnered_with_cineville, 
               s.show_datetime, s.ticket_url, m.poster_url
        FROM screenings s
        LEFT JOIN movies m ON s.movie_id = m.movie_id
        LEFT JOIN cinemas c ON s.cinema_id = c.cinema_id
        ORDER BY s.show_datetime
    """
    df = pd.read_sql(query, conn)
    conn.close()

    df["show_datetime"] = pd.to_datetime(df["show_datetime"])
    df["title"] = df["title"].str.title()
    df["cinema"] = df["cinema"].str.title()
    return df


def format_day(date):
    """Formats the date as Today, Tomorrow, or a weekday name."""
    today = datetime.now().date()
    delta_days = (date.date() - today).days

    if delta_days == 0:
        return "Today"
    elif delta_days == 1:
        return "Tomorrow"
    return date.strftime("%A (%b %d)") if delta_days >= 4 else date.strftime("%A")


@st.cache_data
def fuzzy_match_titles(movie_title, watchlist_titles, threshold=85):
    """Checks if a movie title is in the Letterboxd watchlist using fuzzy matching."""
    if pd.isna(movie_title):
        return False

    movie_title = str(movie_title).strip()
    for watchlist_title in watchlist_titles:
        if pd.isna(watchlist_title):
            continue
        watchlist_title = str(watchlist_title).strip()
        if fuzz.ratio(movie_title.lower(), watchlist_title.lower()) >= threshold:
            return True
    return False


def get_watchlist_titles(username):
    """Fetch and cache Letterboxd watchlist titles."""
    if not username:
        return []

    logger.info(f"Fetching Letterboxd watchlist for user: {username}")

    start_time = time.time()
    user_url = f"https://letterboxd.com/{username}/watchlist/"
    lb_scraper = LetterboxdScraper()
    watchlist_df = lb_scraper.run(user_url)
    end_time = time.time()

    elapsed_time = end_time - start_time
    logger.info(f"Fetched Letterboxd watchlist in {elapsed_time:.2f} seconds.")
    return watchlist_df["title"].tolist()


# Helper function to calculate the rounded finish time
def round_to_quarter_hour(time_obj):
    # Round the time to the nearest quarter hour
    minutes = (time_obj.minute // 15 + 1) * 15
    if minutes == 60:
        minutes = 0
        time_obj += timedelta(hours=1)
    return time_obj.replace(minute=minutes, second=0, microsecond=0)