# Hungarian Holidays API 🇭🇺

A Python REST API for retrieving Hungarian public holidays and weekend workdays (munkanap-áthelyezés) via web scraping from multiple Hungarian and international sources.

## Features

- **Public Holidays**: All official Hungarian public holidays (11 days)
- **Weekend Workdays**: Saturdays/Sundays designated as working days (munkanap-áthelyezés)
- **Multi-source Scraping**: Aggregates data from multiple sources with automatic fallback
- **Hungarian Sources First**: Prioritizes official Hungarian government sources
- **Smart Source Selection**: Automatically picks the best source based on requested year
- **Caching**: Results are cached to minimize scraping load
- **REST API**: Easy-to-use REST endpoints with OpenAPI documentation

## Data Sources

### Hungarian Sources (Primary)
1. **PublicHolidays.hu** - Comprehensive Hungarian holiday list with proper Hungarian names
2. **MFA.gov.hu** - Official Hungarian Ministry of Foreign Affairs ([source](https://almati.mfa.gov.hu/hu/hu-uennepnapok))
3. **DailyNewsHungary.com** - English-language Hungarian news with workday announcements

### International Sources (Fallback)
4. **TimeAndDate.com** - Wide year coverage
5. **OfficeHolidays.com** - Backup source

## Installation

1. Clone the repository:
```bash
cd hungarian-holidays-api
```

2. Create a virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

Start the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Get Holidays (Current Year)
```
GET /holidays
```

### Get Holidays for Specific Year
```
GET /holidays/{year}
GET /holidays?year=2025
```

### Get Only Holiday List
```
GET /holidays-only?year=2025
```

### Get Weekend Workdays
```
GET /workdays?year=2025
GET /workdays/{year}
```

### Check Specific Date
```
GET /check/2025-03-15
```
Returns whether the date is a holiday, weekend, or working day.

### Clear Cache
```
POST /cache/clear
```

### Health Check
```
GET /health
```

## Example Response

```json
{
  "year": 2025,
  "holidays": [
    {"date": "2025-01-01", "name": "New Year's Day", "name_en": "New Year's Day", "is_national": true},
    {"date": "2025-03-15", "name": "Revolution Day", "name_en": "Revolution Day", "is_national": true},
    {"date": "2025-04-18", "name": "Good Friday", "name_en": "Good Friday", "is_national": true},
    {"date": "2025-04-21", "name": "Easter Monday", "name_en": "Easter Monday", "is_national": true},
    {"date": "2025-05-01", "name": "Labour Day", "name_en": "Labour Day", "is_national": true},
    {"date": "2025-06-09", "name": "Whit Monday", "name_en": "Whit Monday", "is_national": true},
    {"date": "2025-08-20", "name": "Saint Stephen's Day", "name_en": "Saint Stephen's Day", "is_national": true},
    {"date": "2025-10-23", "name": "Republic Day", "name_en": "Republic Day", "is_national": true},
    {"date": "2025-11-01", "name": "All Saints' Day", "name_en": "All Saints' Day", "is_national": true},
    {"date": "2025-12-25", "name": "Christmas Day", "name_en": "Christmas Day", "is_national": true},
    {"date": "2025-12-26", "name": "2nd Day of Christmas", "name_en": "2nd Day of Christmas", "is_national": true}
  ],
  "weekend_workdays": [
    {"date": "2025-05-17", "original_day": "Saturday", "reason": "Bridge day for Labour Day", "related_holiday": null},
    {"date": "2025-10-18", "original_day": "Saturday", "reason": "Bridge day for October 23", "related_holiday": null},
    {"date": "2025-12-13", "original_day": "Saturday", "reason": "Bridge day for Christmas Eve", "related_holiday": null}
  ],
  "source": {
    "name": "PublicHolidays.hu",
    "url": "https://publicholidays.hu/",
    "year_coverage": 2025,
    "scraped_at": "2025-12-18T10:30:00"
  },
  "total_holidays": 11,
  "total_weekend_workdays": 3
}
```

## Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Hungarian Public Holidays (2025)

| Date | Hungarian Name | English Name |
|------|---------------|--------------|
| January 1 | Újév | New Year's Day |
| March 15 | 1848-as forradalom ünnepe | Revolution Day |
| April 18 | Nagypéntek | Good Friday |
| April 21 | Húsvéthétfő | Easter Monday |
| May 1 | Munka Ünnepe | Labour Day |
| June 9 | Pünkösdhétfő | Whit Monday |
| August 20 | Államalapítás ünnepe | St. Stephen's Day |
| October 23 | 1956-os forradalom ünnepe | Republic Day |
| November 1 | Mindenszentek | All Saints' Day |
| December 25 | Karácsony | Christmas Day |
| December 26 | Karácsony másnapja | 2nd Day of Christmas |

## Weekend Workdays 2025 (Munkanap-áthelyezés)

Based on the [official Hungarian government decree](https://almati.mfa.gov.hu/hu/hu-uennepnapok):

| Working Saturday | Reason | Creates Long Weekend |
|-----------------|--------|---------------------|
| May 17 | Labour Day bridge | May 1-4 (4 days) |
| October 18 | October 23 bridge | October 23-26 (4 days) |
| December 13 | Christmas Eve bridge | December 24-28 (5 days) |

## License

MIT License
