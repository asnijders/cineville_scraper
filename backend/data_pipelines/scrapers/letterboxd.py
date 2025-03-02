import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
import re


class LetterboxdScraper:
    """Scraper for Letterboxd watchlist using asynchronous fetching."""

    async def fetch_html(self, session, url):
        """Asynchronously fetch the HTML of a given URL."""
        async with session.get(url) as response:
            return await response.text()

    async def fetch_all_pages(self, base_url):
        """Fetch all pages of the Letterboxd watchlist asynchronously."""
        async with aiohttp.ClientSession() as session:
            # First, get the first page to determine pagination
            first_page_html = await self.fetch_html(session, base_url)
            soup = BeautifulSoup(first_page_html, "html.parser")

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

            # Fetch all pages concurrently
            tasks = [self.fetch_html(session, url) for url in page_urls]
            pages_html = await asyncio.gather(*tasks)

        return "\n".join(pages_html)  # Return concatenated HTML

    def parse_data(self, raw_html):
        """Extract movie details from the HTML content as a DataFrame."""
        soup = BeautifulSoup(raw_html, "html.parser")
        movies = []

        for movie in soup.select("li.poster-container"):
            # Extract film slug (used for title and link)
            film_slug_tag = movie.select_one("div.film-poster")
            film_slug = film_slug_tag["data-film-slug"] if film_slug_tag else None

            # Extract title (not directly available, needs an additional request in some cases)
            title = film_slug.replace("-", " ").title() if film_slug else None

            # Remove the year and parentheses if in the format "(YYYY)"
            title = re.sub(r"\s*\d{4}", "", title) if title else None

            movies.append(
                {
                    "title": title.lower(),
                    "year": None,  # Needs to be fetched separately
                    "link": None,
                    "poster_url": None,
                    "film_slug": film_slug,
                    "date_added": pd.Timestamp.now(),
                }
            )

        return pd.DataFrame(movies)

    def run(self, url):
        """Execute full scraping pipeline and return structured DataFrames."""
        raw_html = asyncio.run(self.fetch_all_pages(url))
        watchlist_df = self.parse_data(raw_html=raw_html)
        return watchlist_df
