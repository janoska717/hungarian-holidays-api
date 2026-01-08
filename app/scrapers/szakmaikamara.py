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
        Parses the structured list of munkaszüneti napok and pihenőnapok.
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        holidays = []
        page_text = soup.get_text()
        seen_dates = set()
        
        # Build month pattern
        month_pattern = "|".join(self.MONTH_MAP.keys())
        day_pattern = "hétfő|kedd|szerda|csütörtök|péntek|szombat|vasárnap"
        
        # First, identify Saturday workdays to exclude them
        saturday_workdays = set()
        workday_pattern = rf"({month_pattern})\s+(\d{{1,2}})[\.,]?\s*szombat.*?munkanap"
        for match in re.finditer(workday_pattern, page_text, re.IGNORECASE):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            month = self.MONTH_MAP.get(month_name)
            if month:
                try:
                    saturday_workdays.add(date(year, month, day))
                except ValueError:
                    pass
        
        # Pattern 1: Standard format "január 1., csütörtök" or "május 1., péntek"
        # Matches lines like "január 1., csütörtök" or "április 3., péntek (nagypéntek)"
        # Exclude szombat entries that are followed by "munkanap"
        standard_pattern = rf"({month_pattern})\s+(\d{{1,2}})[\.,]\s*({day_pattern})"
        
        for match in re.finditer(standard_pattern, page_text, re.IGNORECASE):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            day_name = match.group(3).lower() if match.group(3) else None
            month = self.MONTH_MAP.get(month_name)
            
            if month:
                try:
                    holiday_date = date(year, month, day)
                    # Skip if it's a Saturday workday
                    if holiday_date in saturday_workdays:
                        continue
                    # Skip if it's szombat and could be a workday (check context)
                    if day_name == "szombat":
                        # Check if "munkanap" appears nearby in context
                        match_end = match.end()
                        context_after = page_text[match_end:match_end + 50].lower()
                        if "munkanap" in context_after:
                            continue
                    # Also skip if it's a pihenőnap (bridge day) - those are handled separately
                    match_end = match.end()
                    context_after = page_text[match_end:match_end + 30].lower()
                    if "pihenőnap" in context_after:
                        continue
                    if holiday_date not in seen_dates:
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
        
        # Pattern 2: Combined format "december 25., péntek és december 26., szombat"
        combined_pattern = rf"({month_pattern})\s+(\d{{1,2}})[\.,]?\s*({day_pattern})?\s+és\s+({month_pattern})\s+(\d{{1,2}})[\.,]?\s*({day_pattern})?"
        
        for match in re.finditer(combined_pattern, page_text, re.IGNORECASE):
            for i, (month_idx, day_idx) in enumerate([(1, 2), (4, 5)]):
                month_name = match.group(month_idx).lower()
                day = int(match.group(day_idx))
                month = self.MONTH_MAP.get(month_name)
                
                if month:
                    try:
                        holiday_date = date(year, month, day)
                        if holiday_date not in seen_dates:
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
        
        # Pattern 3: Full date format "2026. január 2., péntek pihenőnap"
        full_date_pattern = rf"{year}\.\s*({month_pattern})\s+(\d{{1,2}})[\.,]?\s*(?:,?\s*)?({day_pattern})?\s*pihenőnap"
        
        for match in re.finditer(full_date_pattern, page_text, re.IGNORECASE):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            month = self.MONTH_MAP.get(month_name)
            
            if month:
                try:
                    holiday_date = date(year, month, day)
                    if holiday_date not in seen_dates:
                        specific_name = self._get_bridge_day_name(holiday_date)
                        holidays.append(Holiday(
                            date=holiday_date,
                            name=specific_name,
                            name_en=specific_name,
                            is_national=False  # Bridge days are not national holidays
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
        elif d.month == 5 or d.month == 6:
            # Pentecost (can be in May or June)
            if d.weekday() == 6:  # Sunday
                return "Whit Sunday"
            elif d.weekday() == 0:  # Monday
                return "Whit Monday"
            elif d.weekday() == 5:  # Saturday
                return "Whit Saturday"
        
        return f"Holiday ({d.strftime('%B %d')})"
    
    def _get_bridge_day_name(self, d: date) -> str:
        """Get name for bridge days (pihenőnapok)."""
        if d.month == 1 and d.day == 2:
            return "Bridge Day (New Year)"
        elif d.month == 8 and d.day == 21:
            return "Bridge Day (St. Stephen's Day)"
        elif d.month == 12 and d.day == 24:
            return "Christmas Eve (Bridge Day)"
        return f"Bridge Day ({d.strftime('%B %d')})"
    
    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        """
        Scrape weekend workday info from szakmaikamara.hu.
        Parses the structured list of Saturday workdays (szombati munkanapok).
        """
        soup = self.fetch_page(year)
        if not soup:
            return []
        
        workdays = []
        page_text = soup.get_text()
        seen_dates = set()
        
        # Build month pattern
        full_month_pattern = "|".join(self.MONTH_MAP.keys())
        
        # Pattern 1: Full format "2026. január 10. szombat munkanap"
        # or "2026. január 10., szombat munkanap"
        full_workday_pattern = rf"{year}\.\s*({full_month_pattern})\s+(\d{{1,2}})[\.,]?\s*(?:,?\s*)?szombat\s+munkanap"
        
        for match in re.finditer(full_workday_pattern, page_text, re.IGNORECASE):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            month = self.MONTH_MAP.get(month_name)
            
            if month:
                try:
                    workday_date = date(year, month, day)
                    if workday_date not in seen_dates and workday_date.weekday() == 5:  # Verify Saturday
                        reason = self._get_workday_reason(workday_date)
                        workdays.append(WorkDay(
                            date=workday_date,
                            original_day="Saturday",
                            reason=reason
                        ))
                        seen_dates.add(workday_date)
                except ValueError:
                    continue
        
        # Pattern 2: Inline format "január 10-én, augusztus 8-án és december 12-én"
        # when followed by context about workdays
        month_pattern = "|".join(self.MONTH_MAP.keys())
        inline_dates_pattern = rf"({month_pattern})\s+(\d{{1,2}})-[éáa]n"
        
        # Check if we're in a context talking about workdays (near "dolgozni kell" or similar)
        if "dolgozni kell" in page_text.lower() or "szombati" in page_text.lower():
            for match in re.finditer(inline_dates_pattern, page_text, re.IGNORECASE):
                month_name = match.group(1).lower()
                day = int(match.group(2))
                month = self.MONTH_MAP.get(month_name)
                
                if month:
                    try:
                        workday_date = date(year, month, day)
                        if workday_date not in seen_dates and workday_date.weekday() == 5:  # Verify Saturday
                            reason = self._get_workday_reason(workday_date)
                            workdays.append(WorkDay(
                                date=workday_date,
                                original_day="Saturday",
                                reason=reason
                            ))
                            seen_dates.add(workday_date)
                    except ValueError:
                        continue
        
        # Pattern 3: Table format "január 10. szombat | munkanap" or "áthelyezett munkanap"
        table_month_pattern = "|".join(self.MONTH_MAP.keys())
        table_pattern = rf"({table_month_pattern})\s+(\d{{1,2}})[\.,]?\s*szombat.*?(?:munkanap|áthelyezett)"
        
        for match in re.finditer(table_pattern, page_text, re.IGNORECASE):
            month_name = match.group(1).lower()
            day = int(match.group(2))
            month = self.MONTH_MAP.get(month_name)
            
            if month:
                try:
                    workday_date = date(year, month, day)
                    if workday_date not in seen_dates and workday_date.weekday() == 5:  # Verify Saturday
                        reason = self._get_workday_reason(workday_date)
                        workdays.append(WorkDay(
                            date=workday_date,
                            original_day="Saturday",
                            reason=reason
                        ))
                        seen_dates.add(workday_date)
                except ValueError:
                    continue
        
        return sorted(workdays, key=lambda x: x.date)
    
    def _get_workday_reason(self, d: date) -> str:
        """Get reason for workday based on date."""
        if d.month == 1:
            return "Bridge day for New Year (January 2)"
        elif d.month == 5:
            return "Bridge day for Labour Day (May 2)"
        elif d.month == 8:
            return "Bridge day for St. Stephen's Day (August 21)"
        elif d.month == 10:
            return "Bridge day for October 23 Revolution Day"
        elif d.month == 12:
            return "Bridge day for Christmas Eve (December 24)"
        return "Transferred workday"

