import logging
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from backend.data_models.dm_movies import Movie
from backend.data_models.dm_cinemas import Cinema
from backend.data_models.dm_screenings import Screening
from backend.data_models.dm_ratings import Rating
import backend.data_models.dm_cinemas  # Import Cinema model
import backend.data_models.dm_movies   # Import Movie model
import backend.data_models.dm_screenings  # Import Screening model
import backend.data_models.dm_ratings  # Import Ratings model
from backend.data_models.base import Base


engine = create_engine("postgresql://ardsnijders@localhost:5432/db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Creates all tables in the database (if not exists)."""

    print("Models imported and ready for table creation.")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")

    # List all tables in the database
    print(f"Created tables: {Base.metadata.tables.keys()}")


def drop_db():
    """Creates all tables in the database (if not exists)."""
    import backend.data_models.dm_cinemas as dm_cinemas, backend.data_models.dm_movies as dm_movies, backend.data_models.dm_screenings as dm_screenings, backend.data_models.dm_ratings as dm_ratings  # Import models to register them

    Base.metadata.drop_all(bind=engine)


def get_db_session():
    """Create and return a new database session."""
    return SessionLocal()


def save_cinemas(cinemas_df):
    """Insert or update cinemas efficiently."""
    session = get_db_session()
    try:
        existing_cinema_ids = {
            c.cinema_id for c in session.query(Cinema.cinema_id).all()
        }
        new_cinemas = []

        for _, row in cinemas_df.iterrows():
            if row["cinema_id"] in existing_cinema_ids:
                session.query(Cinema).filter_by(cinema_id=row["cinema_id"]).update(
                    row.to_dict()
                )
            else:
                new_cinemas.append(row.to_dict())

        if new_cinemas:
            session.bulk_insert_mappings(Cinema, new_cinemas)

        session.commit()
    finally:
        session.close()


def save_movies(movies_df):
    """Insert or update movies efficiently while avoiding UNIQUE constraint errors."""
    session = get_db_session()
    try:
        for _, row in movies_df.iterrows():
            existing_movie = session.query(Movie).filter_by(fl_slug=row["fl_slug"]).first()
            if existing_movie:
                # Update the existing movie
                for key, value in row.to_dict().items():
                    setattr(existing_movie, key, value)
            else:
                # Insert a new movie
                session.add(Movie(**row.to_dict()))

        session.commit()
    finally:
        session.close()


def get_existing_movies():
    """Fetch all existing movies from the database."""
    session = SessionLocal()
    try:
        existing_movies = session.query(Movie).all()
        if existing_movies == []:
            return None
        else:
            return pd.DataFrame([movie.__dict__ for movie in existing_movies]).drop(
                columns=["_sa_instance_state"]
        )
    finally:
        session.close()


def get_new_movies(scraped_movies):

    existing_movies = get_existing_movies()
    if existing_movies is None:
        print("No existing Movies table found")
        return scraped_movies

    existing_ids = existing_movies['fl_slug'].unique().tolist()

    return scraped_movies[~scraped_movies["fl_slug"].isin(existing_ids)]


def get_ratings():
    """Fetch all ratings from the database."""
    session = get_db_session()
    try:
        ratings = session.query(Rating).all()
        if ratings == []:
            return None
        else:
            return pd.DataFrame([rating.__dict__ for rating in ratings]).drop(
                columns=["_sa_instance_state"]
        )
    finally:
        session.close()


def save_screenings(screenings_df):
    """Overwrite screenings table with new data."""
    session = get_db_session()
    
    try:
        logging.info("Starting to delete all records from screenings table...")
        session.execute(text("DELETE FROM screenings;"))  # Faster delete
        logging.info("Records deleted successfully.")
        
        if screenings_df.empty:
            logging.warning("The DataFrame is empty. No records to insert.")
            return

        # Ensure correct data type for screening_id
        screenings_df['screening_id'] = screenings_df['screening_id'].astype(int)

        # Convert DataFrame rows into SQLAlchemy objects
        screenings = [
            Screening(
                fl_slug=row["fl_slug"],
                fl_cinema_name=row["fl_cinema_name"],
                fl_title=row["fl_title"],
                fl_year=row["fl_year"],
                fl_cinema_id=row["fl_cinema_id"],
                fl_show_datetime=row["fl_show_datetime"],
                fl_ticket_url=row["fl_ticket_url"],
                fl_rating=row["fl_rating"],
                fl_url=row["fl_url"],
                fl_poster_url=row["fl_poster_url"],
                redirect_url=row["redirect_url"],
                screening_id=row["screening_id"],
            )
            for _, row in screenings_df.iterrows()
        ]

        logging.info(f"Inserting {len(screenings)} records into screenings table...")

        # Use add_all instead of bulk_insert_mappings
        session.add_all(screenings)
        session.commit()
        logging.info("Data inserted and committed successfully.")
        
    except Exception as e:
        logging.error(f"Error saving data: {e}")
        session.rollback()  # Rollback the transaction on error
        
    finally:
        session.close()
        logging.info("Session closed.")

def save_all_to_db(cinemas_df, movies_df, screenings_df):
    """Save all data in a single transaction."""
    session = get_db_session()
    try:
        save_cinemas(cinemas_df)
        save_movies(movies_df)
        save_screenings(screenings_df)
        session.commit()  # ✅ Ensure all changes are committed together
    except Exception as e:
        session.rollback()  # Rollback everything if one step fails
        print("Error saving data:", e)
    finally:
        session.close()