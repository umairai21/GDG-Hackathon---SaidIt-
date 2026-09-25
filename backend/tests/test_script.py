import pytest

from pipeline.script import detect_script


@pytest.mark.parametrize("text,expected", [
    ("dahi", "latin"),
    ("حليب", "arabic"),
    ("500", "digits"),
    ("3eish", "mixed"),     # Arabizi: Latin letters + digits as letters
    ("la7m", "mixed"),
    ("milkحليب", "mixed"),
    ("café", "latin"),
])
def test_detect_script(text, expected):
    assert detect_script(text) == expected
