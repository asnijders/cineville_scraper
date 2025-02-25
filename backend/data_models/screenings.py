from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP
from .base import Base


class Screening(Base):
    __tablename__ = "screenings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(String, ForeignKey("movies.movie_id", ondelete="CASCADE"))
    cinema_id = Column(String, ForeignKey("cinemas.cinema_id", ondelete="CASCADE"))
    show_datetime = Column(TIMESTAMP, nullable=False)
    ticket_url = Column(String)
    rating = Column(String)  # Optional, some movies may not have a rating
    movie_link = Column(String)  # Filmladder movie URL
    poster_url = Column(String)  # Poster image URL
