import aiohttp
import asyncio
import random


class Scraper:

    def __init__(self):
        self.USER_AGENTS = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Safari/537.36",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.123 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.98 Safari/537.36",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36"
                    ]

    async def fetch_data(self, session, url, semaphore):
        headers = {"User-Agent": random.choice(self.USER_AGENTS)}
        """Fetch raw HTML content asynchronously."""
        async with semaphore:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
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
