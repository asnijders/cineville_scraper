import tmdbsimple as tmdb
import pandas as pd
import numpy as np
import json
import time
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
api_key = os.getenv("API_KEY")
print(f"Loaded API Key: {api_key}")
tmdb.API_KEY = api_key


def collect_metadata(df):

    tmdb_ids = df['tmdb_id'].unique().tolist()
    dataframes = []
    for tmdb_id in tmdb_ids:
        dataframes.append(get_metadata(tmdb_id))
        time.sleep(0.03)

    results_df = pd.concat(dataframes, axis=0)
    df = df.merge(results_df, on="tmdb_id", how='left')

    print(len(df))

    return df


def get_metadata(tmdb_id):

    if not pd.isna(tmdb_id):
        movie = tmdb.Movies(tmdb_id)
        info = movie.info()
        reviews = movie.reviews()
        keywords = movie.keywords()
        credits = movie.credits()
        credits = {
                    'directors': [profile['name'] for profile in credits['crew'] if profile['job'] == 'Director'],
                    'cast': [profile['name'] for profile in credits['cast'][:5]]
                }

    else:
        print('blip')
        info, keywords, reviews, credits = np.nan, np.nan, np.nan, np.nan

    data = {
        'tmdb_info': info,
        'tmdb_keywords': keywords,
        'tmdb_reviews': reviews,
        'tmdb_credits': credits
    }

    # Convert values to JSON strings
    json_data = {key: json.dumps(value) for key, value in data.items()}

    # Create a DataFrame with a single row
    df = pd.DataFrame([json_data])
    df['tmdb_id'] = tmdb_id

    return df
