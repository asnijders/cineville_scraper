import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from rapidfuzz import process, fuzz
import requests
from PIL import Image
import logging
import time
from backend.data_pipelines.scrapers.letterboxd import LetterboxdScraper
from backend.data_pipelines.scrapers.letterboxdasync import LetterboxdScraperNew
import os
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Media folder path
MEDIA_FOLDER = "media"
os.makedirs(MEDIA_FOLDER, exist_ok=True)


# @st.cache_data(show_spinner=False)
def load_image(image_url, movie_id):
    image_path = os.path.join(MEDIA_FOLDER, f"{movie_id}_poster.jpg")
    if os.path.exists(image_path):
        return Image.open(image_path)
    try:
        response = requests.get(image_url, stream=True, timeout=5)
        if response.status_code == 200:
            image = Image.open(response.raw).convert("RGB")
            image.thumbnail((320, 435))
            image.save(image_path, "JPEG", quality=85)
            return image
    except Exception as e:
        logger.error(f"Error loading image from {image_url}: {e}")
    return None


def get_db_connection():
    return sqlite3.connect("backend/db.sqlite3", check_same_thread=False)


# @st.cache_data(show_spinner=False)
def get_filtered_movies(selected_day, selected_time, only_cineville, watchlist_titles):
    conn = get_db_connection()
    query = """
        SELECT DISTINCT(m.movie_id), m.title, m.year, m.rating, m.plot, m.duration,
               m.director, m.genres, c.name AS cinema, c.partnered_with_cineville, 
               s.show_datetime, s.ticket_url, m.poster_url
        FROM screenings s
        JOIN movies m ON s.movie_id = m.movie_id
        JOIN cinemas c ON s.cinema_id = c.cinema_id
        WHERE 1 = 1
    """
    params = []

    if selected_day != "All Days":
        target_date = datetime.now() + timedelta(
            days=(
                ["Today", "Tomorrow"].index(selected_day)
                if selected_day in ["Today", "Tomorrow"]
                else 0
            )
        )
        query += " AND DATE(s.show_datetime) = ?"
        params.append(target_date.strftime("%Y-%m-%d"))

    if selected_time:
        query += " AND TIME(s.show_datetime) >= ?"
        params.append(selected_time)

    if only_cineville:
        query += " AND c.partnered_with_cineville = 1"

    if watchlist_titles:
        watchlist_placeholders = ",".join("?" * len(watchlist_titles))
        query += f" AND m.title IN ({watchlist_placeholders})"
        params.extend(watchlist_titles)

    df = pd.read_sql(query, conn, params=params, parse_dates=["show_datetime"])
    conn.close()
    df["formatted_day"] = df["show_datetime"].dt.strftime("%A (%b %d)")
    df["title"] = df["title"].str.title()
    df["cinema"] = df["cinema"].str.title()
    return df


def format_day(date):
    today = datetime.now().date()
    delta_days = (date.date() - today).days
    return (
        "Today"
        if delta_days == 0
        else "Tomorrow" if delta_days == 1 else date.strftime("%A (%b %d)")
    )


def get_watchlist_titles(username):
    if not username:
        return []

    total_start_time = time.time()  # Track total function execution time

    # --- Step 1: Scrape Letterboxd Watchlist ---
    scrape_start_time = time.time()
    lb_scraper = LetterboxdScraperNew()
    watchlist_df = lb_scraper.run(f"https://letterboxd.com/{username}/watchlist/")
    watchlist_titles = watchlist_df.title.tolist()
    scrape_end_time = time.time()
    scrape_elapsed = scrape_end_time - scrape_start_time
    logger.info(f"Letterboxd scraping executed in {scrape_elapsed:.6f} seconds")

    # --- Step 2: Fetch Unique Movie Titles from Database ---
    conn = get_db_connection()
    query = "SELECT DISTINCT title, year FROM movies"
    db_titles_df = pd.read_sql(query, conn)
    conn.close()

    # Combine title and year for better matching
    db_titles = db_titles_df.title.tolist()

    if not db_titles:
        logger.warning("No movie titles found in the database.")
        return []

    # --- Step 3: Match Watchlist Titles to DB Titles ---
    match_start_time = time.time()
    matched_titles = []
    for watchlist_title in watchlist_titles:
        match, score, _ = process.extractOne(
            watchlist_title, db_titles, scorer=fuzz.token_sort_ratio
        )
        if score >= 95:  # Lower threshold for better flexibility
            logger.info(f"Strong match found for: {watchlist_title} -> {match} ({score})")
            matched_titles.append(match)

    match_end_time = time.time()
    match_elapsed = match_end_time - match_start_time
    logger.info(f"Title matching executed in {match_elapsed:.6f} seconds")

    # --- Total Execution Time ---
    total_end_time = time.time()
    total_elapsed = total_end_time - total_start_time
    logger.info(f"get_watchlist_titles executed in {total_elapsed:.6f} seconds")

    return matched_titles


def round_to_quarter_hour(time_obj):
    minutes = (time_obj.minute // 15 + 1) * 15
    return time_obj.replace(
        minute=0 if minutes == 60 else minutes, second=0, microsecond=0
    ) + timedelta(hours=1 if minutes == 60 else 0)
