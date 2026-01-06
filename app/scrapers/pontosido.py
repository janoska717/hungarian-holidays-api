import re
from datetime import date
from typing import Optional
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class PontosIdoScraper(BaseScraper):
    """
    Scraper for pontosido.com - excellent Hungarian source for munkaszüneti napok.
    Has well-structured data with clear dates, types, and rearrangement info.
    """
    
    name = "PontosIdo.com"
    base_url = "https://www.pontosido.com/munkaszuneti-napok/"
    min_year_offset = -3
    max_year_offset = 1
    
    # Hungarian month names
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
    
    # Hungarian day names
    DAY_MAP = {
        "hétfő": 0, "kedd": 1, "szerda": 2, "csütörtök": 3,
        "péntek": 4, "szombat": 5, "vasárnap": 6,
    }
    
    DAY_NAMES = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday",
        3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    # Hungarian holiday names to English
    HOLIDAY_NAMES_EN = {
        "újév": "New Year's Day",
        "új év": "New Year's Day",
        "1848-as forradalom": "1848 Revolution Memorial Day",
        "nemzeti ünnep": "National Day",
        "nagypéntek": "Good Friday",
        "húsvét": "Easter",
        "húsvéthétfő": "Easter Monday",
        "húsvét vasárnap": "Easter Sunday",
        "húsvét hétfő": "Easter Monday",
        "munka ünnepe": "Labour Day",
        "pünkösd": "Whit",
        "pünkösdhétfő": "Whit Monday",
        "pünkösd vasárnap": "Whit Sunday",
        "pünkösd hétfő": "Whit Monday",
        "államalapítás": "St. Stephen's Day",
        "szent istván": "St. Stephen's Day",
        "1956-os forradalom": "1956 Revolution Memorial Day",
        "mindenszentek": "All Saints' Day",
        "karácsony": "Christmas",
        "szenteste": "Christmas Eve",
        "szilveszter": "New Year's Eve",
    }
    
    def get_url(self, year: int) -> str:
        """This page has all years' info."""
        return self.base_url
    
    def _get_english_name(self, hungarian_name: str) -> str:
        """Get English name for a Hungarian holiday."""
        hungarian_lower = hungarian_name.lower()
        for hu_key, en_name in self.HOLIDAY_NAMES_EN.items():
            if hu_key in hungarian_lower:
                return en_name
        return hungarian_name
    
    def _parse_hungarian_date(self, text: str) -> Optional[tuple[int, int, int]]:
        """
        Parse date like "2025. december 24. szerda" or "2025. január 1. szerda"
        Returns (year, month, day) tuple or None.
        """
        # Pattern: YYYY. month DD. dayname
        pattern = r"(\d{4})\.\s*(\w+)\s+(\d{1,2})\.\s*(\w+)"
        match = re.match(pattern, text.strip())
        if match:
            year_str, month_str, day_str, _ = match.groups()
            month = self.MONTH_MAP.get(month_str.lower())
            if month:
                try:
                    return (int(year_str), month, int(day_str))
                except ValueError:
                    pass
        return None
    
    def scrape_holidays(self, year: int) -> list[Holiday]:
        """Scrape Hungarian holidays from pontosido.com."""
        soup = self.fetch_page(year)
        if not soup:
            # Fall back to known 2025 holidays
            if year == 2025:
                return self._get_2025_holidays()
            return []
        
        holidays = []
        seen_dates = set()
        
        # Find all text content looking for year-specific patterns
        # The site has a structured format with dates and descriptions
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for date line like "2025. december 24. szerda"
            date_match = re.match(rf"({year})\.\s*(\w+)\s+(\d{{1,2}})\.\s*(\w+)", line)
            if date_match:
                year_str, month_str, day_str, day_name = date_match.groups()
                month = self.MONTH_MAP.get(month_str.lower())
                
                if month:
                    try:
                        holiday_date = date(int(year_str), month, int(day_str))
                        
                        # Get the next line which should be the description
                        desc_line = ""
                        if i + 1 < len(lines):
                            desc_line = lines[i + 1].strip()
                        
                        # Check if it's a holiday/off day (not a work day)
                        desc_lower = desc_line.lower()
                        
                        is_holiday = "ünnepnap" in desc_lower
                        is_rest_day = "pihenőnap" in desc_lower
                        is_workday = "munkanap" in desc_lower and "áthelyezett munkanap" in desc_lower
                        
                        if (is_holiday or is_rest_day) and not is_workday:
                            if holiday_date not in seen_dates:
                                # Extract the holiday name from description
                                name = desc_line
                                # Clean up the name
                                name = re.sub(r"Ünnepnap,?\s*", "", name, flags=re.IGNORECASE)
                                name = re.sub(r"Pihenőnap,?\s*", "", name, flags=re.IGNORECASE)
                                name = re.sub(r"\(\d+\s*napos\s*hétvége\)", "", name)
                                name = re.sub(r"áthelyezett pihenőnap", "Áthelyezett pihenőnap", name, flags=re.IGNORECASE)
                                name = name.strip()
                                
                                if not name:
                                    name = "Pihenőnap"
                                
                                english_name = self._get_english_name(name)
                                
                                holidays.append(Holiday(
                                    date=holiday_date,
                                    name=name,
                                    name_en=english_name,
                                    is_national=is_holiday
                                ))
                                seen_dates.add(holiday_date)
                        
                    except ValueError:
                        pass
            i += 1
        
        # Add known 2025 holidays that might be missed by scraping
        if year == 2025:
            known_holidays = self._get_2025_holidays()
            for kh in known_holidays:
                if kh.date not in seen_dates:
                    holidays.append(kh)
                    seen_dates.add(kh.date)
        
        return sorted(holidays, key=lambda x: x.date)
    
    def _get_2025_holidays(self) -> list[Holiday]:
        """
        Return known 2025 Hungarian holidays based on official sources.
        This ensures complete holiday data even if scraping misses some.
        """
        return [
            Holiday(date=date(2025, 1, 1), name="Újév", name_en="New Year's Day", is_national=True),
            Holiday(date=date(2025, 3, 15), name="1848-as forradalom ünnepe", name_en="1848 Revolution Memorial Day", is_national=True),
            Holiday(date=date(2025, 4, 18), name="Nagypéntek", name_en="Good Friday", is_national=True),
            Holiday(date=date(2025, 4, 20), name="Húsvét vasárnap", name_en="Easter Sunday", is_national=True),
            Holiday(date=date(2025, 4, 21), name="Húsvét hétfő", name_en="Easter Monday", is_national=True),
            Holiday(date=date(2025, 5, 1), name="Munka ünnepe", name_en="Labour Day", is_national=True),
            Holiday(date=date(2025, 5, 2), name="Áthelyezett pihenőnap", name_en="Bridge Day (Labour Day)", is_national=False),
            Holiday(date=date(2025, 6, 8), name="Pünkösd vasárnap", name_en="Whit Sunday", is_national=True),
            Holiday(date=date(2025, 6, 9), name="Pünkösd hétfő", name_en="Whit Monday", is_national=True),
            Holiday(date=date(2025, 8, 20), name="Szent István nap", name_en="St. Stephen's Day", is_national=True),
            Holiday(date=date(2025, 10, 23), name="1956-os forradalom ünnepe", name_en="1956 Revolution Memorial Day", is_national=True),
            Holiday(date=date(2025, 10, 24), name="Áthelyezett pihenőnap", name_en="Bridge Day (October Revolution)", is_national=False),
            Holiday(date=date(2025, 11, 1), name="Mindenszentek", name_en="All Saints' Day", is_national=True),
            Holiday(date=date(2025, 12, 24), name="Szenteste", name_en="Christmas Eve", is_national=False),
            Holiday(date=date(2025, 12, 25), name="Karácsony", name_en="Christmas Day", is_national=True),
            Holiday(date=date(2025, 12, 26), name="Karácsony másnapja", name_en="Second Day of Christmas", is_national=True),
        ]
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """Scrape weekend workdays (szombati munkanapok) from pontosido.com."""
        soup = self.fetch_page(year)
        if not soup:
            # Fall back to known 2025 workdays
            if year == 2025:
                return self._get_2025_workdays()
            return []
        
        workdays = []
        seen_dates = set()
        
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for date line
            date_match = re.match(rf"({year})\.\s*(\w+)\s+(\d{{1,2}})\.\s*(\w+)", line)
            if date_match:
                year_str, month_str, day_str, day_name = date_match.groups()
                month = self.MONTH_MAP.get(month_str.lower())
                
                if month:
                    try:
                        workday_date = date(int(year_str), month, int(day_str))
                        
                        # Get the next line for description
                        desc_line = ""
                        if i + 1 < len(lines):
                            desc_line = lines[i + 1].strip()
                        
                        # Check if it's a workday (áthelyezett munkanap)
                        if "munkanap" in desc_line.lower() and "áthelyezett" in desc_line.lower():
                            if workday_date not in seen_dates and workday_date.weekday() >= 5:
                                day_name_en = self.DAY_NAMES.get(workday_date.weekday(), "Saturday")
                                workdays.append(WorkDay(
                                    date=workday_date,
                                    original_day=day_name_en,
                                    reason="Áthelyezett munkanap (Transferred workday)"
                                ))
                                seen_dates.add(workday_date)
                        
                    except ValueError:
                        pass
            i += 1
        
        # Ensure 2025 workdays are always included
        if year == 2025:
            known_workdays = self._get_2025_workdays()
            for kw in known_workdays:
                if kw.date not in seen_dates:
                    workdays.append(kw)
                    seen_dates.add(kw.date)
        
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

