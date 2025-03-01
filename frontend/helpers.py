import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz, process
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
os.makedirs(MEDIA_FOLDER, exist_ok=True)  # Ensure media folder exists efficiently


def load_image(image_url, movie_id):
    """Loads and caches an image from a URL efficiently."""
    image_path = os.path.join(MEDIA_FOLDER, f"{movie_id}_poster.jpg")

    if os.path.exists(image_path):
        return Image.open(image_path)

    try:
        start_time = time.time()
        response = requests.get(
            image_url, stream=True, timeout=5
        )  # Stream download, set timeout
        if response.status_code == 200:
            image = Image.open(response.raw).convert(
                "RGB"
            )  # Avoid unnecessary BytesIO wrapping
            image.thumbnail((320, 435))  # Resize before saving
            image.save(image_path, "JPEG", quality=85)  # Optimize file size
            logger.info(f"Image saved: {image_path} in {time.time() - start_time:.2f}s")
            return image
    except Exception as e:
        logger.error(f"Error loading image from {image_url}: {e}")
    return None


def get_db_connection():
    """Creates a persistent database connection."""
    return sqlite3.connect("backend/db.sqlite3", check_same_thread=False)


@st.cache_resource(show_spinner=False)
def get_movies_with_screenings():
    """Fetches movies with screenings efficiently."""
    conn = get_db_connection()
    query = """
        SELECT m.movie_id, m.title, m.year, m.rating, m.plot, m.duration,
               m.director, m.genres, c.name AS cinema, c.partnered_with_cineville, 
               s.show_datetime, s.ticket_url, m.poster_url
        FROM screenings s
        JOIN movies m ON s.movie_id = m.movie_id  -- INNER JOIN speeds up query
        JOIN cinemas c ON s.cinema_id = c.cinema_id
        ORDER BY s.show_datetime
    """
    df = pd.read_sql(query, conn, parse_dates=["show_datetime"])
    conn.close()

    df["formatted_day"] = df["show_datetime"].dt.strftime("%A (%b %d)")
    df["title"] = df["title"].str.title()
    df["cinema"] = df["cinema"].str.title()
    return df


def format_day(date):
    """Formats the date as Today, Tomorrow, or a weekday name."""
    today = datetime.now().date()
    delta_days = (date.date() - today).days
    return (
        "Today"
        if delta_days == 0
        else "Tomorrow" if delta_days == 1 else date.strftime("%A (%b %d)")
    )


@st.cache_data
def fuzzy_match_titles(movie_title, watchlist_titles, threshold=85):
    """Efficient fuzzy matching using process.extractOne."""
    if pd.isna(movie_title) or not watchlist_titles:
        return False
    match, score = process.extractOne(
        movie_title.strip(), watchlist_titles, scorer=fuzz.partial_ratio
    )
    return score >= threshold


def get_watchlist_titles(username):
    """Fetches Letterboxd watchlist efficiently."""
    if not username:
        return []

    logger.info(f"Fetching Letterboxd watchlist for: {username}")
    start_time = time.time()
    lb_scraper = LetterboxdScraper()
    watchlist_df = lb_scraper.run(f"https://letterboxd.com/{username}/watchlist/")
    elapsed_time = time.time() - start_time
    logger.info(f"Fetched Letterboxd watchlist in {elapsed_time:.2f}s")
    return watchlist_df["title"].tolist() if "title" in watchlist_df else []


def round_to_quarter_hour(time_obj):
    """Rounds time to the nearest quarter-hour efficiently."""
    minutes = (time_obj.minute // 15 + 1) * 15
    return time_obj.replace(
        minute=0 if minutes == 60 else minutes, second=0, microsecond=0
    ) + timedelta(hours=1 if minutes == 60 else 0)
