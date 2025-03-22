import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
import re
import numpy as np
from .scraper import Scraper

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.123 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.98 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36"
    ]


class TmdbIdScraper(Scraper):
    """Scraper to extract TMDB links from Letterboxd movie pages using asyncio."""

    def __init__(self, cache_expiry=86400):  # Default expiry: 24 hours
        super().__init__(cache_expiry=cache_expiry)  # Pass to Scraper

    def parse_data(self, raw_html):
        """Parse and extract TMDB ID, IMDb ID, film ID, film slug, and poster URL from HTML."""
        if not raw_html:
            return None

        soup = BeautifulSoup(raw_html, "html.parser")

        data = {
            "lb_film_id": None,
            "lb_film_slug": None,
            "lb_poster_url": None,
            "tmdb_id": None,
            "imdb_id": None
        }

        # Extract TMDB ID from body tag
        body_tag = soup.find("body", class_="film backdropped")
        if body_tag:
            data["tmdb_id"] = body_tag.get("data-tmdb-id")

        # Extract TMDB ID from TMDB link
        tmdb_link = soup.find("a", class_="micro-button track-event", attrs={"data-track-action": "TMDB"})
        if tmdb_link and "themoviedb.org/movie/" in tmdb_link["href"]:
            try:
                data["tmdb_id"] = tmdb_link["href"].split("/")[-2]  # Extracts the ID from the URL
            except IndexError:
                pass

        # Extract IMDb ID from IMDb link
        imdb_url = soup.find("a", class_="micro-button track-event", attrs={"data-track-action": "IMDb"})
        if imdb_url and "imdb.com/title/" in imdb_url["href"]:
            try:
                data["imdb_id"] = imdb_url["href"].split("/")[-2]  # Extracts the IMDb ID from the URL
            except IndexError:
                pass

        # Extract film ID and film slug from backdrop container
        backdrop_div = soup.find("div", class_="backdrop-wrapper")
        if backdrop_div:
            data["lb_film_id"] = backdrop_div.get("data-film-id")
            data["lb_film_slug"] = backdrop_div.get("data-film-slug")

        # Extract poster URL
        poster_div = soup.find("div", class_="really-lazy-load", attrs={"data-type": "film"})
        if poster_div:
            data["lb_poster_url"] = poster_div.get("data-poster-url")

        return data

    async def run(self, df):
        """Execute full scraping pipeline asynchronously."""

        def build_url(imdb_id):
            return f'https://letterboxd.com/imdb/{imdb_id}'

        # print(df)
        df.loc[:, 'lb_url'] = df['imdb_id'].apply(lambda x: build_url(x))
        urls = df["lb_url"].tolist()

        # Fetch content asynchronously
        await self.setup_redis()
        raw_html_list = await self.scrape_all(urls)
        await self.close_redis()

        # Parse each page
        results = [
            self.parse_data(html) for html in raw_html_list
        ]

        # Convert results to DataFrame and merge
        results_df = pd.DataFrame(results)

        df = df.merge(results_df, on="imdb_id", how="left")

        # Drop rows with duplicate IMDb links (e.g., different screening types)
        df = df.drop_duplicates(subset=["imdb_id"], keep="first")

        # Ensure all None/NaN/null values are consistently represented as np.nan
        df.replace(["None", "null"], np.nan, inplace=True)  # If string "None" or "null" are present
        df = df.map(lambda x: np.nan if pd.isna(x) else x)  # Convert None and NaN to np.nan

        return df


class WatchlistScraper:
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
