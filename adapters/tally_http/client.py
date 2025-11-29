import requests
from tenacity import retry, wait_exponential, stop_after_attempt
from .validators import ensure_status_ok, TallyHTTPError

DEFAULT_HEADERS = {
    "Content-Type": "text/xml; charset=utf-8",
    "Accept": "text/xml",
    "User-Agent": "intelayer/0.1",
}

class TallyClient:
    def __init__(self, base_url: str, company: str):
        self.base_url = base_url.rstrip("/")
        self.company = company
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @retry(wait=wait_exponential(multiplier=1, min=1, max=30),
           stop=stop_after_attempt(5))
    def post_xml(self, xml: str, timeout: int = 300) -> str:
        """
        Post XML to Tally and return response.
        
        Args:
            xml: XML request string
            timeout: Request timeout in seconds (default 300 for large exports)
        """
        r = self.session.post(self.base_url, data=xml.encode("utf-8"), timeout=timeout)
        r.raise_for_status()
        text = r.text
        ensure_status_ok(text)  # raises if STATUS != 1
        return text
