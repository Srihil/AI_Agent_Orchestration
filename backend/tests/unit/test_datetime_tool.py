import re
from app.tools.datetime_tool import get_current_datetime


def test_full_format():
    result = get_current_datetime.invoke({"format": "full"})
    assert "UTC" in result
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC", result)


def test_date_format():
    result = get_current_datetime.invoke({"format": "date"})
    assert re.match(r"\d{4}-\d{2}-\d{2}", result)


def test_iso_format():
    result = get_current_datetime.invoke({"format": "iso"})
    assert "T" in result


def test_timestamp_format():
    result = get_current_datetime.invoke({"format": "timestamp"})
    assert result.isdigit()
    assert int(result) > 1700000000
