import re
import pandas as pd
from bs4 import BeautifulSoup
from .scraper import Scraper


class ScreeningScraper(Scraper):
    """Scraper for Filmladder screening and cinema data."""

    def __init__(self):
        super().__init__()  # Inherit USER_AGENTS
        self.FILMLADDER_URL = "https://www.filmladder.nl/amsterdam/bioscopen"

    async def fetch_filmladder_data(self):
        """Fetch the HTML content of the Filmladder page asynchronously."""
        raw_html = await self.scrape_all([self.FILMLADDER_URL])
        return raw_html[0] if raw_html else None

    def parse_data(self, raw_html):
        """Extract cinema and screening data from HTML."""
        soup = BeautifulSoup(raw_html, "html.parser")
        cinemas = soup.find_all("div", class_="cinema")

        screenings_data = []
        cinemas_data = []

        for cinema in cinemas:
            cinema_name_tag = cinema.find("div", class_="info cinema-name").find("h3").find("a")
            cinema_name = cinema_name_tag.text.strip() if cinema_name_tag else "Unknown Cinema"

            address_tag = cinema.find("div", class_="address")
            address = address_tag.text.strip() if address_tag else None

            website_tag = cinema_name_tag["href"] if cinema_name_tag else None
            website = f"https://www.filmladder.nl{website_tag}" if website_tag else None

            # Store cinema metadata
            cinemas_data.append({
                "name": cinema_name.lower(),
                "location": "Amsterdam",
                "address": address,
                "website": website,
            })

            # Extract screenings
            movies = cinema.find_all("div", class_="hall")
            for movie in movies:
                title_tag = movie.find("h4").find("a")
                title = title_tag.text.strip() if title_tag else "Unknown Title"

                img_tag = movie.find("img", class_="poster")
                img_url = img_tag["data-src"] if img_tag else None

                rating_tag = movie.find("span", class_="star-rating")
                rating = rating_tag.text.strip() if rating_tag else None

                movie_link = title_tag["href"] if title_tag and title_tag.has_attr("href") else ""
                year_match = re.search(r"-(\d{4})/", movie_link)
                movie_year = year_match.group(1) if year_match else None

                days = movie.find_all("div", class_="day with-perfomances")
                for day in days:
                    times = day.find_all("div", itemprop="startDate")

                    for time_slot in times:
                        time_link = time_slot.find("a")
                        ticket_url = time_link["href"] if time_link else None
                        show_datetime = time_slot.get("content", "Unknown")

                        screenings_data.append({
                            "fl_cinema_name": cinema_name.lower(),
                            "fl_title": title.lower(),
                            "fl_year": movie_year,
                            "fl_show_datetime": show_datetime,
                            "fl_ticket_url": ticket_url,
                            "fl_rating": rating,
                            "fl_movie_link": movie_link,
                            "fl_poster_url": img_url,
                        })

        return pd.DataFrame(screenings_data), pd.DataFrame(cinemas_data)

    async def run(self):
        """Execute full scraping pipeline asynchronously and return structured DataFrames."""
        raw_html = await self.fetch_filmladder_data()
        if raw_html:
            return self.parse_data(raw_html)
        return pd.DataFrame(), pd.DataFrame()


class ImdbIdScraper(Scraper):
    """Scraper to extract IMDb links from Filmladder movie pages asynchronously."""

    def __init__(self):
        super().__init__()  # Inherit USER_AGENTS

    def parse_data(self, raw_html):
        """Parse and extract IMDb data-link from HTML."""
        if not raw_html:
            return None

        soup = BeautifulSoup(raw_html, "html.parser")
        imdb_element = soup.find("span", class_="imdb-rating star-rating") or \
                       soup.find("div", class_="imdb-button")

        return imdb_element.get("data-link") if imdb_element else None

    async def run(self, df):
        """Execute full scraping pipeline asynchronously."""
        urls = df["fl_movie_link"].tolist()

        # Fetch content asynchronously
        raw_html_list = await self.scrape_all(urls)

        # Parse each page
        results = [(url, self.parse_data(html)) for url, html in zip(urls, raw_html_list)]

        # Convert results to DataFrame and merge
        results_df = pd.DataFrame(results, columns=["fl_movie_link", "imdb_link"])
        df = df.merge(results_df, on="fl_movie_link", how="left")

        # Drop duplicate IMDb links (handling different screening types)
        df = df.drop_duplicates(subset=["imdb_link"], keep="first")

        # Extract IMDb ID using regex for efficiency
        df["imdb_id"] = df["imdb_link"].str.extract(r'/title/(tt\d+)')

        return df


class RedirectUrlScraper(Scraper):
    """
    Scraper to fetch film ladder ticket referral links
    """
    
    def __init__(self):
        super().__init__()  # Inherit USER_AGENTS from Scraper

    def parse_redirect_url(self, html_content):
        """
        Parse the redirect URL from the HTML content.

        Args:
        - html_content: The raw HTML content of the page as a string.

        Returns:
        - The redirect URL if found, otherwise None.
        """
        match = re.search(r"window\.location=['\"](https?://[^\s'\"]+)['\"]", 
                          html_content)
        return match.group(1) if match else None

    async def run(self, df):
        """Execute full scraping pipeline asynchronously."""
        urls = df["fl_ticket_url"].tolist()

        # Fetch HTML content for each URL asynchronously using inherited scrape_all
        html_responses = await self.scrape_all(urls)

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
