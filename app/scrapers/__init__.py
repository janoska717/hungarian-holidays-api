from .base import BaseScraper
from .mfa_gov import MfaGovHuScraper
from .dailynewshungary import DailyNewsHungaryScraper
from .timeanddate import TimeAndDateScraper
from .officeholidays import OfficeHolidaysScraper
from .pontosido import PontosIdoScraper
from .szakmaikamara import SzakmaiKamaraScraper
from .unnepnapok import UnnepnapokScraper

__all__ = [
    "BaseScraper",
    "MfaGovHuScraper",
    "DailyNewsHungaryScraper",
    "TimeAndDateScraper", 
    "OfficeHolidaysScraper",
    "PontosIdoScraper",
    "SzakmaiKamaraScraper",
    "UnnepnapokScraper",
]
