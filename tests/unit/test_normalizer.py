import pytest

from catalog.normalizer import normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("abc-123", "ABC123"),
        (" 12 34 ", "1234"),
        ("Bosch 0.986/494", "BOSCH0986494"),
        ("", ""),
    ],
)
def test_normalize_keeps_only_uppercase_alphanumerics(raw: str, expected: str) -> None:
    assert normalize(raw) == expected
