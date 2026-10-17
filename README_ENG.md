# Linkding MCP Server 🔖

A high-performance, decoupled **Model Context Protocol (MCP)** server designed to seamlessly integrate with your self-hosted **[Linkding](https://github.com/sissbruecker/linkding)** bookmark manager.

Allows any MCP-compatible AI client (such as Google Antigravity, Claude Desktop, Cursor, etc.) to perform the complete CRUD lifecycle for bookmarks and inspect tags natively using tool calling.

---

## 🚀 Features

- **Full Bookmark Lifecycle:** Advanced search (full-text and tag filters like `#dev`), creation, partial in-place updates (`PATCH`), and permanent deletion.
- **Tag Inspection:** List all existing Linkding tags with pagination support.
- **Dual Transport Protocols:**
  - `streamable-http` / `sse`: Run continuously as a background microservice inside Docker containers or NAS/servers (e.g. Synology, UGREEN NAS, Raspberry Pi).
  - `stdio`: Run on-demand as a local process launched directly by your AI client.
- **Isolated Development with Devbox:** Zero pollution of your host system's Python environment.
- **Async & Resilient:** Dual compatibility with `MCPServer` (MCP 2.x) and `FastMCP` (MCP 1.x), asynchronous `httpx`, robust error handling, and structured JSON responses.

---

## 🛠️ Exposed MCP Tools

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `search_bookmarks` | `query` *(opt)*, `limit` *(def: 20)*, `offset` *(def: 0)* | Search bookmarks by title, URL, description, notes, or tags (`#tag`). Returns ID, title, URL, description, notes, and structured tags. |
| `create_bookmark` | `url` *(req)*, `title` *(opt)*, `description` *(opt)*, `notes` *(opt)*, `tags` *(opt)*, `unread` *(def: false)*, `shared` *(def: false)* | Create a new bookmark in Linkding. Automatically maps the `tags` list to the native `tag_names` attribute. |
| `update_bookmark` | `bookmark_id` *(req)*, `tags` *(opt)*, `title` *(opt)*, `description` *(opt)*, `notes` *(opt)*, `unread` *(opt)*, `shared` *(opt)* | Updates only the supplied fields via `PATCH`. Allows replacing tags without modifying other metadata. |
| `delete_bookmark` | `bookmark_id` *(req)* | Permanently delete a bookmark by its integer ID. |
| `get_tags` | `limit` *(def: 100)*, `offset` *(def: 0)* | Retrieve the list of available tags with pagination and creation timestamps. |

---

## ⚙️ Configuration & Environment Variables

Create a `.env` file in the root of the project (you can use `.env.example` as a template):

```bash
# Base URL of your Linkding instance
LINKDING_URL=http://localhost:9090

# Linkding REST API token (obtain from Settings > Integrations > API in Linkding)
LINKDING_API_TOKEN=your_secret_api_token_here

# Optional MCP transport configuration (streamable-http, sse, or stdio)
MCP_TRANSPORT=streamable-http
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

---

## 💻 Local Development with Devbox

The repository includes a `devbox.json` manifest providing an isolated Python 3.12 and `uv` environment.

### 1. Initialize the Environment
```bash
devbox run uv pip install -r requirements.txt
```

### 2. Run as a Web Microservice (Streamable HTTP / SSE)
```bash
# Recommended modern Streamable HTTP mode (endpoint: /mcp)
devbox run python server.py --transport streamable-http --host 0.0.0.0 --port 8000

# Or legacy SSE mode (endpoint: /sse)
devbox run python server.py --transport sse --host 0.0.0.0 --port 8000
```

### 3. Run in Local CLI Mode (STDIO)
```bash
devbox run python server.py --transport stdio
```

---

## 🐳 Deployment with Docker / NAS / Raspberry Pi

Keep the Linkding MCP server running 24/7 on your local network or server:

### Option 1: Docker Compose (Recommended)
1. Configure your `.env` file with your Linkding URL and API Token.
2. Launch the container:
```bash
docker compose up -d --build
```
3. Check the logs:
```bash
docker compose logs -f
```

### Option 2: Pre-built Docker Hub Image
```bash
docker run -d \
  --name linkding-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LINKDING_URL="http://linkding.local:9090" \
  -e LINKDING_API_TOKEN="your_token_here" \
  -e MCP_TRANSPORT="streamable-http" \
  mangrar/linkding-mcp:latest
```

---

## 🔌 AI Client Configuration (`mcp_config.json`)

### A. Remote Network Mode (Streamable HTTP - Recommended)
Best for connecting to a server running in Docker, your NAS, or behind a reverse proxy (e.g. Nginx, NPM, Traefik):

```json
{
  "mcpServers": {
    "linkding": {
      "url": "http://linkding-mcp.local:8000/mcp"
    }
  }
}
```
*(If you are running the legacy SSE transport, specify `/sse` as the endpoint instead)*.

### B. Local Containerized Mode (Docker via STDIO)
Best if you want your local AI client to spawn a fresh, ephemeral container on demand:

```json
{
  "mcpServers": {
    "linkding": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e", "LINKDING_URL=http://localhost:9090",
        "-e", "LINKDING_API_TOKEN=your_token_here",
        "mangrar/linkding-mcp:latest",
        "python",
        "server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### C. Local Devbox Mode (STDIO)
Best for local Python execution without containers:

```json
{
  "mcpServers": {
    "linkding": {
      "command": "devbox",
      "args": [
        "run",
        "-c",
        "/path/to/linkding-mcp",
        "python",
        "server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "LINKDING_URL": "http://localhost:9090",
        "LINKDING_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

---

## 🧪 Verification

You can verify that all tools and parameter schemas register correctly:

```bash
devbox run python -c "
import asyncio, server
tools = asyncio.run(server.mcp.list_tools())
print('Registered tools:', [t.name for t in tools])
"
```

Expected output:
```
Registered tools: ['search_bookmarks', 'create_bookmark', 'update_bookmark', 'delete_bookmark', 'get_tags']
```

---

## 📄 License

MIT License.
