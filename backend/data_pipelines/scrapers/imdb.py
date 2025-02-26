import pandas as pd
import time
import random
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

    def parse_data(self, raw_html):
        """Parse and extract metadata from IMDb HTML content."""
        soup = BeautifulSoup(raw_html, "html.parser")

        print(raw_html)

        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else None

        year_tag = soup.find("span", class_="sc-8c396aa2-2")
        year = year_tag.text.strip() if year_tag else None

        rating_tag = soup.find("span", class_="sc-7ab21ed2-1")
        rating = rating_tag.text.strip() if rating_tag else None

        genre_tags = soup.find_all("span", class_="ipc-chip__text")
        genres = [tag.text.strip() for tag in genre_tags] if genre_tags else []

        return {
            "title": title,
            "year": year,
            "rating": rating,
            "genres": ", ".join(genres),
        }

    def run(self, df):
        """Execute full scraping pipeline to gather IMDb metadata."""
        urls = df["imdb_link"].dropna().tolist()
        metadata_results = []

        for url in tqdm(urls, desc="Scraping IMDb Metadata"):
            raw_html = self.fetch_data(url)
            metadata = self.parse_data(raw_html)
            time.sleep(random.uniform(0.5, 1.5))  # Random delay to avoid detection
            metadata_results.append(metadata)

        self.driver.quit()  # Quit driver after scraping

        metadata_df = pd.DataFrame(metadata_results)
        df = df.merge(metadata_df, left_on="imdb_link", right_on="title", how="left")

        return df
