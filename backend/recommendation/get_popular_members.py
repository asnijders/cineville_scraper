import aiohttp
import asyncio
import pandas as pd
import time
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch(session, url, semaphore):
    """Fetch content asynchronously for a given URL"""
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


async def scrape(urls, max_concurrent=15):
    """Fetch all pages asynchronously"""
    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return results


def parse_members(pages):

    """Parsing using BeautifulSoup to extract member names"""
    all_member_ids = []
    for page in pages:
        if page["content"]:
            html = page["content"]
            soup = BeautifulSoup(html, "html.parser")
            # Find the first <a> tag in each <td class="table-person"> and get the href attribute
            member_ids = [
                a["href"]
                for a in soup.find_all("td", class_="table-person")
                for a in a.find_all("a", href=True)[:1]
            ]
            all_member_ids.extend(member_ids)  # Collect all hrefs
        else:
            print(f"Failed to fetch or parse URL: {page['url']}")

    all_member_ids = [member_id.strip('/') for member_id in all_member_ids]
    return all_member_ids


def write_results(member_ids):

    member_ids = pd.Series(member_ids)
    member_ids.name = 'member_id'
    filepath = 'backend/recommendation/data/member_ids.csv'
    member_ids.to_csv(filepath)
    return None


def get_members():

    num_pages = 256  # Modify the number of pages here
    start = time.time()

    # Create URLs for each page
    urls = [
        f"https://letterboxd.com/members/popular/this/year/page/{page+1}/"
        for page in range(num_pages)
    ]

    # Fetch content asynchronously
    results = asyncio.run(scrape(urls))

    # Parse each page sequentially
    member_ids = parse_members(results)

    # save ids to .csv
    write_results(member_ids)

    end = time.time()
    print(f"Scraping and parsing of {len(urls)} urls finished in {end-start} seconds")



if __name__ == "__main__":
    get_members()
