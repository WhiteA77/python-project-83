import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException


def fetch_html(url: str, timeout: int = 10) -> tuple[str, int]:
    """Fetch HTML content from the given URL.

    Args:
        url (str): Target URL.
        timeout (int, optional): Request timeout in seconds. Defaults to 10.

    Returns:
        tuple[str, int]: HTML content and status code.

    Raises:
        RequestException: If the request fails or returns an error status.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text, response.status_code


def parse_seo(html: str) -> tuple[str | None, str | None, str | None]:
    """Extract SEO tags from HTML.

    Args:
        html (str): HTML content.

    Returns:
        tuple[str | None, str | None, str | None]: ``h1`` text, ``title`` text
        and ``description`` meta tag content. Missing values are returned as
        ``None``.
    """
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.h1.get_text(strip=True) if soup.h1 else None
    title = soup.title.get_text(strip=True) if soup.title else None
    description_tag = soup.find("meta", attrs={"name": "description"})
    description = (
        description_tag.get("content", "").strip()
        if description_tag and description_tag.get("content")
        else None
    )
    return h1, title, description
