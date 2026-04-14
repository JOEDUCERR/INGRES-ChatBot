import re

BLOCKED_PATTERNS = [
    r"(drop\s+table)", r"(delete\s+from)", r"(insert\s+into)",
    r"(update\s+\w+\s+set)", r"(--)", r"(;.*)", r"(<script)"
]

def sanitize_input(text: str) -> str:
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            raise ValueError("Potentially harmful input detected.")
    return text.strip()