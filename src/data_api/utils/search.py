"""Shared fuzzy ranking for nested published records."""

from thefuzz import fuzz


def fuzzy_matches(items: list[dict], query: str, field: str, threshold: int) -> list[dict]:
    scored = []
    for item in items:
        score = fuzz.partial_ratio(query, item.get(field) or "")
        if score >= threshold:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]
