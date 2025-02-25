import time
import pandas as pd
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from scrapers.baseclass import BaseScraper


class LetterboxdScraper(BaseScraper):
    """Scraper for Letterboxd watchlist."""

    BASE_URL = "https://letterboxd.com/ard_s/watchlist/"

    def fetch_data(self):
        """Fetch all pages of the Letterboxd watchlist."""
        self.driver.get(self.BASE_URL)
        all_html = []

        while True:
            time.sleep(0.5)  # Wait for content to load
            all_html.append(self.driver.page_source)  # Save HTML content

            # Try to find and click the "Next" button
            try:
                next_button = WebDriverWait(self.driver, 0.5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "next"))
                )
                next_button.click()
                time.sleep(0.5)  # Allow new content to load                
            except:
                break  # Exit loop when no more pages

        return "\n".join(all_html)  # Return concatenated HTML

    def parse_data(self, raw_html):
        self.raw_html = raw_html

        """Extract movie details from the HTML content as a DataFrame."""
        soup = BeautifulSoup(raw_html, "html.parser")
        movies = []

        for movie in soup.select("li.poster-container"):
            title_tag = movie.select_one("a.frame")
            title = title_tag["data-original-title"] if title_tag else None
            link = f"https://letterboxd.com{title_tag['href']}" if title_tag else None
            poster_tag = movie.select_one("img.image")
            poster_url = poster_tag["src"] if poster_tag else None
            film_slug_tag = movie.select_one("div.film-poster")
            film_slug = film_slug_tag["data-film-slug"] if film_slug_tag else None

            movies.append(
                {
                    "title": title.lower(),
                    "year": None,  # Year needs to be fetched separately
                    "link": link,
                    "poster_url": poster_url,
                    "film_slug": film_slug,
                    "date_added": pd.Timestamp.now(),  # Current timestamp for when added
                }
            )

        movies = pd.DataFrame(movies)

        # Extract year and move it to 'year' column
        movies["year"] = movies["title"].str.extract(r"\((\d{4})\)").astype("Int64")

        # Remove the year from the title and lowercase it
        movies["title"] = movies["title"].str.replace(r"\s*\(\d{4}\)", "", regex=True).str.lower()

        return movies

    def run(self):
        """Execute full scraping pipeline and return structured DataFrames."""
        raw_html = self.fetch_data()
        watchlist_df = self.parse_data(raw_html=raw_html)
        self.driver.quit()
        return watchlist_df
