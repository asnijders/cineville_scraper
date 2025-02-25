import pandas as pd
import time
import random
from tqdm import tqdm
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import UserAgent
from bs4 import BeautifulSoup


class BaseScraper(ABC):
    """Abstract base class for web scrapers."""

    def __init__(self, headless=True):
        """Initialize the scraper with a Selenium WebDriver."""
        self.headless = headless
        self.driver = self._create_driver()

    def _create_driver(self):
        """Set up Chrome WebDriver with random User-Agent."""
        ua = UserAgent()
        options = Options()
        options.add_argument(f"--user-agent={ua.random}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-features=VizDisplayCompositor")

        if self.headless:
            options.add_argument("--headless")

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

    @abstractmethod
    def fetch_data(self, url):
        """Fetch raw HTML content from a website."""
        pass

    @abstractmethod
    def parse_data(self, raw_html):
        """Parse and extract data from HTML."""
        pass

    def run(self, df):
        """Execute full scraping pipeline."""

        urls = df["movie_link"].tolist()
        results = []

        for i, url in enumerate(tqdm(urls, desc="Scraping Progress")):
            raw_html = self.fetch_data(url)
            imdb_link = self.parse_data(raw_html)
            time.sleep(random.uniform(0.3, 1.0))  # Random delay to avoid detection
            results.append((url, imdb_link))  # Append results properly

        self.driver.quit()  # Quit driver after scraping

        # Convert results to DataFrame safely
        if results:
            results_df = pd.DataFrame(results, columns=["movie_link", "imdb_link"])
            df = df.merge(results_df, on="movie_link", how="left")  # Merge safely
        else:
            df["imdb_link"] = None  # Handle empty results gracefully

        # drop rows with duplicate imdb links due to e.g. different screening types
        df = df.drop_duplicates(subset=['imdb_link'], keep='first')

        return df


class IMDBScraper(BaseScraper):
    """Scraper to extract IMDb links from movie pages."""

    def fetch_data(self, url):
        """Fetch raw HTML content from a movie page."""
        self.driver.get(url)
        time.sleep(random.uniform(0.3, 1.0))  # Delay to avoid detection
        return self.driver.page_source

    def parse_data(self, raw_html):
        """Parse and extract IMDb data-link from HTML."""
        soup = BeautifulSoup(raw_html, "html.parser")
        imdb_span = soup.find("span", class_="imdb-rating star-rating")
        if imdb_span and imdb_span.has_attr("data-link"):
            return imdb_span["data-link"]
        return None
