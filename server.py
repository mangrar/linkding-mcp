"""
Linkding MCP Server
A complete, decoupled Model Context Protocol (MCP) server for Linkding bookmarks.
Supports both stdio transport (local) and SSE/Streamable-HTTP transport (Docker/NAS/remote).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Compatibility import across mcp 2.x (MCPServer) and mcp 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
    IS_MCP_V2 = True
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        IS_MCP_V2 = False
    except ImportError:
        from fastmcp import FastMCP
        IS_MCP_V2 = False

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("linkding-mcp")

# Initialize Server
mcp = FastMCP(
    name="linkding",
    instructions=(
        "Linkding MCP server providing full CRUD management for bookmarks and tags "
        "in your self-hosted Linkding instance."
    ),
)


def get_linkding_config() -> tuple[str, str]:
    """Retrieve and validate Linkding URL and API Token from environment variables."""
    base_url = os.getenv("LINKDING_URL", "http://localhost:9090").strip().rstrip("/")
    api_token = os.getenv("LINKDING_API_TOKEN", "").strip()

    if not api_token:
        raise ValueError(
            "LINKDING_API_TOKEN is missing. Please configure LINKDING_API_TOKEN "
            "with your Linkding REST API token (Settings > Integrations > API in Linkding)."
        )

    return base_url, api_token


def get_headers(api_token: str) -> Dict[str, str]:
    """Build standard authorization and content headers for Linkding REST API."""
    return {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def format_error_response(exc: Exception) -> Dict[str, Any]:
    """Generate friendly and structured error messages."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text

        if status in (401, 403):
            return {
                "error": "Authentication failed",
                "status_code": status,
                "message": "Invalid or expired LINKDING_API_TOKEN. Please verify your token permissions.",
                "details": detail,
            }
        elif status == 404:
            return {
                "error": "Not Found",
                "status_code": 404,
                "message": "The requested bookmark or endpoint was not found.",
                "details": detail,
            }
        return {
            "error": "HTTP Error",
            "status_code": status,
            "message": f"Linkding API returned status code {status}",
            "details": detail,
        }
    elif isinstance(exc, httpx.ConnectError):
        return {
            "error": "Connection Failed",
            "message": (
                "Could not connect to the Linkding instance. "
                "Verify that LINKDING_URL is correct and the server is running."
            ),
        }
    elif isinstance(exc, httpx.TimeoutException):
        return {
            "error": "Timeout",
            "message": "Request to Linkding timed out. Please check your network or server latency.",
        }
    return {
        "error": "Unexpected Error",
        "message": str(exc),
    }


