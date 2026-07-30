import re
from dataclasses import dataclass, field


@dataclass
class PIIMatch:
    label: str
    start: int
    end: int


@dataclass
class PIIResult:
    has_pii: bool = False
    matches: list[PIIMatch] = field(default_factory=list)


PII_PATTERNS: list[tuple[str, str]] = [
    (r"\b\d{8}[A-Z]\b", "DNI"),
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "email"),
    (r"\b(?:\+34)?[ -]?(?:6|7|9)\d{8}\b", "phone"),
]


def detect_pii(text: str) -> PIIResult:
    matches: list[PIIMatch] = []
    for pattern, label in PII_PATTERNS:
        for match in re.finditer(pattern, text):
            matches.append(PIIMatch(label=label, start=match.start(), end=match.end()))
    return PIIResult(has_pii=len(matches) > 0, matches=matches)


def redact_pii(text: str, pii: PIIResult | None = None) -> str:
    if pii is None:
        pii = detect_pii(text)
    if not pii.has_pii:
        return text

    result = list(text)
    for match in reversed(pii.matches):
        label_upper = match.label.upper()
        replacement = f"[{label_upper}]"
        result[match.start : match.end] = replacement
    return "".join(result)