from sqlalchemy import Column, Integer, String, Float, Date, JSON
from .base import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(String, primary_key=True)  # Hash ID
    title = Column(String, nullable=False)
    year = Column(Integer)
    movie_link = Column(String, unique=True)  # Filmladder movie URL
    imdb_link = Column(String, unique=True)  # IMDb URL
    imdb_year = Column(Integer)
    rating = Column(Float)
    genres = Column(JSON)  # List of genres
    content_rating = Column(String)
    duration = Column(String)  # ISO 8601 format (e.g., PT1H32M)
    director = Column(JSON)  # List of directors
    writers = Column(JSON)  # List of writers
    actors = Column(JSON)  # List of actors
    rating_count = Column(Integer)
    plot = Column(String)
    release_date = Column(Date)
    keywords = Column(JSON)  # List of keywords
    poster_url = Column(String)
    trailer_url = Column(String)
