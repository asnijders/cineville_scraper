from sqlalchemy import Column, Integer, String, Float, Date, JSON
from .base import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(String, primary_key=True)  # Hash ID
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)  # Allow NULL
    movie_link = Column(String, unique=True, nullable=False)  # Filmladder movie URL
    imdb_link = Column(String, unique=True, nullable=True)  # IMDb URL
    imdb_year = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    genres = Column(JSON, nullable=True)  # List of genres
    content_rating = Column(String, nullable=True)
    duration = Column(String, nullable=True)  # ISO 8601 format (e.g., PT1H32M)
    director = Column(JSON, nullable=True)  # List of directors
    writers = Column(JSON, nullable=True)  # List of writers
    actors = Column(JSON, nullable=True)  # List of actors
    rating_count = Column(Integer, nullable=True)
    plot = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of keywords
    poster_url = Column(String, nullable=True)
    trailer_url = Column(String, nullable=True)

