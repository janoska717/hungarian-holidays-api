import re
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.models import Holiday, WorkDay
from .base import BaseScraper


class UnnepnapokScraper(BaseScraper):
    """Scraper for unnepnapok.com (Hungary) holidays and Saturday workdays."""

    name = "Unnepnapok.com"

    # Holidays list
    base_url = "https://unnepnapok.com/munkaszuneti-napok-unnepek-{year}-magyarorszag/"

    # Saturday workdays list
    workdays_url = "https://unnepnapok.com/szombati-munkanapok-{year}/"

    min_year_offset = -10
    max_year_offset = 10

    MONTH_MAP = {
        "januar": 1,
        "január": 1,
        "februar": 2,
        "február": 2,
        "marcius": 3,
        "március": 3,
        "aprilis": 4,
        "április": 4,
        "majus": 5,
        "május": 5,
        "junius": 6,
        "június": 6,
        "julius": 7,
        "július": 7,
        "augusztus": 8,
        "szeptember": 9,
        "oktober": 10,
        "október": 10,
        "november": 11,
        "december": 12,
    }

    def get_url(self, year: int) -> str:
        return self.base_url.format(year=year)

    def _fetch_soup(self, url: str) -> Optional[BeautifulSoup]:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except httpx.HTTPError as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _parse_date_line(self, line: str) -> Optional[tuple[int, date, str]]:
        """Parse lines like: '2026. január 1. – csütörtök – Újév'"""
        line = " ".join(line.strip().split())
        if not line:
            return None

        # Try multiple patterns to be more flexible
        # Pattern 1: YYYY. month DD. – dayname – title
        match = re.match(
            r"^(\d{4})\.\s*([\wáéíóöőúüű]+)\.?\s+(\d{1,2})\.\s*[–\-—]\s*.+?\s*[–\-—]\s*(.+)$",
            line,
            flags=re.IGNORECASE,
        )
        
        # Pattern 2: YYYY. month DD. – title (no day name)
        if not match:
            match = re.match(
                r"^(\d{4})\.\s*([\wáéíóöőúüű]+)\.?\s+(\d{1,2})\.\s*[–\-—]\s*(.+)$",
                line,
                flags=re.IGNORECASE,
            )
        
        if not match:
            return None

        year_str, month_str, day_str = match.group(1), match.group(2), match.group(3)
        title = match.group(4).strip()
        
        # Clean up title - remove day names at the start
        title = re.sub(r"^(hétfő|kedd|szerda|csütörtök|péntek|szombat|vasárnap)\s*[–\-—]\s*", "", title, flags=re.IGNORECASE).strip()
        
        month_key = month_str.strip().lower().rstrip(".")
        month = self.MONTH_MAP.get(month_key)
        if not month:
            # Sometimes month has trailing punctuation
            month = self.MONTH_MAP.get(re.sub(r"[^\wáéíóöőúüű]", "", month_key))
        if not month:
            return None

        try:
            parsed_date = date(int(year_str), month, int(day_str))
        except ValueError:
            return None

        return int(year_str), parsed_date, title

    def scrape_holidays(self, year: int) -> list[Holiday]:
        soup = self.fetch_page(year)
        if not soup:
            return []

        holidays: list[Holiday] = []
        seen: set[date] = set()

        # Scan all lines and take those matching the requested year
        for raw_line in soup.get_text("\n").splitlines():
            parsed = self._parse_date_line(raw_line)
            if not parsed:
                continue

            parsed_year, parsed_date, title = parsed
            if parsed_year != year:
                continue

            title_lower = title.lower()
            # Skip transferred workdays in holiday list
            if "munkanap" in title_lower:
                continue

            if parsed_date in seen:
                continue

            holidays.append(
                Holiday(
                    date=parsed_date,
                    name=title,
                    name_en=title,
                    is_national=True,
                )
            )
            seen.add(parsed_date)

        return sorted(holidays, key=lambda h: h.date)

    def scrape_weekend_workdays(self, year: int) -> list[WorkDay]:
        url = self.workdays_url.format(year=year)
        soup = self._fetch_soup(url)
        if not soup:
            return []

        workdays: list[WorkDay] = []
        seen: set[date] = set()

        for raw_line in soup.get_text("\n").splitlines():
            parsed = self._parse_date_line(raw_line)
            if not parsed:
                continue

            parsed_year, parsed_date, title = parsed
            if parsed_year != year:
                continue

            if parsed_date.weekday() < 5:
                continue

            if parsed_date in seen:
                continue

            # Extract reason from parentheses or "helyett" pattern
            reason = title
            
            # Try parentheses first: "munkanap (január 2. péntek helyett)"
            paren_match = re.search(r"\(([^)]+)\)", title)
            if paren_match:
                reason = paren_match.group(1).strip()
            else:
                # Try "X helyett" pattern
                helyett_match = re.search(r"helyett", title, re.IGNORECASE)
                if helyett_match:
                    # Extract the date part before "helyett"
                    before_helyett = title[:helyett_match.start()].strip()
                    # Clean up "munkanap" and other noise
                    reason = re.sub(r"^(munkanap|szombati\s+munkanap)[,\s]*", "", before_helyett, flags=re.IGNORECASE).strip()
                    if reason:
                        reason = f"{reason} helyett"
            
            # Clean title noise
            reason = re.sub(r"^(munkanap|szombati\s+munkanap)[,\s\-–—]*", "", reason, flags=re.IGNORECASE).strip()
            if not reason:
                reason = "Áthelyezett munkanap"

            workdays.append(
                WorkDay(
                    date=parsed_date,
                    original_day="Saturday" if parsed_date.weekday() == 5 else "Sunday",
                    reason=reason,
                )
            )
            seen.add(parsed_date)

        return sorted(workdays, key=lambda w: w.date)
