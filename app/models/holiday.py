from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class Holiday(BaseModel):
    """Represents a Hungarian public holiday."""
    date: date
    name: str
    name_en: Optional[str] = None
    is_national: bool = True


class WorkDay(BaseModel):
    """Represents a weekend day that is a working day (munkanap-áthelyezés)."""
    date: date
    original_day: str = Field(description="The day of week (e.g., 'Saturday')")
    reason: Optional[str] = Field(default=None, description="Reason for the workday swap")
    related_holiday: Optional[date] = Field(default=None, description="The holiday this workday is related to")


class SourceInfo(BaseModel):
    """Information about the data source used."""
    name: str
    url: str
    year_coverage: int = Field(description="The year this source covers")
    scraped_at: str


class HolidayResponse(BaseModel):
    """Response model for holiday API."""
    year: int
    holidays: list[Holiday]
    weekend_workdays: list[WorkDay]
    source: SourceInfo
    total_holidays: int
    total_weekend_workdays: int

