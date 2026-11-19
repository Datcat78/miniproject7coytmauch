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


# Tools

@mcp.tool()
def list_posts(mine: bool = False) -> dict[str, Any]:
    """List posts on the Practice Hub.

    Call this to see which posts exist, or to find a post's ID before calling
    get_post or any tool that changes a post. Use mine=True when the user asks
    about their own posts ("my posts"), and before updating or deleting a post,
    because only posts the user owns can be changed.

    Args:
        mine: True returns only posts owned by the user whose API token this
            server uses. False (the default) returns posts from all users.

    Returns:
        On success: {"ok": true, "count": <int>, "post_ids": [<int>, ...],
        "data": [<post>, ...]}. Each post has id, title, body, tags,
        author_id, author_name, created_at, updated_at, and attachments. Use a
        value from post_ids as the post_id argument of other post tools. The
        Hub returns at most 50 posts per request.
        On failure: {"ok": false, "status": <int or null>, "error": <message>}.
    """
    if mine:
        result = practice_hub_request(lambda client: client.list_posts(mine=True))  # GET /posts?mine=true
    else:
        # client.list_posts() always adds ?mine=false, so call the plain endpoint directly.
        result = practice_hub_request(lambda client: client._request("GET", "/posts"))

    posts = result.get("data")
    if result["ok"] and isinstance(posts, list):
        post_ids = [post["id"] for post in posts if isinstance(post, dict) and "id" in post]
        return {"ok": True, "count": len(posts), "post_ids": post_ids, "data": posts}
    return result


@mcp.tool()
def get_post(post_id: int) -> dict[str, Any]:
    """Get one Practice Hub post by its ID, including its full body.

    Call this when you need a single post's complete, current content: to
    show or summarize it, to confirm it exists, or to check its fields before
    updating or deleting it. If you do not know the ID, call list_posts first.

    Args:
        post_id: The post's integer ID, taken from list_posts (post_ids or a
            post's "id" field) or given by the user.

    Returns:
        On success: {"ok": true, "data": <post>}, where the post has id, title,
        body, tags, author_id, author_name, created_at, updated_at, and
        attachments.
        On failure: {"ok": false, "status": <int or null>, "error": <message>}.
        Status 404 means no post has that ID.
    """
    return practice_hub_request(lambda client: client.get_post(post_id))


@mcp.tool()
def create_post(title: str, body: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    """Create a new Practice Hub post owned by the authenticated user.

    Call this only when the user wants to publish a brand-new post. To change
    a post that already exists, use update_post instead.

    Args:
        title: The post title (required, 1-200 characters).
        body: The post text. Defaults to an empty body.
        tags: A list of tag strings, such as ["python", "mcp"]. Defaults to no
            tags.

    Returns:
        On success: {"ok": true, "data": <new post>}. The new post's ID is
        data.id; use it with get_post, update_post, or delete_post.
        On failure: {"ok": false, "status": <int or null>, "error": <message>}.
        Status 422 means the Hub rejected the title, body, or tags.
    """
    return practice_hub_request(lambda client: client.create_post(title, body, tags))


@mcp.tool()
def update_post(
    post_id: int,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Edit an existing Practice Hub post owned by the authenticated user.

    Call this when the user wants to change the title, body, or tags of a post
    that already exists. Pass only the fields to change; any field left out
    keeps its current value. tags replaces the whole tag list, so to add or
    remove a single tag, call get_post first and send the full new list.

    Args:
        post_id: The integer ID of the post to edit (from list_posts or
            get_post).
        title: New title, or omit to keep the current title.
        body: New body text, or omit to keep the current body.
        tags: New complete list of tag strings, or omit to keep the current
            tags. An empty list [] removes all tags.

    Returns:
        On success: {"ok": true, "data": <updated post>}.
        On failure: {"ok": false, "status": <int or null>, "error": <message>}.
        Status 403 means the user does not own this post; 404 means no post
        has that ID.
    """
    # Send only the fields the caller gave, so the Hub keeps the others (PATCH).
    changes = {"title": title, "body": body, "tags": tags}
    fields = {name: value for name, value in changes.items() if value is not None}
    return practice_hub_request(lambda client: client.update_post(post_id, **fields))


@mcp.tool()
def delete_post(post_id: int) -> dict[str, Any]:
    """Permanently delete a Practice Hub post owned by the authenticated user.

    Call this only when the user clearly asks to delete a specific post. This
    cannot be undone, so if you are not sure which post they mean, confirm the
    ID with list_posts(mine=True) or get_post first.

    Args:
        post_id: The integer ID of the post to delete.

    Returns:
        On success: {"ok": true, "post_id": <int>, "message": <confirmation>}.
        On failure: {"ok": false, "status": <int or null>, "error": <message>}.
        Status 403 means the user does not own this post; 404 means no post
        has that ID.
    """
    # The Hub answers a successful DELETE with 204 No Content (an empty body).
    result = practice_hub_request(lambda client: client.delete_post(post_id))
    if result["ok"]:
        return {"ok": True, "post_id": post_id, "message": f"Post {post_id} was deleted."}
    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
