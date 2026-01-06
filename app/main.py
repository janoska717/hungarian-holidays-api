from datetime import date, datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models import Holiday, WorkDay, HolidayResponse
from app.services import HolidayService

app = FastAPI(
    title="Hungarian Holidays API",
    description="""
    REST API for Hungarian public holidays and weekend workdays (munkanap-áthelyezés).
    
    Data is obtained via web scraping from multiple sources, with automatic selection
    of the most appropriate source based on the requested year.
    
    ## Features
    
    - **Public Holidays**: All official Hungarian public holidays
    - **Weekend Workdays**: Saturdays/Sundays that are designated as working days
    - **Multi-source**: Aggregates data from multiple reliable sources
    - **Year Selection**: Request any year, with smart source selection
    - **Caching**: Results are cached to minimize scraping
    
    ## Sources
    
    **Hungarian Sources (Primary):**
    - MFA.gov.hu - Official Hungarian Ministry of Foreign Affairs
    - PublicHolidays.hu - Comprehensive Hungarian holiday list
    - DailyNewsHungary.com - Weekend workday announcements
    
    **International Sources (Fallback):**
    - TimeAndDate.com
    - OfficeHolidays.com
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
holiday_service = HolidayService()


@app.get("/", tags=["Root"])
async def root():
    """API root - provides basic info and links."""
    return {
        "name": "Hungarian Holidays API",
        "version": "1.0.0",
        "description": "REST API for Hungarian public holidays and weekend workdays",
        "endpoints": {
            "holidays": "/holidays",
            "holidays_by_year": "/holidays/{year}",
            "workdays": "/workdays",
            "workdays_by_year": "/workdays/{year}",
            "check_date": "/check/{date}",
            "documentation": "/docs",
        },
        "current_year": datetime.now().year,
    }


@app.get("/holidays", response_model=HolidayResponse, tags=["Holidays"])
async def get_holidays(
    year: Optional[int] = Query(
        default=None,
        description="Year to get holidays for. Defaults to current year.",
        ge=2000,
        le=2100,
    )
):
    """
    Get Hungarian public holidays and weekend workdays for a specific year.
    
    If no year is provided, returns data for the current year.
    The API automatically selects the best data source based on the requested year.
    """
    try:
        return holiday_service.get_holidays(year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holidays: {str(e)}")


@app.get("/holidays/{year}", response_model=HolidayResponse, tags=["Holidays"])
async def get_holidays_by_year(year: int):
    """
    Get Hungarian public holidays and weekend workdays for a specific year.
    
    The API automatically selects the best data source based on the requested year.
    """
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Year must be between 2000 and 2100")
    
    try:
        return holiday_service.get_holidays(year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holidays: {str(e)}")


@app.get("/holidays-only", response_model=list[Holiday], tags=["Holidays"])
async def get_holidays_list(
    year: Optional[int] = Query(
        default=None,
        description="Year to get holidays for. Defaults to current year.",
        ge=2000,
        le=2100,
    )
):
    """Get only the list of public holidays (without workdays or metadata)."""
    try:
        return holiday_service.get_holidays_only(year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching holidays: {str(e)}")


@app.get("/workdays", response_model=list[WorkDay], tags=["Weekend Workdays"])
async def get_weekend_workdays(
    year: Optional[int] = Query(
        default=None,
        description="Year to get weekend workdays for. Defaults to current year.",
        ge=2000,
        le=2100,
    )
):
    """
    Get weekend workdays (munkanap-áthelyezés) for a specific year.
    
    These are Saturdays or Sundays that are designated as working days,
    typically to create longer holiday periods.
    """
    try:
        return holiday_service.get_weekend_workdays_only(year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workdays: {str(e)}")


@app.get("/workdays/{year}", response_model=list[WorkDay], tags=["Weekend Workdays"])
async def get_weekend_workdays_by_year(year: int):
    """Get weekend workdays for a specific year."""
    if year < 2000 or year > 2100:
        raise HTTPException(status_code=400, detail="Year must be between 2000 and 2100")
    
    try:
        return holiday_service.get_weekend_workdays_only(year)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching workdays: {str(e)}")


@app.get("/check/{check_date}", tags=["Date Check"])
async def check_date(check_date: date):
    """
    Check if a specific date is a holiday or weekend workday.
    
    Date format: YYYY-MM-DD (e.g., 2025-03-15)
    """
    try:
        is_holiday = holiday_service.is_holiday(check_date)
        is_workday = holiday_service.is_weekend_workday(check_date)
        is_weekend = check_date.weekday() >= 5
        
        # Get holiday name if it's a holiday
        holiday_name = None
        if is_holiday:
            holidays = holiday_service.get_holidays_only(check_date.year)
            for h in holidays:
                if h.date == check_date:
                    holiday_name = h.name
                    break
        
        return {
            "date": check_date.isoformat(),
            "day_of_week": check_date.strftime("%A"),
            "is_holiday": is_holiday,
            "holiday_name": holiday_name,
            "is_weekend": is_weekend,
            "is_weekend_workday": is_workday,
            "is_working_day": (not is_weekend and not is_holiday) or is_workday,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking date: {str(e)}")


@app.post("/cache/clear", tags=["Admin"])
async def clear_cache():
    """Clear the cache to force fresh data scraping on next request."""
    holiday_service.clear_cache()
    return {"message": "Cache cleared successfully"}


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

