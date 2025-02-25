from sqlalchemy import Column, String, Boolean
from .base import Base


class Cinema(Base):
    __tablename__ = "cinemas"

    cinema_id = Column(String, primary_key=True)  # Hash ID
    name = Column(String, nullable=False)
    location = Column(String)
    address = Column(String)
    website = Column(String)
    partnered_with_cineville = Column(Boolean, default=False)
