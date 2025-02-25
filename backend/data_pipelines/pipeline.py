import logging
import pandas as pd
from scrapers.filmladder import FilmladderScraper
from utils.helpers import normalize_and_hash
# from db.database import save_movies, save_screenings, save_cinemas
# from external.imdb_api import fetch_imdb_metadata

logging.basicConfig(level=logging.INFO)


def assign_ids_screenings(df):
    """Assign `movie_id` and `cinema_id` for screenings DataFrame."""
    df["movie_id"] = df.apply(lambda row: normalize_and_hash(row["title"], row["year"]), axis=1)
    df["cinema_id"] = df.apply(lambda row: normalize_and_hash(row["cinema_name"], "Amsterdam"), axis=1)
    return df


def assign_ids_cinemas(df):
    """Assign `cinema_id` for cinemas DataFrame."""
    df["cinema_id"] = df.apply(lambda row: normalize_and_hash(row["name"], row["location"]), axis=1)
    return df


def extract_unique_movies(df):
    """Extract unique movies from screenings DataFrame."""
    movies_df = df[["movie_id", "title", "year"]].drop_duplicates().reset_index(drop=True)
    return movies_df


def fetch_metadata(movies_df):
    """Fetch IMDb metadata for a list of movies."""
    movies_df["metadata"] = movies_df.apply(lambda row: fetch_imdb_metadata(row["title"], row["year"]), axis=1)
    metadata_df = pd.json_normalize(movies_df["metadata"])  # Flatten nested IMDb data
    movies_df = pd.concat([movies_df.drop(columns=["metadata"]), metadata_df], axis=1)  
    return movies_df


def run_daily_pipeline():
    logging.info("Starting daily data pipeline...")

    # 1️⃣ Scrape Filmladder (returns two DataFrames)
    filmladder = FilmladderScraper()
    screenings_df, cinemas_df = filmladder.run()

    # 2️⃣ Assign IDs
    screenings_df = assign_ids_screenings(screenings_df)
    cinemas_df = assign_ids_cinemas(cinemas_df)

    # 3️⃣ Extract and fetch IMDb metadata for unique movies
    movies_df = extract_unique_movies(screenings_df)
    movies_df = fetch_metadata(movies_df)

    # 4️⃣ Store data in the database
    save_movies(movies_df)
    save_screenings(screenings_df)
    save_cinemas(cinemas_df)

    logging.info("Daily data pipeline completed.")


if __name__ == "__main__":
    run_daily_pipeline()