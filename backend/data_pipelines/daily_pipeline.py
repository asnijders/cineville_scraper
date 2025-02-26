import logging
import pandas as pd
from datetime import datetime
from data_pipelines.scrapers.filmladder import FilmladderScraper
from data_pipelines.utils.helpers import normalize_and_hash
from data_pipelines.save_to_db import get_existing_movies

# from db.database import save_movies, save_screenings, save_cinemas

logging.basicConfig(level=logging.INFO)


def get_new_movies(scraped_movies):
    existing_movies = get_existing_movies()
    if existing_movies is None:
        print('No existing Movies table found')
        return scraped_movies
    else:
        return scraped_movies[~scraped_movies['movie_id'].isin(existing_movies['movie_id'])]


def assign_ids_screenings(df):
    """Assign `movie_id` and `cinema_id` for screenings DataFrame."""
    df["movie_id"] = df.apply(
        lambda row: normalize_and_hash(row["title"], row["year"]), axis=1
    )
    df["cinema_id"] = df.apply(
        lambda row: normalize_and_hash(row["cinema_name"], "Amsterdam"), axis=1
    )
    return df


def clean_screenings(df):
    df["show_datetime"] = df["show_datetime"].apply(
        lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x
    )
    return df


def assign_ids_watchlist(df):
    """Assign `movie_id` and `cinema_id` for screenings DataFrame."""
    df["movie_id"] = df.apply(
        lambda row: normalize_and_hash(row["title"], row["year"]), axis=1
    )
    return df


def add_cineville_tag(df):
    """Assign 'cineville' tag for cinemas DataFrame."""
    import os

    print(os.getcwd())
    cineville_tags = pd.read_csv(
        "data_pipelines/external_data/cinema_data/cineville_cinemas.csv"
    )

    # Merge with the existing DataFrame based on theater name
    df = df.merge(cineville_tags, on="name", how="left")

    # Fill NaN values in 'partnered_with_cineville' with 'no' for cinemas not in the CSV
    df["partnered_with_cineville"] = df["partnered_with_cineville"].fillna("no")

    return df


def add_imdb_links(df):
    """ "Assign imdb links for movies dataframe"""
    from scrapers.imdb import IMDBScraper

    scraper = IMDBScraper(headless=True)
    df = scraper.run(df)
    return df


def assign_ids_cinemas(df):
    """Assign `cinema_id` for cinemas DataFrame."""
    df["cinema_id"] = df.apply(
        lambda row: normalize_and_hash(row["name"], row["location"]), axis=1
    )
    return df


def extract_unique_movies(df):
    """Extract unique movies from screenings DataFrame."""
    movies_df = (
        df[["movie_id", "title", "year", "movie_link"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    return movies_df


def fetch_metadata(movies_df):
    """Fetch IMDb metadata for a list of movies."""
    movies_df["metadata"] = movies_df.apply(
        lambda row: fetch_imdb_metadata(row["title"], row["year"]), axis=1
    )
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
    screenings_df = clean_screenings(screenings_df)
    cinemas_df = add_cineville_tag(assign_ids_cinemas(cinemas_df))

    # 3️⃣ Extract and fetch IMDb metadata for unique movies
    # TODO: first reference movies_df with existing movies sqlite backend.
    # only fetch IMDB links for new titles.
    # movies_df = extract_unique_movies(screenings_df)

    return screenings_df, cinemas_df

    # movies_df = fetch_metadata(movies_df)

    # # 4️⃣ Store data in the database
    # save_movies(movies_df)
    # save_screenings(screenings_df)
    # save_cinemas(cinemas_df)

    logging.info("Daily data pipeline completed.")


if __name__ == "__main__":
    run_daily_pipeline()
