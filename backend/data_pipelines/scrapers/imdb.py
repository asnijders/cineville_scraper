import aiohttp
import asyncio
import pandas as pd
import random
import time
import json
import re
from bs4 import BeautifulSoup
from tqdm import tqdm
# from .base_scraper import BaseScraper  # Assuming BaseScraper is in the same package


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.129 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.123 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.98 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.132 Safari/537.36"
    ]


class IMDBFetcher():
    """Scraper to extract IMDb links from Filmladder movie pages using asyncio."""

    def __init__(self):
        pass

    async def fetch_data(self, session, url, semaphore):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
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

    def parse_data(self, raw_html):
        """Parse and extract IMDb data-link from HTML."""
        if not raw_html:
            return None

        soup = BeautifulSoup(raw_html, "html.parser")
        imdb_span = soup.find("span", class_="imdb-rating star-rating")
        if imdb_span and imdb_span.has_attr("data-link"):
            return imdb_span["data-link"]

        imdb_div = soup.find("div", class_="imdb-button")
        if imdb_div and imdb_div.has_attr("data-link"):
            return imdb_div["data-link"]

        return None

    async def run(self, df):
        """Execute full scraping pipeline asynchronously."""
        urls = df["fl_movie_link"].tolist()

        # Fetch content asynchronously
        raw_html_list = await self.scrape_all(urls)

        # Parse each page
        results = [
            (url, self.parse_data(html)) for url, html in zip(urls,
                                                              raw_html_list)
        ]

        # Convert results to DataFrame and merge
        results_df = pd.DataFrame(results, columns=["fl_movie_link", 
                                                    "imdb_link"])
        df = df.merge(results_df, on="fl_movie_link", how="left")

        # Drop rows with duplicate IMDb links (e.g., different screening types)
        df = df.drop_duplicates(subset=["imdb_link"], keep="first")

        df['imdb_id'] = df['imdb_link'].apply(lambda x: x.split('/')[-1] if x is not None else None)

        return df


class LetterboxdFetcher():
    """Scraper to extract TMDB links from Letterboxd movie pages using asyncio."""

    def __init__(self):
        pass

    async def fetch_data(self, session, url, semaphore):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
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

    def parse_data(self, raw_html):
        """Parse and extract TMDB ID, IMDb ID, film ID, film slug, and poster URL from HTML."""
        if not raw_html:
            return None
        
        soup = BeautifulSoup(raw_html, "html.parser")
        
        data = {
            "tmdb_id": None,
            "imdb_id": None,
            "lb_film_id": None,
            "lb_film_slug": None,
            "lb_poster_url": None
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
        imdb_link = soup.find("a", class_="micro-button track-event", attrs={"data-track-action": "IMDb"})
        if imdb_link and "imdb.com/title/" in imdb_link["href"]:
            try:
                data["imdb_id"] = imdb_link["href"].split("/")[-2]  # Extracts the IMDb ID from the URL
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
        df['letterboxd_url'] = df['imdb_id'].apply(lambda x: build_url(x))
        urls = df["letterboxd_url"].tolist()

        # Fetch content asynchronously
        raw_html_list = await self.scrape_all(urls)

        # Parse each page
        results = [
            self.parse_data(html) for html in raw_html_list
        ]

        # Convert results to DataFrame and merge
        results_df = pd.DataFrame(results)

        # print)
        
        df = df.merge(results_df, on="imdb_id", how="left")

        # Drop rows with duplicate IMDb links (e.g., different screening types)
        df = df.drop_duplicates(subset=["imdb_id"], keep="first")

        return df


class ReferralFetcher:
    """
    Scraper to fetch film ladder ticket referral links
    """

    def __init__(self):
        pass

    async def fetch_data(self, session, url, semaphore):
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        """Fetch the HTML content of the final page asynchronously with random sleep."""
        async with semaphore:
            try:
                # Add random sleep to mimic human behavior
                sleep_time = random.uniform(1, 3)  # Sleep time between 1 and 3 seconds
                await asyncio.sleep(sleep_time)

                # Allow redirects to follow the chain
                async with session.get(url, headers=headers, allow_redirects=True) as response:
                    if response.status == 200:
                        # Return the HTML content (raw text) of the final response
                        return await response.text()  # Get the HTML content of the final page
                    return None
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                return None

    def parse_redirect_url(self, html_content):
        """
        Parse the redirect URL from the HTML content.

        Args:
        - html_content: The raw HTML content of the page as a string.

        Returns:
        - The redirect URL if found, otherwise None.
        """
        # Regular expression to capture the URL in the window.location statement
        match = re.search(r"window\.location=['\"](https?://[^\s'\"]+)['\"]", html_content)
        if match:
            return match.group(1)  # Return the captured URL
        return None

    async def fetch_all(self, urls, max_concurrent=5):
        """Fetch all pages asynchronously."""
        semaphore = asyncio.Semaphore(max_concurrent)
        connector = aiohttp.TCPConnector(limit=max_concurrent)

        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_data(session, url, semaphore) for url in urls]
            return await asyncio.gather(*tasks)

    async def run(self, df):
        """Execute full scraping pipeline asynchronously."""
        urls = df["fl_ticket_url"].tolist()

        # Fetch HTML content for each URL asynchronously
        html_responses = await self.fetch_all(urls)

        # Parse the redirect URL from each HTML response
        redirect_urls = [self.parse_redirect_url(html) for html in html_responses]

        # Create a new DataFrame with the original URLs and the redirect URLs
        results_df = pd.DataFrame({
            "fl_ticket_url": urls,
            "redirect_url": redirect_urls
        })

        # Merge the original DataFrame with the redirect URLs DataFrame
        df = df.merge(results_df, on="fl_ticket_url", how="left")

        return df