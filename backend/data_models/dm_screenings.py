from sqlalchemy import Column, String, TIMESTAMP, Integer
from backend.data_models.base import Base


class Screening(Base):
    __tablename__ = "screenings"

    # Foreign key to movies table
    fl_slug = Column(String, nullable=False)
    
    # New column for Cinema Name
    fl_cinema_name = Column(String, nullable=False)  # Added for storing cinema name

    # New column for Movie Title
    fl_title = Column(String, nullable=False)  # Added for storing the movie title

    # New column for Year (Optional, if you want to store the year)
    fl_year = Column(String, nullable=False)  # Added for storing the movie year

    # Cinema ID
    fl_cinema_id = Column(String, nullable=False)  # Cinema ID

    # Screening show datetime (with timezone)
    fl_show_datetime = Column(TIMESTAMP(timezone=True), nullable=False)  # Screening show datetime (with timezone)

    # Ticket URL
    fl_ticket_url = Column(String, nullable=True)  # URL for tickets

    # Movie Rating
    fl_rating = Column(String, nullable=True)  # Rating of the movie at the screening

    # Filmladder movie URL
    fl_url = Column(String, nullable=True)  # Filmladder movie URL

    # Poster URL for the movie at this screening
    fl_poster_url = Column(String, nullable=True)  # Poster URL for the movie at this screening

    # Redirect URL for the cinema or screening page
    redirect_url = Column(String, nullable=True)  # Redirect URL for the cinema or screening page

    # Primary key screening_id
    screening_id = Column(Integer, primary_key=True, nullable=False)  # Primary key