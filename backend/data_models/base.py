from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from data_models.config import DATABASE_URL  # Store DB URI in a config file

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Creates all tables in the database (if not exists)."""
    from . import cinemas, movies, screenings  # Import models to register them

    Base.metadata.create_all(bind=engine)
