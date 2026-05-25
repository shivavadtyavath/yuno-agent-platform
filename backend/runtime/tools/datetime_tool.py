"""
Date/time tool — gives agents awareness of the current time.
"""
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def get_current_datetime(timezone_name: str = "UTC") -> str:
    """
    Get the current date and time.

    Args:
        timezone_name: Timezone name (default: UTC). Examples: "UTC", "Asia/Kolkata".

    Returns:
        Current date and time as a formatted string.
    """
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(timezone_name)
        now = datetime.now(tz)
        return now.strftime(f"%A, %B %d %Y %H:%M:%S {timezone_name}")
    except Exception:
        now = datetime.now(timezone.utc)
        return now.strftime("%A, %B %d %Y %H:%M:%S UTC")
