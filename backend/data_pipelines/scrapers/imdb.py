import pandas as pd
import time
import random
import json
from tqdm import tqdm
from bs4 import BeautifulSoup
from data_pipelines.scrapers.baseclass import BaseScraper


class IMDBFetcher(BaseScraper):
    """Scraper to extract IMDb links from Filmladder movie pages."""

    def fetch_data(self, url):
        """Fetch raw HTML content from a movie page."""
        self.driver.get(url)
        time.sleep(random.uniform(0.3, 1.0))  # Delay to avoid detection
        return self.driver.page_source

    def parse_data(self, raw_html):
        """Parse and extract IMDb data-link from HTML."""
        soup = BeautifulSoup(raw_html, "html.parser")

        # Try to find the IMDb rating span first
        imdb_span = soup.find("span", class_="imdb-rating star-rating")
        if imdb_span and imdb_span.has_attr("data-link"):
            return imdb_span["data-link"]

        # If not found, try to find the IMDb button div
        imdb_div = soup.find("div", class_="imdb-button")
        if imdb_div and imdb_div.has_attr("data-link"):
            return imdb_div["data-link"]

        return None  # Return None if no IMDb link is found

    def run(self, df):
        """Execute full scraping pipeline."""
        urls = df["movie_link"].tolist()
        results = []

        for url in tqdm(urls, desc="Scraping Progress"):
            raw_html = self.fetch_data(url)
            imdb_link = self.parse_data(raw_html)
            time.sleep(random.uniform(0.3, 1.0))  # Random delay to avoid detection
            results.append((url, imdb_link))

        self.driver.quit()  # Quit driver after scraping

        # Convert results to DataFrame and merge
        results_df = pd.DataFrame(results, columns=["movie_link", "imdb_link"])
        df = df.merge(results_df, on="movie_link", how="left")

        # Drop rows with duplicate IMDb links (e.g., different screening types)
        df = df.drop_duplicates(subset=["imdb_link"], keep="first")

        return df


class IMDBScraper(BaseScraper):
    """Scraper to extract metadata from IMDb movie pages."""

    def fetch_data(self, url):
        """Fetch raw HTML content from an IMDb movie page."""
        self.driver.get(url)
        time.sleep(random.uniform(0.5, 1.5))  # Random delay to avoid detection
        return self.driver.page_source

    def extract_field(self, soup, selector, attr=None, multiple=False):
        """
        Extracts a field from the BeautifulSoup object.
        - If `attr` is None, extracts text.
        - If `attr` is provided, extracts the attribute value.
        - If `multiple` is True, returns a list of values.
        """
        if multiple:
            elements = soup.select(selector)
            return [
                el.get(attr, "").strip() if attr else el.text.strip() for el in elements
            ]
        element = soup.select_one(selector)
        return (
            element.get(attr, "").strip()
            if attr and element
            else (element.text.strip() if element else None)
        )

    def parse_json_ld(self, soup):
        """Extracts metadata from JSON-LD structured data."""
        script_tag = soup.find("script", type="application/ld+json")
        if script_tag:
            try:
                return json.loads(script_tag.string)
            except json.JSONDecodeError:
                return {}
        return {}

    def parse_data(self, raw_html):
        """Parse and extract metadata from IMDb HTML content."""
        soup = BeautifulSoup(raw_html, "html.parser")
        json_ld = self.parse_json_ld(soup)

        metadata = {
            # "title": self.extract_field(soup, "h1"),
            "imdb_year": json_ld.get("datePublished", "").split("-")[
                0
            ],  # Extract only the year
            "rating": json_ld.get("aggregateRating", {}).get("ratingValue"),
            "genres": self.extract_field(soup, "span.ipc-chip__text", multiple=True),
            "content_rating": json_ld.get("contentRating"),
            "duration": json_ld.get("duration"),
            "director": (
                [d["name"] for d in json_ld.get("director", []) if "name" in d]
                if isinstance(json_ld.get("director"), list)
                else None
            ),
            "writers": (
                [w["name"] for w in json_ld.get("creator", []) if "name" in w]
                if isinstance(json_ld.get("creator"), list)
                else None
            ),
            "actors": (
                [a["name"] for a in json_ld.get("actor", []) if "name" in a]
                if isinstance(json_ld.get("actor"), list)
                else None
            ),
            "rating_count": json_ld.get("aggregateRating", {}).get("ratingCount"),
            "plot": json_ld.get("description"),
            "release_date": json_ld.get("datePublished"),  # Keep full date
            "keywords": (
                json_ld.get("keywords", "").split(", ")
                if json_ld.get("keywords")
                else []
            ),
            "poster_url": json_ld.get("image"),
            "trailer_url": json_ld.get("trailer", {}).get("embedUrl"),
        }

        return metadata

    def run(self, df):
        """Execute full scraping pipeline to gather IMDb metadata."""
        urls = df["imdb_link"].dropna().unique().tolist()  # Avoid duplicates
        self.metadata_results = []

        for url in tqdm(urls, desc="Scraping IMDb Metadata"):
            raw_html = self.fetch_data(url)
            metadata = self.parse_data(raw_html)
            metadata["imdb_link"] = url  # Ensure we keep the link for merging
            time.sleep(random.uniform(1, 4))  # Random to avoid detection
            self.metadata_results.append(metadata)

        self.driver.quit()  # Quit driver after scraping

        metadata_df = pd.DataFrame(self.metadata_results)

        # Merge on imdb_link instead of title
        df = df.merge(metadata_df, on="imdb_link", how="left")
        df["release_date"] = pd.to_datetime(df["release_date"]).dt.date

        return df
