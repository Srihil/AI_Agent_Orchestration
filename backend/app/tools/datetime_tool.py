from datetime import datetime, timezone
from langchain_core.tools import tool


@tool
def get_current_datetime(format: str = "full") -> str:
    """Get the current date and time.

    Args:
        format: Output format — "full" (default), "date", "time", "iso", "timestamp"

    Returns:
        The current date/time as a formatted string.
    """
    now = datetime.now(timezone.utc)

    formats = {
        "full": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S UTC"),
        "iso": now.isoformat(),
        "timestamp": str(int(now.timestamp())),
    }

    return formats.get(format, formats["full"])
