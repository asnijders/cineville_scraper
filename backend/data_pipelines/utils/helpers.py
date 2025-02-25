import hashlib
import re
import pandas as pd


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


def add_imdb_ids(df):

    path = 'backend/data_pipelines/external_data/imdb_data/title.basics.tsv.gz'
    imdb_data = pd.read_csv(path, sep='\t')

    df['idmb_id'] = imbd_data
