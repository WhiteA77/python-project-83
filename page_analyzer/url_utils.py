from urllib.parse import urlparse

import validators

DEFAULT_MAX_LENGTH = 255


def validate_url(url: str, max_length: int = DEFAULT_MAX_LENGTH) -> bool:
    if not url or len(url) > max_length:
        return False
    return validators.url(url) is True


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"