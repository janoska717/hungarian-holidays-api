import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class OfficeHolidaysScraper(BaseScraper):
    """Scraper for officeholidays.com Hungarian holidays."""
    
    name = "OfficeHolidays.com"
    base_url = "https://www.officeholidays.com/countries/hungary/{year}"
    min_year_offset = -3
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
    
    def _parse_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse date string to date object."""
        date_str = date_str.strip().lower()
        
        # Try various patterns
        patterns = [
            r"(\d+)\s+(\w+)",  # "15 March"
            r"(\w+)\s+(\d+)",  # "March 15"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                groups = match.groups()
                if groups[0].isdigit():
                    day, month_str = int(groups[0]), groups[1]
                else:
                    month_str, day = groups[0], int(groups[1])
                
                month = self.MONTH_MAP.get(month_str[:3].lower())
                if month:
                    try:
                        return date(year, month, day)
                    except ValueError:
                        pass
        
        return None
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape Hungarian holidays from officeholidays.com."""
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        
        # Find holiday table
        table = soup.find("table", class_="country-table")
        if not table:
            table = soup.find("table")
        
        if not table:
            return []
        
        rows = table.find_all("tr")
        
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            
            # First cell contains date
            date_cell = cells[0].get_text(strip=True)
            # Second cell contains holiday name
            name_cell = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            
            holiday_date = self._parse_date(date_cell, year)
            
            if holiday_date and name_cell:
                holidays.append(Holiday(
                    date=holiday_date,
                    name=name_cell,
                    name_en=name_cell,
                    is_national=True
                ))
        
        # Remove duplicates
        seen_dates = set()
        unique_holidays = []
        for h in holidays:
            if h.date not in seen_dates:
                seen_dates.add(h.date)
                unique_holidays.append(h)
        
        return sorted(unique_holidays, key=lambda x: x.date)
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """OfficeHolidays doesn't provide weekend workday info."""
        return []

