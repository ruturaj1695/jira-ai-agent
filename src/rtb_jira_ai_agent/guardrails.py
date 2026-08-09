import re


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"reveal\s+(the\s+)?system\s+prompt",
    r"show\s+me\s+(your|the)\s+hidden\s+instructions",
    r"disregard\s+(all\s+)?rules",
]


def validate_user_query(query: str) -> None:
    """Reject common instruction-override attempts before agent execution."""
    normalized = query.strip()
    if not normalized:
        raise ValueError("Query cannot be empty")
    if len(normalized) > 2000:
        raise ValueError("Query exceeds the maximum supported length")
    if any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS):
        raise ValueError("Potential prompt injection detected")
