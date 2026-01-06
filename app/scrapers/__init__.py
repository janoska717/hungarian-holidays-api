from .base import BaseScraper
from .mfa_gov import MfaGovHuScraper
from .publicholidays import PublicHolidaysScraper
from .dailynewshungary import DailyNewsHungaryScraper
from .timeanddate import TimeAndDateScraper
from .officeholidays import OfficeHolidaysScraper
from .pontosido import PontosIdoScraper
from .szakmaikamara import SzakmaiKamaraScraper

__all__ = [
    "BaseScraper",
    "MfaGovHuScraper",
    "PublicHolidaysScraper",
    "DailyNewsHungaryScraper",
    "TimeAndDateScraper", 
    "OfficeHolidaysScraper",
    "PontosIdoScraper",
    "SzakmaiKamaraScraper",
]
