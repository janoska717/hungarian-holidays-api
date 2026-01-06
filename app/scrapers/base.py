from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay, SourceInfo


class BaseScraper(ABC):
    """Base class for all holiday scrapers."""
    
    name: str = "Base Scraper"
    base_url: str = ""
    
    # Year range this scraper typically supports (relative to current year)
    min_year_offset: int = -2  # Can scrape 2 years in the past
    max_year_offset: int = 2   # Can scrape 2 years in the future
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5,hu;q=0.3",
            }
        )
    
    def get_url(self, year: int) -> str:
        """Get the URL for a specific year."""
        return self.base_url.format(year=year)
    
    def fetch_page(self, year: int) -> Optional[BeautifulSoup]:
        """Fetch and parse the page for a given year."""
        url = self.get_url(year)
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except httpx.HTTPError as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def supports_year(self, year: int) -> bool:
        """Check if this scraper supports the given year."""
        current_year = datetime.now().year
        return (current_year + self.min_year_offset) <= year <= (current_year + self.max_year_offset)
    
    def get_year_distance(self, year: int) -> int:
        """Get the distance from the ideal year range (0 if within range)."""
        current_year = datetime.now().year
        if self.supports_year(year):
            return 0
        min_supported = current_year + self.min_year_offset
        max_supported = current_year + self.max_year_offset
        return min(abs(year - min_supported), abs(year - max_supported))
    
    @abstractmethod
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape holidays for the given year."""
        pass
    
    @abstractmethod
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """Scrape weekend workdays for the given year."""
        pass
    
    def scrape(self, year: int) -> tuple[list[Holiday], list[WorkDay], SourceInfo]:
        """Scrape all data for the given year."""
        holidays = self.scrape_holidays(year)
        workdays = self.scrape_weekend_workdays(year)
        source = SourceInfo(
            name=self.name,
            url=self.get_url(year),
            year_coverage=year,
            scraped_at=datetime.now().isoformat()
        )
        return holidays, workdays, source
    
    def __del__(self):
        if hasattr(self, 'client'):
            self.client.close()

