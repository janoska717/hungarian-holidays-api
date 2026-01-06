import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class MfaGovHuScraper(BaseScraper):
    """
    Scraper for official Hungarian government source (Ministry of Foreign Affairs).
    https://almati.mfa.gov.hu/hu/hu-uennepnapok
    
    This is an official government source that lists Hungarian holidays.
    """
    
    name = "MFA.gov.hu (Official)"
    base_url = "https://almati.mfa.gov.hu/hu/hu-uennepnapok"
    min_year_offset = -1
    max_year_offset = 1
    
    # Hungarian month names mapping
    MONTH_MAP = {
        "január": 1, "jan": 1,
        "február": 2, "feb": 2,
        "március": 3, "már": 3, "marc": 3,
        "április": 4, "ápr": 4, "apr": 4,
        "május": 5, "máj": 5, "maj": 5,
        "június": 6, "jún": 6, "jun": 6,
        "július": 7, "júl": 7, "jul": 7,
        "augusztus": 8, "aug": 8,
        "szeptember": 9, "szept": 9, "sep": 9,
        "október": 10, "okt": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    
    # Hungarian holiday names to English
    HOLIDAY_NAMES_EN = {
        "új év": "New Year's Day",
        "újév": "New Year's Day",
        "1848-as forradalom": "1848 Revolution Memorial Day",
        "nemzeti ünnep": "National Day",
        "nagypéntek": "Good Friday",
        "húsvét": "Easter Monday",
        "húsvéthétfő": "Easter Monday",
        "munka ünnepe": "Labour Day",
        "pünkösd": "Whit Monday",
        "pünkösdhétfő": "Whit Monday",
        "államalapítás": "St. Stephen's Day",
        "szent istván": "St. Stephen's Day",
        "1956-os forradalom": "1956 Revolution Memorial Day",
        "mindenszentek": "All Saints' Day",
        "karácsony": "Christmas",
    }
    
    DAY_NAMES = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    def get_url(self, year: int) -> str:
        """This page has current year info."""
        return self.base_url
    
    def _get_english_name(self, hungarian_name: str) -> str:
        """Get English name for a Hungarian holiday."""
        hungarian_lower = hungarian_name.lower()
        for hu_key, en_name in self.HOLIDAY_NAMES_EN.items():
            if hu_key in hungarian_lower:
                return en_name
        return hungarian_name
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape Hungarian holidays from the official MFA website."""
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        
        # Get the page text
        page_text = soup.get_text()
        
        # Split into lines and process each line
        lines = page_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Match pattern: YYYY. month DD. Holiday Name
            # e.g., "2025. január 1. Új Év – pihenőnap"
            # e.g., "2025. március 15. 1848-as forradalom és szabadságharc ünnepe"
            pattern = rf"({year})\.\s*(január|február|március|április|május|június|július|augusztus|szeptember|október|november|december)\.?\s*(\d{{1,2}})(?:-\d{{1,2}})?\.?\s+(.+?)(?:\s*–\s*pihenőnap|\s*\(\d+\s*napos|\s*$)"
            
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                try:
                    year_str, month_str, day_str, name = match.groups()
                    month = self.MONTH_MAP.get(month_str.lower())
                    
                    if month:
                        holiday_date = date(int(year_str), month, int(day_str))
                        
                        # Clean up the name
                        name = name.strip()
                        name = re.sub(r"\s*\(\d+\s*napos\s*hétvége\).*$", "", name)
                        name = re.sub(r"\s*–\s*pihenőnap.*$", "", name)
                        name = name.strip()
                        
                        # Skip Kazakh/Tajik holidays
                        if name and not any(skip in name.lower() for skip in ["kazahsztán", "kazah", "tádzsik"]):
                            english_name = self._get_english_name(name)
                            
                            holidays.append(Holiday(
                                date=holiday_date,
                                name=name,
                                name_en=english_name,
                                is_national=True
                            ))
                except (ValueError, TypeError):
                    continue
        
        # Handle Christmas date range (december 24-28)
        for line in lines:
            range_pattern = rf"({year})\.\s*december\.?\s*(\d{{1,2}})-(\d{{1,2}})\.?\s+([Kk]arácsony)"
            match = re.search(range_pattern, line)
            if match:
                year_str, start_day, end_day, name = match.groups()
                # Add Christmas Day (25) and Boxing Day (26)
                try:
                    christmas_25 = date(int(year_str), 12, 25)
                    christmas_26 = date(int(year_str), 12, 26)
                    
                    if christmas_25 not in [h.date for h in holidays]:
                        holidays.append(Holiday(
                            date=christmas_25,
                            name="Karácsony",
                            name_en="Christmas Day",
                            is_national=True
                        ))
                    if christmas_26 not in [h.date for h in holidays]:
                        holidays.append(Holiday(
                            date=christmas_26,
                            name="Karácsony másnapja",
                            name_en="Second Day of Christmas",
                            is_national=True
                        ))
                except ValueError:
                    pass
        
        # Remove duplicates based on date
        seen_dates = set()
        unique_holidays = []
        for h in holidays:
            if h.date not in seen_dates:
                seen_dates.add(h.date)
                unique_holidays.append(h)
        
        # Add known bridge days for 2025 if not already present
        if year == 2025:
            bridge_days = self._get_2025_bridge_days()
            for bd in bridge_days:
                if bd.date not in seen_dates:
                    unique_holidays.append(bd)
                    seen_dates.add(bd.date)
        
        return sorted(unique_holidays, key=lambda x: x.date)
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """
        Scrape weekend workdays from the page.
        The MFA page mentions long weekends which imply workday swaps.
        
        Based on Hungarian government decrees for 2025:
        - Saturday May 17 is a working day (for May 2 bridge day)
        - Saturday October 18 is a working day (for October 24 bridge day)  
        - Saturday December 13 is a working day (for December 24 bridge day)
        """
        soup = self.fetch_page(year)
        if not soup:
            # Fall back to known 2025 workdays if page unavailable
            if year == 2025:
                return self._get_2025_workdays()
            return []
        
        workdays = []
        page_text = soup.get_text()
        
        # Look for patterns that mention "napos hétvége" (long weekend)
        # These indicate workday swaps happened
        
        long_weekend_patterns = [
            (r"május\s*1.*?4\s*napos\s*hétvége", 5, 17, "Bridge day for Labour Day"),
            (r"október\s*23.*?4\s*napos\s*hétvége", 10, 18, "Bridge day for October 23"),
            (r"karácsony.*?5\s*napos\s*hétvége", 12, 13, "Bridge day for Christmas Eve"),
        ]
        
        for pattern, month, day, reason in long_weekend_patterns:
            if re.search(pattern, page_text, re.IGNORECASE):
                try:
                    workday_date = date(year, month, day)
                    # Verify it's a Saturday
                    if workday_date.weekday() == 5:  # Saturday
                        workdays.append(WorkDay(
                            date=workday_date,
                            original_day="Saturday",
                            reason=reason
                        ))
                except ValueError:
                    continue
        
        # If no workdays found from scraping, use known data for 2025
        if not workdays and year == 2025:
            return self._get_2025_workdays()
        
        return sorted(workdays, key=lambda x: x.date)
    
    def _get_2025_workdays(self) -> list[WorkDay]:
        """
        Return known 2025 Saturday workdays based on government decree.
        Source: Hungarian government decree for 2025 work schedule.
        """
        return [
            WorkDay(
                date=date(2025, 5, 17),
                original_day="Saturday",
                reason="Bridge day for Labour Day (May 2)",
                related_holiday=date(2025, 5, 2)
            ),
            WorkDay(
                date=date(2025, 10, 18),
                original_day="Saturday", 
                reason="Bridge day for October 23 Revolution Day",
                related_holiday=date(2025, 10, 24)
            ),
            WorkDay(
                date=date(2025, 12, 13),
                original_day="Saturday",
                reason="Bridge day for Christmas Eve (December 24)",
                related_holiday=date(2025, 12, 24)
            ),
        ]
    
    def _get_2025_bridge_days(self) -> list[Holiday]:
        """
        Return known 2025 bridge days (áthelyezett pihenőnapok).
        These are working days that become rest days due to rearrangement.
        """
        return [
            Holiday(
                date=date(2025, 5, 2),
                name="Áthelyezett pihenőnap",
                name_en="Bridge Day (Labour Day)",
                is_national=False
            ),
            Holiday(
                date=date(2025, 10, 24),
                name="Áthelyezett pihenőnap",
                name_en="Bridge Day (October Revolution)",
                is_national=False
            ),
            Holiday(
                date=date(2025, 12, 24),
                name="Szenteste (Áthelyezett pihenőnap)",
                name_en="Christmas Eve",
                is_national=False
            ),
        ]
