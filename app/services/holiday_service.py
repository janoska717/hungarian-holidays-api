from datetime import datetime, date
from typing import Optional
import os
from cachetools import TTLCache

from app.models import Holiday, WorkDay, HolidayResponse, SourceInfo
from app.scrapers import (
    BaseScraper,
    MfaGovHuScraper,
    PublicHolidaysScraper,
    DailyNewsHungaryScraper,
    TimeAndDateScraper,
    OfficeHolidaysScraper,
    PontosIdoScraper,
    SzakmaiKamaraScraper,
)


class HolidayService:
    """Service for fetching Hungarian holidays from multiple sources."""
    
    def __init__(self):
        # Initialize all scrapers - ordered by preference
        # Hungarian sources are prioritized for accurate munkanap-áthelyezés data
        self.holiday_scrapers: list[BaseScraper] = [
            PontosIdoScraper(),          # Hungarian - excellent structured data with Dec 24
            MfaGovHuScraper(),           # Hungarian official - includes bridge days
            SzakmaiKamaraScraper(),      # Hungarian - good long weekend info
            PublicHolidaysScraper(),     # PublicHolidays.hu - best structured data
            TimeAndDateScraper(),         # International backup
            OfficeHolidaysScraper(),      # International fallback
        ]
        
        # Scrapers specifically for weekend workdays (szombati munkanapok)
        # Hungarian sources have the official workday rearrangement info
        self.workday_scrapers: list[BaseScraper] = [
            PontosIdoScraper(),          # Hungarian - has clear munkanap info
            MfaGovHuScraper(),           # Official government info for workdays
            SzakmaiKamaraScraper(),      # Hungarian - mentions specific Saturday workdays
            DailyNewsHungaryScraper(),   # News articles about workday announcements
        ]

        # PublicHolidays.hu frequently blocks Azure/cloud IP ranges (403) and is not a primary
        # source for "áthelyezett munkanap" data. Keep it disabled for workdays by default.
        if (os.getenv("INCLUDE_PUBLICHOLIDAYS_FOR_WORKDAYS") or "").strip().lower() in {"1", "true", "yes"}:
            self.workday_scrapers.append(PublicHolidaysScraper())
        
        # Cache results for 1 hour to avoid excessive scraping
        self._cache: TTLCache = TTLCache(maxsize=100, ttl=3600)
    
    def _get_scrapers_for_year(self, scrapers: list[BaseScraper], year: int) -> list[BaseScraper]:
        """Get scrapers sorted by suitability for the given year."""
        return sorted(
            scrapers,
            key=lambda s: (s.get_year_distance(year), scrapers.index(s))
        )
    
    def get_holidays(self, year: Optional[int] = None) -> HolidayResponse:
        """
        Get Hungarian holidays and weekend workdays for the specified year.
        
        Args:
            year: The year to get holidays for. Defaults to current year.
            
        Returns:
            HolidayResponse with holidays, weekend workdays, and source info.
        """
        if year is None:
            year = datetime.now().year
        
        # Check cache first
        cache_key = f"holidays_{year}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Scrape holidays
        holidays, holiday_source = self._scrape_holidays(year)
        
        # Scrape weekend workdays (from multiple sources and combine)
        workdays = self._scrape_workdays(year)
        
        # Create source info (use holiday source as primary)
        if holiday_source is None:
            holiday_source = SourceInfo(
                name="None",
                url="",
                year_coverage=year,
                scraped_at=datetime.now().isoformat()
            )
        
        response = HolidayResponse(
            year=year,
            holidays=holidays,
            weekend_workdays=workdays,
            source=holiday_source,
            total_holidays=len(holidays),
            total_weekend_workdays=len(workdays)
        )
        
        # Cache the result
        self._cache[cache_key] = response
        
        return response
    
    def _scrape_holidays(self, year: int) -> tuple[list[Holiday], Optional[SourceInfo]]:
        """Scrape holidays from available sources."""
        scrapers = self._get_scrapers_for_year(self.holiday_scrapers, year)
        
        for scraper in scrapers:
            try:
                print(f"Trying {scraper.name} for holidays in year {year}...")
                holidays, _, source = scraper.scrape(year)
                
                if holidays:
                    print(f"Success! Got {len(holidays)} holidays from {scraper.name}")
                    return holidays, source
                else:
                    print(f"No holidays found from {scraper.name}")
                    
            except Exception as e:
                print(f"Error with {scraper.name}: {e}")
                continue
        
        return [], None
    
    def _scrape_workdays(self, year: int) -> list[WorkDay]:
        """Scrape weekend workdays from all available sources and combine."""
        all_workdays: dict[date, WorkDay] = {}
        scrapers = self._get_scrapers_for_year(self.workday_scrapers, year)
        
        for scraper in scrapers:
            try:
                print(f"Trying {scraper.name} for weekend workdays in year {year}...")
                workdays = scraper.scrape_weekend_workdays(year)
                
                for workday in workdays:
                    # Only add if not already present (prefer earlier sources)
                    if workday.date not in all_workdays:
                        all_workdays[workday.date] = workday
                        print(f"Found workday {workday.date} from {scraper.name}")
                    
            except Exception as e:
                print(f"Error with {scraper.name} for workdays: {e}")
                continue
        
        return sorted(all_workdays.values(), key=lambda x: x.date)
    
    def get_holidays_only(self, year: Optional[int] = None) -> list[Holiday]:
        """Get only the holidays list."""
        response = self.get_holidays(year)
        return response.holidays
    
    def get_weekend_workdays_only(self, year: Optional[int] = None) -> list[WorkDay]:
        """Get only the weekend workdays list."""
        response = self.get_holidays(year)
        return response.weekend_workdays
    
    def is_holiday(self, check_date: date) -> bool:
        """Check if a specific date is a holiday."""
        holidays = self.get_holidays_only(check_date.year)
        return any(h.date == check_date for h in holidays)
    
    def is_weekend_workday(self, check_date: date) -> bool:
        """Check if a specific date is a weekend workday."""
        workdays = self.get_weekend_workdays_only(check_date.year)
        return any(w.date == check_date for w in workdays)
    
    def clear_cache(self):
        """Clear the cache to force fresh scraping."""
        self._cache.clear()
