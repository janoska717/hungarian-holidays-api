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

        # Accept both hyphen and en-dash separators
        # groups: year, month, day, title
        match = re.match(
            r"^(\d{4})\.\s*([\wáéíóöőúüű]+)\s+(\d{1,2})\.\s*[–-]\s*[^–-]+\s*[–-]\s*(.+?)\s*$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            return None

        year_str, month_str, day_str, title = match.groups()
        month_key = month_str.strip().lower()
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

        return int(year_str), parsed_date, title.strip()

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

            # Reason is often in parentheses
            reason_match = re.search(r"\(([^)]+)\)", title)
            reason = reason_match.group(1).strip() if reason_match else title

            workdays.append(
                WorkDay(
                    date=parsed_date,
                    original_day="Saturday" if parsed_date.weekday() == 5 else "Sunday",
                    reason=reason,
                )
            )
            seen.add(parsed_date)

        return sorted(workdays, key=lambda w: w.date)
