"""Client for calling the scanner API."""

import base64
import logging
from pathlib import Path
from typing import Any

import requests

from foxhole_stockpiles.core.settings import get_settings

logger = logging.getLogger(__name__)


class ScannerClient:
    """Client for interacting with the scanner API."""

    def __init__(self) -> None:
        """Initialize the scanner client."""
        settings = get_settings()
        self.base_url = f"http://{settings.api_server.host}:{settings.api_server.port}"
        self.auth = None

        # Setup auth if configured
        if settings.api_auth.auth_type == "basic" and settings.api_auth.auth_token:
            # Token must be base64 encoded "username:password" per settings documentation
            try:
                decoded = base64.b64decode(settings.api_auth.auth_token).decode("utf-8")
                if ":" in decoded:
                    username, password = decoded.split(":", 1)
                    self.auth = (username, password)
                else:
                    logger.error("Invalid basic auth token: missing ':' separator")
            except (ValueError, UnicodeDecodeError) as e:
                logger.error("Invalid base64 auth token: %s", e)

    def scan_screenshot(self, filepath: str) -> tuple[bool, str]:
        """Scan a screenshot file.

        Args:
            filepath (str): Path to the screenshot file

        Returns:
            tuple[bool, str]: Tuple of (success, result_message)
        """
        try:
            path = Path(filepath)
            if not path.exists():
                return False, f"File not found: {filepath}"

            logger.info("Scanning %s", path.name)

            # Open and send file
            with open(filepath, "rb") as f:
                files = {"image": (path.name, f, "image/png")}
                response = requests.post(
                    f"{self.base_url}/ocr/scan_image",
                    files=files,
                    auth=self.auth,
                    timeout=30,
                )

            if response.status_code == 200:
                result = response.json()
                if result is None:
                    logger.info("Scan completed successfully")
                    return True, "Scan completed successfully"
                formatted = self._format_result(result)
                logger.info("Scan completed successfully")
                return True, formatted
            else:
                error_msg = f"API Error ({response.status_code}): {response.text}"
                logger.error(error_msg)
                return False, error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to server. Make sure the server is running."
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error scanning screenshot: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _format_result(self, result: dict[str, Any] | None) -> str:
        """Format scan result for display.

        Args:
            result (dict[str, Any] | None): Scan result dictionary

        Returns:
            str: Formatted result string
        """
        lines = []
        lines.append("=== Scan Result ===\n")

        if result and "stockpiles" in result:
            for stockpile in result["stockpiles"]:
                title = stockpile.get("title", "Unknown")
                lines.append(f"\nStockpile: {title}")
                lines.append("-" * 40)

                items = stockpile.get("items", [])
                if items:
                    for item in items:
                        code = item.get("code_name", "unknown")
                        quantity = item.get("quantity", 0)
                        confidence = item.get("confidence", 0.0)
                        lines.append(f"  {code}: {quantity} (confidence: {confidence:.2%})")

                        # Show candidates if available
                        candidates = item.get("candidates", [])
                        if len(candidates) > 1:
                            lines.append("    Alternatives:")
                            for candidate in candidates[1:]:  # Skip first (main match)
                                c_code = candidate.get("code_name", "unknown")
                                c_conf = candidate.get("confidence", 0.0)
                                lines.append(f"      - {c_code} ({c_conf:.2%})")
                else:
                    lines.append("  No items detected")

        lines.append("\n" + "=" * 40)
        return "\n".join(lines)
