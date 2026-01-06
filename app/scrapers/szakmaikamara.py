import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class SzakmaiKamaraScraper(BaseScraper):
    """
    Scraper for szakmaikamara.hu - Hungarian professional chamber website.
    Has good information about munkaszüneti napok and hosszú hétvégék.
    Source: https://szakmaikamara.hu/munkaszuneti-napok/
    """
    
    name = "SzakmaiKamara.hu"
    base_url = "https://szakmaikamara.hu/munkaszuneti-napok/"
    min_year_offset = -1
    max_year_offset = 1
    
    MONTH_MAP = {
        "január": 1, "jan": 1,
        "február": 2, "feb": 2,
        "március": 3, "márc": 3,
        "április": 4, "ápr": 4,
        "május": 5, "máj": 5,
        "június": 6, "jún": 6,
        "július": 7, "júl": 7,
        "augusztus": 8, "aug": 8,
        "szeptember": 9, "szept": 9,
        "október": 10, "okt": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    
    DAY_NAMES = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    def get_url(self, year: int) -> str:
        """This page has current year's info."""
        return self.base_url
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """
        Scrape holiday information from szakmaikamara.hu.
        This site doesn't have a complete list, but mentions key dates.
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        page_text = soup.get_text()
        
        # Look for long weekend date ranges that indicate holidays
        # Pattern: "YYYY. hónap DD-DD-DD-DD." (e.g., "2025. december 24-25-26-27-28.")
        range_patterns = [
            # Christmas long weekend
            (rf"{year}\.\s*december\s+(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})", 12, "Christmas Holiday Period"),
            # Easter weekend
            (rf"{year}\.\s*április\s+(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})", 4, "Easter Holiday Period"),
            # May Day weekend
            (rf"{year}\.\s*május\s+(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})", 5, "Labour Day Holiday Period"),
            # October 23 weekend
            (rf"{year}\.\s*október\s+(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})", 10, "October Revolution Holiday Period"),
            # Pentecost weekend (3 days)
            (rf"{year}\.\s*június\s+(\d{{1,2}})-(\d{{1,2}})-(\d{{1,2}})", 6, "Whit Weekend"),
        ]
        
        seen_dates = set()
        
        for pattern, month, holiday_name in range_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                days = [int(d) for d in match.groups()]
                for day in days:
                    try:
                        holiday_date = date(year, month, day)
                        if holiday_date not in seen_dates:
                            # Determine specific holiday name based on date
                            specific_name = self._get_specific_holiday_name(holiday_date)
                            holidays.append(Holiday(
                                date=holiday_date,
                                name=specific_name,
                                name_en=specific_name,
                                is_national=True
                            ))
                            seen_dates.add(holiday_date)
                    except ValueError:
                        continue
        
        return sorted(holidays, key=lambda x: x.date)
    
    def _get_specific_holiday_name(self, d: date) -> str:
        """Get specific holiday name based on date."""
        if d.month == 1 and d.day == 1:
            return "New Year's Day"
        elif d.month == 3 and d.day == 15:
            return "1848 Revolution Memorial Day"
        elif d.month == 5 and d.day == 1:
            return "Labour Day"
        elif d.month == 5 and d.day == 2:
            return "Bridge Day (Labour Day)"
        elif d.month == 8 and d.day == 20:
            return "St. Stephen's Day"
        elif d.month == 10 and d.day == 23:
            return "1956 Revolution Memorial Day"
        elif d.month == 10 and d.day == 24:
            return "Bridge Day (October Revolution)"
        elif d.month == 11 and d.day == 1:
            return "All Saints' Day"
        elif d.month == 12 and d.day == 24:
            return "Christmas Eve"
        elif d.month == 12 and d.day == 25:
            return "Christmas Day"
        elif d.month == 12 and d.day == 26:
            return "Second Day of Christmas"
        elif d.month == 12 and d.day == 27:
            return "Christmas Holiday"
        elif d.month == 12 and d.day == 28:
            return "Christmas Holiday"
        elif d.month == 4:
            # Easter period
            if d.weekday() == 4:  # Friday
                return "Good Friday"
            elif d.weekday() == 6:  # Sunday
                return "Easter Sunday"
            elif d.weekday() == 0:  # Monday
                return "Easter Monday"
            elif d.weekday() == 5:  # Saturday
                return "Easter Saturday"
        elif d.month == 6:
            # Pentecost
            if d.weekday() == 6:  # Sunday
                return "Whit Sunday"
            elif d.weekday() == 0:  # Monday
                return "Whit Monday"
            elif d.weekday() == 5:  # Saturday
                return "Whit Saturday"
        
        return f"Holiday ({d.strftime('%B %d')})"
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """
        Scrape weekend workday info from szakmaikamara.hu.
        The site mentions specific Saturday workdays.
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        workdays = []
        page_text = soup.get_text()
        
        # Look for specific mention of Saturday workdays
        # Pattern: "május 17-én, október 18-án, és december 13-án"
        # or "YYYY-BEN IS HÁROM ILYEN" followed by dates
        
        # Extract dates mentioned as workdays
        workday_patterns = [
            # Direct mentions like "május 17-én"
            (r"május\s+(\d{1,2})(?:-[eé]n)?(?:,|\s)", 5),
            (r"október\s+(\d{1,2})(?:-[áa]n)?(?:,|\s)", 10),
            (r"december\s+(\d{1,2})(?:-[áa]n)?(?:,|\s)", 12),
        ]
        
        # Check if context mentions these as workdays
        if "szombati munkanap" in page_text.lower() or "ledolgozós" in page_text.lower():
            for pattern, month in workday_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    day = int(match.group(1))
                    try:
                        workday_date = date(year, month, day)
                        # Verify it's a Saturday
                        if workday_date.weekday() == 5:
                            reason = self._get_workday_reason(workday_date)
                            workdays.append(WorkDay(
                                date=workday_date,
                                original_day="Saturday",
                                reason=reason
                            ))
                    except ValueError:
                        continue
        
        # Remove duplicates
        unique_workdays = []
        seen = set()
        for w in workdays:
            if w.date not in seen:
                unique_workdays.append(w)
                seen.add(w.date)
        
        return sorted(unique_workdays, key=lambda x: x.date)
    
    def _get_workday_reason(self, d: date) -> str:
        """Get reason for workday based on date."""
        if d.month == 5:
            return "Bridge day for Labour Day (May 2)"
        elif d.month == 10:
            return "Bridge day for October 23 Revolution Day"
        elif d.month == 12:
            return "Bridge day for Christmas Eve (December 24)"
        elif d.month == 8:
            return "Bridge day for St. Stephen's Day (August 20)"
        return "Transferred workday"

