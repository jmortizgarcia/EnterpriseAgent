import re

MAX_INPUT_LENGTH = 4000

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(your|previous|all)\s+(instructions|prompts|system)",
    r"you\s+are\s+(now|henceforth)",
    r"system\s+prompt:",
    r"forget\s+(everything|all\s+previous)",
    r"override\s+(your|previous)\s+(instructions|directives)",
    r"do\s+not\s+follow\s+(the\s+)?(instructions|rules|guidelines)",
    r"act\s+as\s+(if\s+you\s+are|though\s+you\s+are)\s+(a\s+)?(human|admin|system)",
]


class ValidationResult:
    def __init__(self, blocked: bool = False, reason: str = ""):
        self.blocked = blocked
        self.reason = reason


def validate_input(text: str) -> ValidationResult:
    if not text:
        return ValidationResult(blocked=True, reason="Empty message")

    if len(text) > MAX_INPUT_LENGTH:
        return ValidationResult(
            blocked=True,
            reason=f"Input too long ({len(text)} characters, max {MAX_INPUT_LENGTH})",
        )

    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return ValidationResult(blocked=True, reason="Prompt injection detected")

    return ValidationResult(blocked=False)


def validate_output(text: str | None) -> ValidationResult:
    if not text:
        return ValidationResult(blocked=False)

    if len(text) > MAX_INPUT_LENGTH * 2:
        return ValidationResult(
            blocked=True,
            reason=f"Response too long ({len(text)} characters)",
        )

    return ValidationResult(blocked=False)