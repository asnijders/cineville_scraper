import time
import re
import pandas as pd
from bs4 import BeautifulSoup
from scrapers.baseclass import BaseScraper


class FilmladderScraper(BaseScraper):
    """Scraper for Filmladder screening and cinema data."""

    FILMLADDER_URL = "https://www.filmladder.nl/amsterdam/bioscopen"

    def fetch_data(self):
        """Navigate to the Filmladder page and fetch the HTML content."""
        self.driver.get(self.FILMLADDER_URL)
        time.sleep(3)  # Allow page to load

        # Simulate scrolling to trigger lazy loading
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        return self.driver.page_source  # Return full page HTML

    def parse_data(self, raw_html):

        self.raw_html = raw_html

        """Extract cinema and screening data from HTML."""
        soup = BeautifulSoup(raw_html, "html.parser")
        cinemas = soup.find_all("div", class_="cinema")

        screenings_data = []
        cinemas_data = []

        for cinema in cinemas:
            cinema_name_tag = (
                cinema.find("div", class_="info cinema-name").find("h3").find("a")
            )
            cinema_name = (
                cinema_name_tag.text.strip() if cinema_name_tag else "Unknown Cinema"
            )

            address_tag = cinema.find("div", class_="address")
            address = address_tag.text.strip() if address_tag else None

            website_tag = cinema_name_tag["href"] if cinema_name_tag else None
            website = f"https://www.filmladder.nl{website_tag}" if website_tag else None

            # Store cinema metadata
            cinemas_data.append(
                {
                    "name": cinema_name,
                    "location": "Amsterdam",
                    "address": address,
                    "website": website,
                }
            )

            # Extract screenings
            movies = cinema.find_all("div", class_="hall")
            for movie in movies:
                title_tag = movie.find("h4").find("a")
                title = title_tag.text.strip() if title_tag else "Unknown Title"

                img_tag = movie.find("img", class_="poster")
                img_url = img_tag["data-src"] if img_tag else None

                rating_tag = movie.find("span", class_="star-rating")
                rating = rating_tag.text.strip() if rating_tag else None

                # Extract movie year from href
                movie_link = (
                    title_tag["href"]
                    if title_tag and title_tag.has_attr("href")
                    else ""
                )
                year_match = re.search(r"-(\d{4})/", movie_link)
                movie_year = (
                    year_match.group(1) if year_match else None
                )  # Extract year if found

                days = movie.find_all("div", class_="day with-perfomances")
                for day in days:
                    times = day.find_all("div", itemprop="startDate")

                    for time_slot in times:
                        time_link = time_slot.find("a")
                        ticket_url = time_link["href"] if time_link else None
                        show_datetime = time_slot.get("content", "Unknown")

                        screenings_data.append(
                            {
                                "cinema_name": cinema_name,
                                "title": title,
                                "year": movie_year,
                                "show_datetime": show_datetime,
                                "ticket_url": ticket_url,
                                "rating": rating,
                                "poster_url": img_url,
                            }
                        )

        return pd.DataFrame(screenings_data), pd.DataFrame(cinemas_data)

    def run(self):
        """Execute full scraping pipeline and return structured DataFrames."""
        raw_html = self.fetch_data()
        screenings_df, cinemas_df = self.parse_data(raw_html=raw_html)
        self.driver.quit()
        return screenings_df, cinemas_df
