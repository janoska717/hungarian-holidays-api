import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class TimeAndDateScraper(BaseScraper):
    """Scraper for timeanddate.com Hungarian holidays."""
    
    name = "TimeAndDate.com"
    base_url = "https://www.timeanddate.com/holidays/hungary/{year}"
    min_year_offset = -5
    max_year_offset = 5
    
    # Hungarian month names mapping
    MONTH_MAP = {
        "jan": 1, "january": 1, "január": 1,
        "feb": 2, "february": 2, "február": 2,
        "mar": 3, "march": 3, "március": 3,
        "apr": 4, "april": 4, "április": 4,
        "may": 5, "május": 5,
        "jun": 6, "june": 6, "június": 6,
        "jul": 7, "july": 7, "július": 7,
        "aug": 8, "august": 8, "augusztus": 8,
        "sep": 9, "september": 9, "szeptember": 9,
        "oct": 10, "october": 10, "október": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    
    def _parse_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse date string like 'Mar 15' or '15 Mar' to date object."""
        date_str = date_str.strip().lower()
        
        # Try "Mon DD" format (Mar 15)
        match = re.match(r"(\w+)\s+(\d+)", date_str)
        if match:
            month_str, day_str = match.groups()
            month = self.MONTH_MAP.get(month_str[:3])
            if month:
                try:
                    return date(year, month, int(day_str))
                except ValueError:
                    pass
        
        # Try "DD Mon" format (15 Mar)
        match = re.match(r"(\d+)\s+(\w+)", date_str)
        if match:
            day_str, month_str = match.groups()
            month = self.MONTH_MAP.get(month_str[:3])
            if month:
                try:
                    return date(year, month, int(day_str))
                except ValueError:
                    pass
        
        return None
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape Hungarian holidays from timeanddate.com."""
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        
        # Find the holiday table
        table = soup.find("table", {"id": "holidays-table"})
        if not table:
            # Try alternative selector
            table = soup.find("table", class_="zebra")
        
        if not table:
            return []
        
        rows = table.find_all("tr")
        
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            
            # Get date from first cell
            date_cell = cells[0].get_text(strip=True)
            holiday_date = self._parse_date(date_cell, year)
            
            if not holiday_date:
                continue
            
            # Get holiday name (usually in the 3rd cell)
            name_cell = cells[2] if len(cells) > 2 else cells[1]
            name = name_cell.get_text(strip=True)
            
            # Check if it's a national/public holiday
            holiday_type = cells[1].get_text(strip=True).lower() if len(cells) > 1 else ""
            is_national = "national" in holiday_type or "public" in holiday_type
            
            if name and holiday_date:
                holidays.append(Holiday(
                    date=holiday_date,
                    name=name,
                    name_en=name,
                    is_national=is_national
                ))
        
        # Filter to only national holidays and remove duplicates
        seen_dates = set()
        unique_holidays = []
        for h in holidays:
            if h.is_national and h.date not in seen_dates:
                seen_dates.add(h.date)
                unique_holidays.append(h)
        
        return sorted(unique_holidays, key=lambda x: x.date)
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """TimeAndDate doesn't provide weekend workday info."""
        return []

