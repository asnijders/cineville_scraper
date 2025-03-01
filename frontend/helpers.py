import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz, process
import requests
from io import BytesIO
from PIL import Image
import logging
import time
import logging
from backend.data_pipelines.scrapers.letterboxd import LetterboxdScraper
import os
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Media folder path
MEDIA_FOLDER = "media"
os.makedirs(MEDIA_FOLDER, exist_ok=True)


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


def get_filtered_movies(selected_day, selected_time, only_cineville, watchlist_titles):
    conn = get_db_connection()
    query = """
        SELECT m.movie_id, m.title, m.year, m.rating, m.plot, m.duration,
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


def fuzzy_match_titles(movie_title, watchlist_titles, threshold=85):
    if pd.isna(movie_title) or not watchlist_titles:
        return False
    
    start_time = time.time()  # Start timing
    
    match, score = process.extractOne(
        movie_title.strip(), watchlist_titles, scorer=fuzz.partial_ratio
    )
    
    end_time = time.time()  # End timing
    elapsed_time = end_time - start_time
    logger.info(f"fuzzy_match_titles executed in {elapsed_time:.6f} seconds")
    
    return score >= threshold


def get_watchlist_titles(username):
    if not username:
        return []
    
    start_time = time.time()  # Start timing
    
    lb_scraper = LetterboxdScraper()
    watchlist_df = lb_scraper.run(f"https://letterboxd.com/{username}/watchlist/")
    
    end_time = time.time()  # End timing
    elapsed_time = end_time - start_time
    logger.info(f"get_watchlist_titles executed in {elapsed_time:.6f} seconds")
    
    return watchlist_df["title"].tolist() if "title" in watchlist_df else []


def round_to_quarter_hour(time_obj):
    minutes = (time_obj.minute // 15 + 1) * 15
    return time_obj.replace(
        minute=0 if minutes == 60 else minutes, second=0, microsecond=0
    ) + timedelta(hours=1 if minutes == 60 else 0)
