import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class DailyNewsHungaryScraper(BaseScraper):
    """
    Scraper for DailyNewsHungary - English language Hungarian news site.
    Good source for weekend workday information.
    https://dailynewshungary.com
    """
    
    name = "DailyNewsHungary"
    base_url = "https://dailynewshungary.com/long-weekends-in-hungary-in-{year}-revealed/"
    min_year_offset = -2
    max_year_offset = 2
    
    MONTH_MAP = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    
    DAY_NAMES = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    def _parse_date(self, date_str: str, year: int) -> Optional[date]:
        """Parse English date string like 'May 17' or '17 May'."""
        date_str = date_str.strip().lower()
        
        for month_name, month_num in self.MONTH_MAP.items():
            if month_name in date_str:
                # Try "Month DD" format
                day_match = re.search(rf"{month_name}\s+(\d+)", date_str)
                if day_match:
                    try:
                        return date(year, month_num, int(day_match.group(1)))
                    except ValueError:
                        pass
                
                # Try "DD Month" format
                day_match = re.search(rf"(\d+)\s+{month_name}", date_str)
                if day_match:
                    try:
                        return date(year, month_num, int(day_match.group(1)))
                    except ValueError:
                        pass
        
        return None
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """
        DailyNewsHungary focuses on workday info, not full holiday lists.
        Return empty - let other scrapers handle holidays.
        """
        return []
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """
        Scrape weekend workdays from DailyNewsHungary articles.
        They publish articles about the government decree each year.
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        workdays = []
        page_text = soup.get_text()
        
        # Look for patterns like:
        # "Saturday, 17 May 2025, is a working day"
        # "Saturday 17 May 2025 working day"
        
        working_day_patterns = [
            r"saturday[,\s]+(\d+)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}[,\s]+(?:is\s+)?(?:a\s+)?working\s*day",
            r"(\d+)(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}[,\s]+(?:is\s+)?(?:a\s+)?working\s*day",
            r"saturday[,\s]+(\d+)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[,\s]+working\s*day",
        ]
        
        for pattern in working_day_patterns:
            matches = re.finditer(pattern, page_text, re.IGNORECASE)
            for match in matches:
                try:
                    day, month_str = match.groups()[:2]
                    month = self.MONTH_MAP.get(month_str.lower()[:3])
                    
                    if month:
                        workday_date = date(year, month, int(day))
                        
                        # Verify it's a weekend day
                        if workday_date.weekday() >= 5:
                            day_name = self.DAY_NAMES.get(workday_date.weekday())
                            
                            # Check if not already added
                            if workday_date not in [w.date for w in workdays]:
                                # Try to find the reason (rest day info)
                                reason = self._find_reason(page_text, workday_date)
                                
                                workdays.append(WorkDay(
                                    date=workday_date,
                                    original_day=day_name,
                                    reason=reason
                                ))
                except (ValueError, TypeError, IndexError):
                    continue
        
        return sorted(workdays, key=lambda x: x.date)
    
    def _find_reason(self, text: str, workday_date: date) -> str:
        """Try to find the reason/related holiday for a workday."""
        month_names = {
            1: "january", 2: "february", 3: "march", 4: "april",
            5: "may", 6: "june", 7: "july", 8: "august",
            9: "september", 10: "october", 11: "november", 12: "december"
        }
        
        month_name = month_names.get(workday_date.month, "")
        
        # Common patterns that link working days to rest days
        # e.g., "Saturday, 17 May 2025, is a working day; Friday, 2 May 2025, is a rest day"
        pattern = rf"{workday_date.day}\s+{month_name}.*?working\s*day[;,]\s*(\w+day)[,\s]+(\d+)\s+(\w+).*?rest\s*day"
        
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rest_day, rest_date_day, rest_month = match.groups()
            return f"Working day for {rest_month} {rest_date_day} bridge day"
        
        # Default reason
        return "Bridge day workday"

