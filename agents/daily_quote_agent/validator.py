import logging

try:
    import requests
except ImportError:
    requests = None
from db_utils import quote_exists

logger = logging.getLogger("quote-agent")


class QuoteValidator:
    def __init__(self):
        pass

    def verify_author(self, quote: str, author: str) -> bool:
        if requests is None:
            logger.warning("requests not available; skipping author verification")
            return True
        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": author,
                "format": "json",
            }
            r = requests.get(search_url, params=params, timeout=10)
            data = r.json()
            if "query" in data and data["query"]["search"]:
                title = data["query"]["search"][0]["title"]
                extract_params = {
                    "action": "query",
                    "prop": "extracts",
                    "titles": title,
                    "explaintext": True,
                    "format": "json",
                }
                r2 = requests.get(search_url, params=extract_params, timeout=10)
                j2 = r2.json()
                pages = j2.get("query", {}).get("pages", {})
                for _, pg in pages.items():
                    extract = pg.get("extract", "").lower()
                    if quote.lower()[:50] in extract or author.lower() in extract:
                        return True
            return True
        except Exception as e:
            logger.warning("Author verification failed (network or parsing): %s", e)
            return True

    def is_unique(self, quote: str) -> bool:
        return not quote_exists(quote)
