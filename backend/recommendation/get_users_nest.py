import aiohttp
import asyncio
import nest_asyncio
import sys
import time
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
nest_asyncio.apply()


async def fetch_with_semaphore(session, url, semaphore, index, total):
    async with semaphore:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    status = "success"
                else:
                    content = None
                    status = "failed"
        except Exception as e:
            content = None
            status = str(e)
        return {"url": url, "content": content, "status": status}


async def scrape_urls(urls, max_concurrent=15):
    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_with_semaphore(session, url, semaphore, i, len(urls))
            for i, url in enumerate(urls)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    print()  # Move to the next line after progress completes
    return results


def get_users(num_pages=5):

    start = time.time()
    urls = [
        f"https://letterboxd.com/members/popular/this/year/page/{page+1}/"
        for page in range(num_pages)
    ]
    results = asyncio.run(scrape_urls(urls))
    end = time.time()
    print(f'Scraping of {len(urls)} urls finished in {end-start} seconds')
    return results
