from sqlalchemy import Column, String, Integer, JSON
from backend.data_models.base import Base


class Movie(Base):
    __tablename__ = "movies"

    fl_slug = Column(String, primary_key=True)  # Filmladder slug as primary key
    fl_title = Column(String, nullable=False)  # Movie title
    fl_year = Column(Integer, nullable=True)  # Year of release
    fl_url = Column(String, unique=True, nullable=False)  # Filmladder movie URL
    imdb_url = Column(String, unique=True, nullable=True)  # IMDb URL
    imdb_id = Column(String, unique=True, nullable=True)  # IMDb ID
    lb_url = Column(String, unique=True, nullable=True)  # Letterboxd URL
    lb_film_id = Column(String, unique=True, nullable=True)  # Letterboxd film ID
    lb_film_slug = Column(String, unique=True, nullable=True)  # Letterboxd slug
    lb_poster_url = Column(String, nullable=True)  # Letterboxd poster URL
    tmdb_id = Column(String, unique=True, nullable=True)  # TMDb ID
    tmdb_info = Column(JSON, nullable=True)  # TMDb movie details
    tmdb_keywords = Column(JSON, nullable=True)  # TMDb keywords list
    tmdb_reviews = Column(JSON, nullable=True)  # TMDb reviews
    tmdb_credits = Column(JSON, nullable=True)  # TMDb cast and crew info
    text_to_embed = Column(String, nullable=True)  # Text representation for embeddings
    embedding = Column(JSON, nullable=True)  # Embedding vector
