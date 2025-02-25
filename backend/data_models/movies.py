from sqlalchemy import Column, Integer, String
from .base import Base


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(String, primary_key=True)  # Hash ID
    title = Column(String, nullable=False)
    year = Column(Integer)
    movie_link = Column(String, unique=True)  # Filmladder movie URL
    imdb_link = Column(String, unique=True)  # IMDb URL (to be populated)
