from enterpriseagent.guardrails.input import validate_output


async def validate_response(text: str | None) -> str | None:
    result = validate_output(text)
    if result.blocked:
        return None
    return text