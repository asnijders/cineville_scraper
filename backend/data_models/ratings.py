from sqlalchemy import Column, String, PrimaryKeyConstraint
from .base import Base


class Rating(Base):
    __tablename__ = "ratings"

    member_id = Column(String, nullable=False)  # Letterboxd user ID
    film_id = Column(String, nullable=False)  # Letterboxd film ID
    slug = Column(String, nullable=False)  # Film slug
    rating = Column(String)  # Rating (1-10 or None)
    alt_title = Column(String)  # Alternative title of the film

    __table_args__ = (PrimaryKeyConstraint("member_id", "film_id"),)
