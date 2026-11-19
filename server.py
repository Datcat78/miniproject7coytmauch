# INF601 - Advanced Programming in Python
# Coyt Mauch
# Mini Project 7 - Practice Hub MCP Server

"""Practice Hub MCP server.

Exposes the Practice Hub posts API to MCP clients over stdio. Every tool goes
through one shared helper, ``practice_hub_request``, which builds a
``PracticeHubClient`` from environment configuration and turns every failure
into a clear error result.

stdout carries the MCP protocol messages, so this module never prints.
Diagnostics go to stderr through ``logging``.
"""

import logging
import os
import re
import sys
from typing import Any, Callable

import requests
from mcp.server.fastmcp import FastMCP

from Practice_Hub_Client import PracticeHubClient, PracticeHubConnectionError, PracticeHubError

# Logging goes to stderr so stdout stays reserved for MCP messages.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("practice-hub")

# Configuration. PRACTICE_API_URL is the site root (https://practice.fhsucyber.com);
# PracticeHubClient appends /api/v1 itself.
PRACTICE_API_URL = os.environ.get("PRACTICE_API_URL", "").strip()
PRACTICE_API_TOKEN = os.environ.get("PRACTICE_API_TOKEN", "").strip()
REQUEST_TIMEOUT = 10  # seconds per HTTP request

mcp = FastMCP("practice-hub")


# Shared request helper

def practice_hub_request(operation: Callable[[PracticeHubClient], Any]) -> dict[str, Any]:
    """Run one Practice Hub API call and return a uniform result.

    ``operation`` receives a configured ``PracticeHubClient`` and calls one of
    its methods, for example::

        practice_hub_request(lambda client: client.get_post(post_id))

    Returns ``{"ok": True, "data": ...}`` on success, or
    ``{"ok": False, "status": <int or None>, "error": "<message>"}`` on failure.
    """
    config_error = _config_error()
    if config_error:
        return _failure(config_error)

    try:
        with PracticeHubClient(PRACTICE_API_URL, PRACTICE_API_TOKEN, timeout=REQUEST_TIMEOUT) as client:
            data = operation(client)
    except PracticeHubConnectionError as exc:
        # The client chains the original requests exception as __cause__.
        if isinstance(exc.__cause__, requests.Timeout):
            return _failure(f"Practice Hub did not respond within {REQUEST_TIMEOUT} seconds. Try again in a moment.")
        return _failure(
            f"Could not connect to Practice Hub at {PRACTICE_API_URL}. "
            "Check PRACTICE_API_URL and your network connection."
        )
    except PracticeHubError as exc:
        return _http_failure(exc)

    # The client returns None for an empty body (such as 204 No Content), and
    # delete_post() returns True after a successful DELETE.
    if data is None or data is True:
        return {"ok": True, "data": None, "message": "Request succeeded. There is no response body to return."}
    return {"ok": True, "data": data}


# Helper internals

# PracticeHubClient formats HTTP errors as "<status>: <server detail>".
_STATUS_PREFIX = re.compile(r"^(\d{3}):\s*(.*)$", re.DOTALL)


def _config_error() -> str | None:
    """Describe missing or malformed configuration, or return None if it is usable."""
    missing = [
        name
        for name, value in (("PRACTICE_API_URL", PRACTICE_API_URL), ("PRACTICE_API_TOKEN", PRACTICE_API_TOKEN))
        if not value
    ]
    if missing:
        return f"Missing configuration: set {' and '.join(missing)} in the environment that starts this MCP server."
    if not PRACTICE_API_URL.startswith(("http://", "https://")):
        return (
            "Invalid configuration: PRACTICE_API_URL must start with http:// or https:// "
            "(for example, https://practice.fhsucyber.com)."
        )
    return None


def _http_failure(exc: PracticeHubError) -> dict[str, Any]:
    """Turn a PracticeHubError into a clear message keyed on the HTTP status."""
    match = _STATUS_PREFIX.match(str(exc))
    status = int(match.group(1)) if match else None
    detail = match.group(2).strip() if match else str(exc)

    if status is None:
        # Raised before or after HTTP: a local argument check or a non-JSON success body.
        return _failure(f"Practice Hub request failed: {detail}")

    if status == 401:
        message = "401 Unauthorized: Practice Hub rejected the API token. Check that PRACTICE_API_TOKEN is correct and not expired."
    elif status == 403:
        message = "403 Forbidden: the token is valid but is not allowed to do this (for example, changing a post you do not own)."
    elif status == 404:
        message = (
            "404 Not Found: the requested post or endpoint does not exist. Check the post ID, and make sure "
            "PRACTICE_API_URL is the site root without /api/v1."
        )
    elif status == 422:
        message = "422 Unprocessable Entity: Practice Hub rejected the data that was sent."
    elif status >= 500:
        message = f"{status} Server Error: Practice Hub had a problem handling the request. Try again later."
    else:
        message = f"HTTP {status} error from Practice Hub."

    if detail:
        message += f" Server message: {detail}"
    return _failure(message, status)


def _failure(message: str, status: int | None = None) -> dict[str, Any]:
    """Build the error result, scrubbing the token in case any text echoed it."""
    message = _redact(message)
    logger.warning("Practice Hub request failed: %s", message)
    return {"ok": False, "status": status, "error": message}


def _redact(text: str) -> str:
    if PRACTICE_API_TOKEN:
        text = text.replace(PRACTICE_API_TOKEN, "[REDACTED]")
    return text


if __name__ == "__main__":
    mcp.run(transport="stdio")
