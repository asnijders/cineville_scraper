import aiohttp
import asyncio
import random
import aioredis
import hashlib


class Scraper:

    def __init__(self, redis_url="redis://localhost:6379", cache_expiry=86400):

        self.redis_url = redis_url
        self.cache_expiry = cache_expiry  # Cache expiration in seconds
        self.redis = None  # Redis connection will be created in async setup
        self.USER_AGENTS = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.123 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.98 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36"
                    ]

    async def setup_redis(self):
        """Initialize Redis connection (should be called once before scraping)."""
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

    async def close_redis(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    async def fetch_data(self, session, url, semaphore):
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}
        cache_key = f"scraper:{hashlib.md5(url.encode()).hexdigest()}"  # Hash URL 
        """Fetch raw HTML content asynchronously."""
        async with semaphore:
            try:
                # Check Redis cache first
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    print(f"Cache hit for {url} - ({cache_key})")
                    return cached_data

                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()

                        # Store response in Redis
                        await self.redis.setex(cache_key,
                                               self.cache_expiry,
                                               html)
                        return html

                    return None
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return None

    async def scrape_all(self, urls, max_concurrent=5):
        """Fetch all pages asynchronously."""
        semaphore = asyncio.Semaphore(max_concurrent)
        connector = aiohttp.TCPConnector(limit=max_concurrent)

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_data(session, url, semaphore) for url in urls]
            return await asyncio.gather(*tasks)
