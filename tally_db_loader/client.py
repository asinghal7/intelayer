"""
Tally HTTP Client for Database Loader.

Reuses the existing client pattern from Intelayer with additional
features for bulk data extraction.
"""
from __future__ import annotations
import requests
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from loguru import logger
from typing import Optional
from .config import TallyLoaderConfig

DEFAULT_HEADERS = {
    "Content-Type": "text/xml; charset=utf-8",
    "Accept": "text/xml",
    "User-Agent": "tally-db-loader/1.0",
}


class TallyConnectionError(Exception):
    """Raised when connection to Tally fails."""
    pass


class TallyResponseError(Exception):
    """Raised when Tally returns an error response."""
    pass


class TallyLoaderClient:
    """
    HTTP client for Tally XML API with retry logic.
    
    Features:
    - Automatic retry with exponential backoff
    - Connection pooling via requests.Session
    - Configurable timeouts
    - Response validation
    """

    def __init__(self, config: Optional[TallyLoaderConfig] = None):
        self.config = config or TallyLoaderConfig.from_env()
        self.base_url = self.config.tally_url.rstrip("/")
        self.company = self.config.tally_company
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((requests.RequestException, TallyConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying Tally request (attempt {retry_state.attempt_number})..."
        ),
    )
    def post_xml(self, xml: str, timeout: Optional[int] = None) -> str:
        """
        Post XML to Tally and return response.

        Args:
            xml: XML request string
            timeout: Request timeout in seconds (uses config default if not specified)

        Returns:
            XML response string

        Raises:
            TallyConnectionError: If connection fails
            TallyResponseError: If Tally returns an error
        """
        timeout = timeout or self.config.request_timeout
        try:
            r = self.session.post(
                self.base_url, data=xml.encode("utf-8"), timeout=timeout
            )
            r.raise_for_status()
            text = r.text

            # Check for Tally error responses
            # Be more specific to avoid false positives
            is_error = False
            if "<STATUS>0</STATUS>" in text:
                is_error = True
            elif "<LINEERROR>" in text or "<ERRORMSG>" in text:
                is_error = True
            elif "Could not find" in text and "Report" in text:
                is_error = True
            
            if is_error:
                # Extract error message if present
                error_msg = self._extract_error(text)
                if error_msg:
                    raise TallyResponseError(f"Tally error: {error_msg}")

            return text

        except requests.ConnectionError as e:
            logger.error(f"Failed to connect to Tally at {self.base_url}: {e}")
            raise TallyConnectionError(f"Cannot connect to Tally: {e}") from e
        except requests.Timeout as e:
            logger.error(f"Tally request timed out after {timeout}s")
            raise TallyConnectionError(f"Request timeout: {e}") from e
        except requests.RequestException as e:
            logger.error(f"Tally request failed: {e}")
            raise TallyConnectionError(f"Request failed: {e}") from e

    def _extract_error(self, text: str) -> Optional[str]:
        """Extract error message from Tally response."""
        import re
        
        # Look for common error patterns in XML tags
        patterns = [
            r"<LINEERROR>(.*?)</LINEERROR>",
            r"<ERROR>(.*?)</ERROR>",
            r"<ERRORMSG>(.*?)</ERRORMSG>",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                # Decode HTML entities
                msg = match.group(1).strip()
                msg = msg.replace("&apos;", "'").replace("&quot;", '"')
                msg = msg.replace("&lt;", "<").replace("&gt;", ">")
                msg = msg.replace("&amp;", "&")
                return msg
        
        # Check for plain text "Could not find" errors
        if "Could not find" in text:
            match = re.search(r"(Could not find[^<]+)", text)
            if match:
                msg = match.group(1).strip()
                msg = msg.replace("&apos;", "'")
                return msg
        
        return None

    def test_connection(self) -> dict:
        """
        Test connection to Tally and return server info.

        Returns:
            Dict with connection status and server info
        """
        # Use a simple Collection request for ledger groups - always exists in any company
        # This mirrors the pattern used by existing Intelayer adapters
        test_xml = f"""<ENVELOPE>
            <HEADER>
                <VERSION>1</VERSION>
                <TALLYREQUEST>Export</TALLYREQUEST>
                <TYPE>Collection</TYPE>
                <ID>ListOfGroups</ID>
            </HEADER>
            <BODY>
                <DESC>
                    <STATICVARIABLES>
                        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
                        <SVCURRENTCOMPANY>{self.company}</SVCURRENTCOMPANY>
                    </STATICVARIABLES>
                    <TDL>
                        <TDLMESSAGE>
                            <COLLECTION NAME="ListOfGroups" ISMODIFY="No">
                                <TYPE>Group</TYPE>
                                <FETCH>NAME</FETCH>
                            </COLLECTION>
                        </TDLMESSAGE>
                    </TDL>
                </DESC>
            </BODY>
        </ENVELOPE>"""

        try:
            response = self.post_xml(test_xml, timeout=30)
            # Check if we got a valid XML response with data
            if "<ENVELOPE" in response and "<COLLECTION" in response:
                # Count groups to show something meaningful
                group_count = response.count("<GROUP ")
                return {
                    "status": "connected",
                    "url": self.base_url,
                    "company": self.company,
                    "response_length": len(response),
                    "groups_found": group_count,
                }
            elif "<ENVELOPE" in response:
                # Got response but maybe empty
                return {
                    "status": "connected",
                    "url": self.base_url,
                    "company": self.company,
                    "message": "Connected, response received",
                    "response_length": len(response),
                }
            else:
                return {
                    "status": "connected_unknown",
                    "url": self.base_url,
                    "message": "Connected but unexpected response format",
                }
        except Exception as e:
            return {
                "status": "failed",
                "url": self.base_url,
                "error": str(e),
            }

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

