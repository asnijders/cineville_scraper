import logging
import pandas as pd
from datetime import datetime
from rapidfuzz import process
import hashlib
import re

# from db.database import save_movies, save_screenings, save_cinemas

logging.basicConfig(level=logging.INFO)


def normalize_and_hash(title: str, year: str = None) -> str:
    """
    Normalize a movie title and year, then generate a stable hash.

    Args:
        title (str): The movie title.
        year (str, optional): The movie release year. Defaults to None.

    Returns:
        str: A unique hash-based movie ID.
    """
    if not title:
        raise ValueError("Title cannot be empty")

    # Convert to lowercase
    title = title.lower().strip()

    # Remove special characters, keeping only letters, numbers, and spaces
    title = re.sub(r"[^a-z0-9\s]", "", title)

    # Normalize whitespace
    title = re.sub(r"\s+", " ", title).strip()

    # Combine title and year (if available)
    identifier = f"{title} {year}" if year else title

    # Generate a SHA256 hash and return first 10 characters for uniqueness
    return hashlib.sha256(identifier.encode()).hexdigest()[:10]


def process_screenings(df):

    def deduplicate_movie_titles(screenings_df, title_column="fl_title", threshold=90):
        """_summary_

        This function identifies and filters out highly similar film titles from screenings
        such as The Brutalist, The Brutalist (IMAX), etcetera

        Args:
            screenings_df (_type_): DataFrame
            title_column (str, optional): _description_. Defaults to "title".
            threshold (int, optional): _description_. Defaults to 90.

        Returns:
            _type_: DataFrame
        """
        unique_titles = screenings_df[title_column].unique()
        grouped_titles = {}

        for title in unique_titles:
            matches = process.extract(title, unique_titles, limit=None)
            similar_titles = [match[0] for match in matches if match[1] >= threshold]

            if not similar_titles:
                print(f"Title '{title}' did not meet the threshold and was discarded.")
                continue

            # Find the shortest title among similar ones
            shortest_title = min(similar_titles, key=len)

            for t in similar_titles:
                grouped_titles[t] = shortest_title

        # Replace titles in the dataframe
        df = screenings_df.copy()
        df[title_column] = df[title_column].map(grouped_titles)
        return df

    def assign_ids_screenings(df):
        """Assign `movie_id` and `cinema_id` for screenings DataFrame."""

        df["fl_cinema_id"] = df.apply(
            lambda row: normalize_and_hash(row["fl_cinema_name"], "Amsterdam"), axis=1
        )
        return df

    df["fl_show_datetime"] = df["fl_show_datetime"].apply(
        lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x
    )

    df['screening_id'] = df['fl_ticket_url'].apply(lambda x: x.split('/')[-1]).astype(int)
    df = deduplicate_movie_titles(df)
    df = assign_ids_screenings(df)

    return df


def assign_ids_watchlist(df):
    """Assign `movie_id` and `cinema_id` for screenings DataFrame."""
    df["movie_id"] = df.apply(
        lambda row: normalize_and_hash(row["title"], row["year"]), axis=1
    )
    return df


def process_cinemas(df):

    def add_cineville_tag(df):
        """Assign 'cineville' tag for cinemas DataFrame."""
        import os

        cineville_tags = pd.read_csv(
            "data_pipelines/external_data/cinema_data/cineville_cinemas.csv"
        )

        # Merge with the existing DataFrame based on theater name
        df = df.merge(cineville_tags, on="name", how="left")

        # Fill NaN values in 'partnered_with_cineville' with 'no' for cinemas not in the CSV
        df["partnered_with_cineville"] = df["partnered_with_cineville"].fillna("no")

        return df

    def assign_ids_cinemas(df):
        """Assign `cinema_id` for cinemas DataFrame."""
        df["cinema_id"] = df.apply(
            lambda row: normalize_and_hash(row["name"], row["location"]), axis=1
        )
        return df

    df = assign_ids_cinemas(df)
    df = add_cineville_tag(df)
    return df


def process_enriched_movies(df):
    df = df.copy()
    df["release_date"] = pd.to_datetime(df["release_date"]).dt.date

    # Assign imdb_year only if 'year' column is empty or None
    df["year"] = df["year"].where(df["year"].notna(), df["imdb_year"])

    df = df.where(pd.notna(df), None)

    return df



def extract_unique_movies(df):
    """Extract unique movies from screenings DataFrame."""
    movies_df = (
        df[["fl_title", "fl_year", "fl_url", "fl_slug"]]
        .drop_duplicates('fl_url')
        .reset_index(drop=True)
    )

    movies_df['fl_year'] = movies_df['fl_year'].apply(lambda x: 0 if pd.isna(x) else x)

    return movies_df


if __name__ == "__main__":
    pass
