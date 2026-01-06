import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class PublicHolidaysScraper(BaseScraper):
    """Scraper for publicholidays.hu - the best source for Hungarian holidays."""
    
    name = "PublicHolidays.hu"
    base_url = "https://publicholidays.hu/"
    min_year_offset = -2
    max_year_offset = 3
    
    MONTH_MAP = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    
    DAY_NAMES = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday", 
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    def get_url(self, year: int) -> str:
        """This site has all years on the main page."""
        return self.base_url
    
    def _parse_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse date string like '1 Jan' or '15 Mar' to date object."""
        date_str = date_str.strip().lower()
        
        # Try "DD Mon" format (1 Jan, 15 Mar)
        match = re.match(r"(\d+)\s+(\w+)", date_str)
        if match:
            day, month_str = match.groups()
            month = self.MONTH_MAP.get(month_str[:3])
            if month:
                try:
                    return date(year, month, int(day))
                except ValueError:
                    pass
        
        return None
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape Hungarian holidays from publicholidays.hu."""
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        
        # Find the heading for the requested year
        year_heading = soup.find("h2", string=re.compile(f"{year}\\s+Public\\s+Holidays", re.IGNORECASE))
        
        if not year_heading:
            # Try finding by ID
            year_heading = soup.find(id=f"{year}-public-holidays")
        
        if not year_heading:
            print(f"Could not find section for year {year}")
            return []
        
        # Find the table that follows this heading
        table = year_heading.find_next("table")
        
        if not table:
            print(f"Could not find table for year {year}")
            return []
        
        # Get all data rows (skip header row in thead)
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
        else:
            rows = table.find_all("tr")[1:]  # Skip header
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            
            # Column structure: Date | Day | Holiday
            date_text = cells[0].get_text(strip=True)
            # cells[1] is day name - we skip it
            holiday_name = cells[2].get_text(strip=True)
            
            # Skip rows that are just notes (like "Visit jogtar.hu...")
            if "visit" in date_text.lower() or not holiday_name:
                continue
            
            holiday_date = self._parse_date(date_text, year)
            
            if holiday_date and holiday_name:
                holidays.append(Holiday(
                    date=holiday_date,
                    name=holiday_name,
                    name_en=holiday_name,
                    is_national=True
                ))
        
        return sorted(holidays, key=lambda x: x.date)
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """
        Scrape weekend workdays. PublicHolidays.hu doesn't always list these,
        but we'll look for any mentions in the page.
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        workdays = []
        page_text = soup.get_text().lower()
        
        # Look for common patterns indicating workdays
        # Hungarian government typically announces these separately
        # This is a best-effort scrape
        
        # Pattern for "X is a working day" or similar
        workday_patterns = [
            rf"(\d+)\s+(january|february|march|april|may|june|july|august|september|october|november|december)[^.]*(?:working|work)\s*day",
            rf"(\d+)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[^.]*(?:working|work)\s*day",
        ]
        
        for pattern in workday_patterns:
            matches = re.finditer(pattern, page_text)
            for match in matches:
                try:
                    day, month_str = match.groups()
                    month = self.MONTH_MAP.get(month_str[:3])
                    if month:
                        workday_date = date(year, month, int(day))
                        if workday_date.weekday() >= 5:  # Only weekend days
                            day_name = self.DAY_NAMES.get(workday_date.weekday())
                            if workday_date not in [w.date for w in workdays]:
                                workdays.append(WorkDay(
                                    date=workday_date,
                                    original_day=day_name,
                                    reason="Bridge day workday"
                                ))
                except (ValueError, TypeError):
                    pass
        
        return sorted(workdays, key=lambda x: x.date)
