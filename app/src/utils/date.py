from datetime import datetime, timedelta
from src.config import settings

def get_utc_date_range_for_local_period(period_days):
    """
    Calculate UTC date range that matches local calendar days.
    
    Example: "today" in Jakarta (UTC+8)
    - Local: Oct 20, 2025 00:00 to 23:59
    - Returns UTC: Oct 19, 2025 16:00 (start of local day in UTC)
    """
    local_now = datetime.now()
    local_start = (local_now - timedelta(days=period_days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Convert local midnight to UTC
    utc_start = local_start - timedelta(hours=settings.TIMEZONE_OFFSET_HOURS)
    return utc_start


def get_local_date_projection(date_field="reference_date"):
    """
    Returns MongoDB aggregation stage to convert UTC to local date.
    Use this in pipelines for grouping by local calendar days.
    """
    utc_offset_ms = settings.TIMEZONE_OFFSET_HOURS * 60 * 60 * 1000
    return {
        "$addFields": {
            "local_date": {"$add": [f"${date_field}", utc_offset_ms]}
        }
    }