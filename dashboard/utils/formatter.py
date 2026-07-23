"""
Dashboard Formatter Utilities Module.
Formatters for currency, percentage, numbers, and timestamps.
"""


def format_currency(value: float) -> str:
    """Formats numeric float as Indian Rupee (₹) currency string."""
    return f"₹{value:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Formats numeric float as percentage string."""
    return f"{value:.{decimals}f}%"


def format_number(value: float, decimals: int = 2) -> str:
    """Formats numeric float with thousand separators."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"


def format_minutes_to_hours(minutes: float) -> str:
    """Converts duration in minutes to formatted 'Xh Ym' string."""
    hrs = int(minutes // 60)
    mins = int(minutes % 60)
    if hrs > 0:
        return f"{hrs}h {mins}m"
    return f"{mins}m"
