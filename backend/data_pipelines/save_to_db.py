from data_models.base import SessionLocal
from data_models.movies import Movie
from data_models.cinemas import Cinema
from data_models.screenings import Screening
from sqlalchemy import text
import pandas as pd


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
            existing_movie = session.query(Movie).filter_by(imdb_link=row["imdb_link"]).first()
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


def save_screenings(screenings_df):
    """Overwrite screenings table with new data."""
    session = get_db_session()
    try:
        session.execute(text("DELETE FROM screenings;"))  # Faster delete
        session.bulk_insert_mappings(Screening, screenings_df.to_dict(orient="records"))
        session.commit()
    finally:
        session.close()


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
