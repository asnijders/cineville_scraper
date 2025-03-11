import aiohttp
import asyncio
import pandas as pd
import time
from bs4 import BeautifulSoup
import logging
import re
from tqdm import tqdm

from sqlalchemy.orm import Session
from backend.data_models.ratings import Rating
from backend.data_models.save_to_db import get_db_session


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_html(session, url, semaphore):
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


async def fetch_all_pages(member_id, max_concurrent=60):

    # Create URLs for each page
    base_url = f"https://letterboxd.com/{member_id}/films/"

    """Fetch all pages asynchronously"""
    semaphore = asyncio.Semaphore(max_concurrent)
    connector = aiohttp.TCPConnector(limit=max_concurrent)

    async with aiohttp.ClientSession(connector=connector) as session:

        # First, get the first page to determine pagination
        first_page_html = await fetch_html(session, base_url, semaphore)
        # print(first_page_html["status"])

        if first_page_html["content"] is None:
            print('Warning: no response found')
            return []
        soup = BeautifulSoup(first_page_html["content"], "html.parser")

        # Extract total number of pages
        pagination = soup.select_one("div.pagination")
        if pagination:
            last_page = max(
                [int(a.text) for a in pagination.select("a") if a.text.isdigit()],
                default=1,
            )
        else:
            last_page = 1

        # Generate all URLs
        page_urls = [f"{base_url}page/{i}/" for i in range(1, last_page + 1)]
        tasks = [fetch_html(session, url, semaphore) for url in page_urls]
        pages_html = await asyncio.gather(*tasks, return_exceptions=True)

    return pages_html


def parse_ratings(pages, member_id):
    ratings_data = []

    for page in pages:
        if page["content"]:

            # Parse the HTML page with BeautifulSoup
            html = page["content"]
            soup = BeautifulSoup(html, "html.parser")

            # Find all the poster containers
            poster_containers = soup.find_all("li", class_="poster-container")

            for container in poster_containers:
                film_id = container.find("div", class_="really-lazy-load")[
                    "data-film-id"
                ]

                # Extract film slug
                slug = container.find("div", class_="really-lazy-load")[
                    "data-film-slug"
                ]

                rating_span = container.find(
                    "span",
                    class_=lambda class_name: class_name and "rated-" in class_name,
                )
                if rating_span:
                    rating = re.findall(r"\d+", str(rating_span))[0]
                else:
                    rating = None

                # Extract alt title from the img tag
                alt_title = container.find("img")["alt"]

                # Store the extracted data as a dictionary
                data = {
                    "member_id": str(member_id),
                    "film_id": str(film_id),
                    "slug": slug,
                    "rating": str(rating),
                    "alt_title": alt_title,
                }

                ratings_data.append(data)

    return ratings_data


def save_ratings_to_db(session: Session, ratings: list):
    """
    Insert or update a list of parsed ratings to the database.

    :param session: SQLAlchemy Session object
    :param ratings: List of dictionaries with rating data
    """

    try:
        for rating in ratings:

            obj = Rating(
                member_id=rating["member_id"],
                film_id=rating["film_id"],
                slug=rating["slug"],
                rating=rating["rating"],
                alt_title=rating["alt_title"]
            )
            session.merge(obj)  # Merge will update if exists, insert if not

        session.commit()
        # print(f"✅ Successfully inserted/updated {len(ratings)} ratings.")

    except Exception as e:
        session.rollback()
        print(f"❌ Error inserting/updating ratings: {e}")


def get_ratings(member_id, db_session):

    start = time.time()

    # Fetch content asynchronously
    pages = asyncio.run(fetch_all_pages(member_id))

    # Parse each page sequentially
    ratings = parse_ratings(member_id=member_id,
                            pages=pages)

    # print(f'{len(ratings)} ratings found for {member_id}')

    save_ratings_to_db(session=db_session,
                       ratings=ratings)

    end = time.time()

    return ratings, len(pages)


def main():

    db_session = get_db_session()
    ratings = {}
    member_ids = pd.read_csv("recommendation/data/new_members_for_parsing.csv").member_id.tolist()[18962:]

    total_members = 0  # Track total members processed
    total_pages = 0    # Track total pages processed
    start_time = time.time()  # Start time for elapsed time calculation

    with tqdm(desc="Processing Members") as pbar:
        for member_id in member_ids:
            ratings[member_id], num_pages = get_ratings(member_id, db_session)

            # Update total counts
            total_members += 1
            total_pages += num_pages

            # Compute elapsed time
            elapsed_time = time.time() - start_time
            members_per_second = total_members / elapsed_time if elapsed_time > 0 else 0
            pages_per_second = total_pages / elapsed_time if elapsed_time > 0 else 0

            # Update tqdm display
            tqdm.write(f'Fetched and parsed {num_pages} pages for member {member_id}')
            pbar.set_postfix(members_per_sec=members_per_second, 
                             pages_per_sec=pages_per_second)
            pbar.update(1)

    return ratings


if __name__ == "__main__":
    main()
