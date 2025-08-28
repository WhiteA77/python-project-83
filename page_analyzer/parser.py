import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, timeout: int = 10) -> tuple[str, int]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.text, response.status_code


def parse_seo(html: str) -> tuple[str | None, str | None, str | None]:
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
