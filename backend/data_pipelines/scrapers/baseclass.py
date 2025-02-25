from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fake_useragent import FakeUserAgent


class BaseScraper(ABC):
    """Abstract base class for web scrapers."""

    def __init__(self, headless=True):
        """Initialize the scraper with a Selenium WebDriver."""
        self.headless = headless
        self.driver = self._create_driver()

    def _create_driver(self):
        """Set up Chrome WebDriver with random User-Agent."""
        ua = FakeUserAgent()
        options = Options()
        options.add_argument(f"--user-agent={ua.random}")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-features=VizDisplayCompositor")

        if self.headless:
            options.add_argument("--headless")  # Run browser in headless mode

        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

    @abstractmethod
    def fetch_data(self):
        """Fetch raw HTML content from a website."""
        pass

    @abstractmethod
    def parse_data(self, raw_html):
        """Parse and extract data from HTML."""
        pass

    def run(self):
        """Execute full scraping pipeline."""
        raw_html = self.fetch_data()
        data_df = self.parse_data(raw_html)  # Returns a DataFrame
        self.driver.quit()  # Close WebDriver
        return data_df