@mcp.tool()
async def search_bookmarks(
    query: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> Dict[str, Any]:
    """Search bookmarks in Linkding or list recent bookmarks with pagination.

    Args:
        query: Optional search term. Matches across title, URL, description, notes, and tags (use '#tag' for specific tags).
        limit: Maximum number of bookmarks to return (default: 20, max: 100).
        offset: Pagination offset index (default: 0).

    Returns:
        A structured dictionary containing total count, pagination status, and the list of bookmarks with ID, title, URL, description, notes, and tags.
    """
    try:
        base_url, token = get_linkding_config()
    except ValueError as e:
        return {"error": "Configuration Error", "message": str(e)}

    params: Dict[str, Any] = {
        "limit": max(1, min(limit, 100)),
        "offset": max(0, offset),
    }
    if query:
        params["q"] = query.strip()

    endpoint = f"{base_url}/api/bookmarks/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(endpoint, headers=get_headers(token), params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for b in data.get("results", []):
                results.append({
                    "id": b.get("id"),
                    "url": b.get("url"),
                    "title": b.get("title") or b.get("website_title") or "Untitled",
                    "description": b.get("description") or b.get("website_description") or "",
                    "notes": b.get("notes") or "",
                    "tags": b.get("tag_names", []),
                    "unread": b.get("unread", False),
                    "shared": b.get("shared", False),
                    "date_added": b.get("date_added"),
                    "date_modified": b.get("date_modified"),
                })

            return {
                "count": data.get("count", len(results)),
                "has_more": bool(data.get("next")),
                "limit": params["limit"],
                "offset": params["offset"],
                "bookmarks": results,
            }
        except Exception as exc:
            logger.error("Error searching bookmarks: %s", exc)
            return format_error_response(exc)


@mcp.tool()
async def create_bookmark(
    url: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
    unread: bool = False,
    shared: bool = False,
) -> Dict[str, Any]:
    """Create a new bookmark in Linkding.

    Args:
        url: The web URL to bookmark (required, e.g. "https://news.ycombinator.com").
        title: Optional custom title. If omitted, Linkding can fetch the title automatically from the webpage.
        description: Optional custom summary or description.
        notes: Optional markdown notes attached to the bookmark.
        tags: Optional list of tags (e.g. ["python", "ai", "tools"]).
        unread: Mark bookmark as unread to read later (default: False).
        shared: Share bookmark publicly in Linkding (default: False).

    Returns:
        The newly created bookmark object with its assigned ID and metadata.
    """
    try:
        base_url, token = get_linkding_config()
    except ValueError as e:
        return {"error": "Configuration Error", "message": str(e)}

    payload: Dict[str, Any] = {
        "url": url.strip(),
        "unread": bool(unread),
        "shared": bool(shared),
    }

    if title is not None:
        payload["title"] = title.strip()
    if description is not None:
        payload["description"] = description.strip()
    if notes is not None:
        payload["notes"] = notes.strip()
    if tags is not None:
        payload["tag_names"] = [t.strip() for t in tags if t.strip()]

    endpoint = f"{base_url}/api/bookmarks/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(endpoint, headers=get_headers(token), json=payload)
            response.raise_for_status()
            data = response.json()

            return {
                "message": "Bookmark created successfully",
                "bookmark": {
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": data.get("title") or data.get("website_title"),
                    "description": data.get("description") or data.get("website_description"),
                    "notes": data.get("notes"),
                    "tags": data.get("tag_names", []),
                    "unread": data.get("unread"),
                    "shared": data.get("shared"),
                    "date_added": data.get("date_added"),
                },
            }
        except Exception as exc:
            logger.error("Error creating bookmark '%s': %s", url, exc)
            return format_error_response(exc)


@mcp.tool()
async def update_bookmark(
    bookmark_id: int,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    notes: Optional[str] = None,
    unread: Optional[bool] = None,
    shared: Optional[bool] = None,
) -> Dict[str, Any]:
    """Update an existing bookmark in Linkding. Only specified fields will be updated.

    Args:
        bookmark_id: The integer ID of the bookmark to update (required).
        tags: Optional new list of tags. Replaces tags for this bookmark without affecting other fields.
        title: Optional new title.
        description: Optional new description.
        notes: Optional new markdown notes.
        unread: Optional bool to update unread status.
        shared: Optional bool to update public sharing status.

    Returns:
        The updated bookmark details.
    """
    try:
        base_url, token = get_linkding_config()
    except ValueError as e:
        return {"error": "Configuration Error", "message": str(e)}

    payload: Dict[str, Any] = {}

    if title is not None:
        payload["title"] = title.strip()
    if description is not None:
        payload["description"] = description.strip()
    if notes is not None:
        payload["notes"] = notes.strip()
    if tags is not None:
        payload["tag_names"] = [t.strip() for t in tags if t.strip()]
    if unread is not None:
        payload["unread"] = unread
    if shared is not None:
        payload["shared"] = shared

    if not payload:
        return {
            "error": "No update fields provided",
            "message": "Specify at least one field to update (e.g. title, tags, description, unread, shared).",
        }

    endpoint = f"{base_url}/api/bookmarks/{bookmark_id}/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.patch(endpoint, headers=get_headers(token), json=payload)
            response.raise_for_status()
            data = response.json()

            return {
                "message": f"Bookmark {bookmark_id} updated successfully",
                "bookmark": {
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": data.get("title") or data.get("website_title"),
                    "description": data.get("description") or data.get("website_description"),
                    "notes": data.get("notes"),
                    "tags": data.get("tag_names", []),
                    "unread": data.get("unread"),
                    "shared": data.get("shared"),
                    "date_modified": data.get("date_modified"),
                },
            }
        except Exception as exc:
            logger.error("Error updating bookmark %s: %s", bookmark_id, exc)
            return format_error_response(exc)


@mcp.tool()
async def delete_bookmark(bookmark_id: int) -> Dict[str, Any]:
    """Delete a bookmark from Linkding permanently.

    Args:
        bookmark_id: The integer ID of the bookmark to delete.

    Returns:
        A confirmation message indicating deletion success.
    """
    try:
        base_url, token = get_linkding_config()
    except ValueError as e:
        return {"error": "Configuration Error", "message": str(e)}

    endpoint = f"{base_url}/api/bookmarks/{bookmark_id}/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.delete(endpoint, headers=get_headers(token))
            response.raise_for_status()

            return {
                "message": f"Bookmark {bookmark_id} deleted successfully.",
                "deleted_id": bookmark_id,
                "status": "success",
            }
        except Exception as exc:
            logger.error("Error deleting bookmark %s: %s", bookmark_id, exc)
            return format_error_response(exc)


@mcp.tool()
async def get_tags(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Retrieve all available tags from Linkding.

    Args:
        limit: Maximum number of tags to return (default: 100).
        offset: Starting index for pagination (default: 0).

    Returns:
        A dictionary containing total count and the list of tags with their names and creation dates.
    """
    try:
        base_url, token = get_linkding_config()
    except ValueError as e:
        return {"error": "Configuration Error", "message": str(e)}

    params = {
        "limit": max(1, min(limit, 500)),
        "offset": max(0, offset),
    }

    endpoint = f"{base_url}/api/tags/"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(endpoint, headers=get_headers(token), params=params)
            response.raise_for_status()
            data = response.json()

            tags = [
                {
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "date_added": t.get("date_added"),
                }
                for t in data.get("results", [])
            ]

            return {
                "count": data.get("count", len(tags)),
                "has_more": bool(data.get("next")),
                "tags": tags,
            }
        except Exception as exc:
            logger.error("Error fetching tags: %s", exc)
            return format_error_response(exc)


def main():
    """Main entrypoint supporting stdio, SSE, and streamable-http transport."""
    parser = argparse.ArgumentParser(description="Linkding Model Context Protocol (MCP) Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport protocol: 'stdio' for CLI/local IDEs, 'sse' or 'streamable-http' for HTTP microservice (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "0.0.0.0"),
        help="Host interface to bind HTTP server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port to listen on (default: 8000)",
    )

    args = parser.parse_args()

    logger.info("Starting Linkding MCP server with transport '%s'...", args.transport)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        if IS_MCP_V2:
            mcp.run(transport=args.transport, host=args.host, port=args.port)
        else:
            if hasattr(mcp, "settings"):
                mcp.settings.host = args.host
                mcp.settings.port = args.port
            mcp.run(transport="sse")


if __name__ == "__main__":
    main()
