import tmdbsimple as tmdb
import pandas as pd
import numpy as np
import json
import aioredis
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file
api_key = os.getenv("API_KEY")
tmdb.API_KEY = api_key


class TMDBMetadataCollector:
    def __init__(self, redis_url="redis://localhost:6379", cache_expiry=None):
        self.redis_url = redis_url
        self.cache_expiry = cache_expiry  # Can be None for no expiry
        self.redis = None

    async def setup_redis(self):
        """Initialize Redis connection."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def close_redis(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def get_metadata(self, tmdb_id):
        """Fetch movie metadata from TMDB API, using Redis cache if available."""
        if pd.isna(tmdb_id):
            return pd.DataFrame([{
                'tmdb_id': tmdb_id,
                'tmdb_info': np.nan,
                'tmdb_keywords': np.nan,
                'tmdb_reviews': np.nan,
                'tmdb_credits': np.nan
            }])

        cache_key = f"tmdb:{tmdb_id}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            print(f'cache hit for tmdb id {tmdb_id} - ({cache_key})')
            return pd.DataFrame([json.loads(cached_data)])  # Return cached data

        # Fetch data from TMDB API
        movie = tmdb.Movies(tmdb_id)
        info = movie.info()
        reviews = movie.reviews()
        keywords = movie.keywords()
        credits = movie.credits()
        credits = {
            'directors': [profile['name'] for profile in credits['crew'] if profile['job'] == 'Director'],
            'cast': [profile['name'] for profile in credits['cast'][:5]]
        }

        # Store in JSON format
        data = {
            'tmdb_id': tmdb_id,
            'tmdb_info': info,
            'tmdb_keywords': keywords,
            'tmdb_reviews': reviews,
            'tmdb_credits': credits
        }
        json_data = json.dumps(data)

        # Store in Redis with expiry (None means no expiration)
        await self.redis.set(cache_key, json_data, ex=self.cache_expiry)

        print(type(json_data))

        return pd.DataFrame([json_data])

    async def run(self, df):
        """Fetch metadata for all movies in a DataFrame asynchronously."""
        await self.setup_redis()

        tmdb_ids = df['tmdb_id'].dropna().unique().tolist()
        tasks = [self.get_metadata(tmdb_id) for tmdb_id in tmdb_ids]
        results = await asyncio.gather(*tasks)

        results_df = pd.concat(results, axis=0)
        df = df.merge(results_df, on="tmdb_id", how='left')

        await self.close_redis()
        return df
