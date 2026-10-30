import re


def normalize(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s
