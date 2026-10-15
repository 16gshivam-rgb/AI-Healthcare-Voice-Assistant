from email_validator import EmailNotValidError, validate_email


def normalize_email(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Email address is required.")
    try:
        return validate_email(candidate, check_deliverability=False, test_environment=True).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError("Please provide a valid email address.") from exc
