# Linkding MCP Server 🔖

Servidor desacoplado de alto rendimiento basado en el protocolo **Model Context Protocol (MCP)** para interactuar con una instancia autoalojada de **[Linkding](https://github.com/sissbruecker/linkding)**.

Permite a cualquier cliente de IA compatible (Google Antigravity, Claude Desktop, Cursor, etc.) realizar el ciclo CRUD completo de marcadores y consulta de etiquetas de forma nativa mediante llamadas a herramientas (Tool Calling).

---

## 🚀 Características

- **Gestión completa de marcadores:** Búsqueda avanzada (por texto o tags como `#dev`), creación, edición parcial sin pérdida de datos, y borrado permanente.
- **Consulta de etiquetas:** Inspección de todas las etiquetas (*tags*) existentes en Linkding con paginación.
- **Doble soporte de transporte:**
  - `stdio`: Para ejecución directa local gestionada por el cliente de IA.
  - `sse` / `streamable-http`: Para despliegue continuo como microservicio en contenedores Docker o NAS (ej. UGREEN NAS, Synology, Raspberry Pi).
- **Entorno reproducible con Devbox:** Sin ensuciar el Python del sistema operativo host.
- **Asíncrono y resiliente:** Desarrollado con `FastMCP` / `MCPServer` y `httpx` asíncrono, con manejo exhaustivo de excepciones y respuestas estructuradas.

---

## 🛠️ Herramientas MCP Expuestas

| Herramienta | Parámetros | Descripción |
| :--- | :--- | :--- |
| `search_bookmarks` | `query` *(opc)*, `limit` *(def: 20)*, `offset` *(def: 0)* | Busca marcadores por texto, URL, notas o tags (`#tag`). Devuelve ID, título, URL, descripción, notas y tags. |
| `create_bookmark` | `url` *(req)*, `title` *(opc)*, `description` *(opc)*, `notes` *(opc)*, `tags` *(opc)*, `unread` *(def: false)*, `shared` *(def: false)* | Crea un nuevo marcador en Linkding. Mapea la lista `tags` al campo nativo `tag_names`. |
| `update_bookmark` | `bookmark_id` *(req)*, `tags` *(opc)*, `title` *(opc)*, `description` *(opc)*, `notes` *(opc)*, `unread` *(opc)*, `shared` *(opc)* | Actualiza únicamente los campos proporcionados mediante `PATCH`. Permite reemplazar tags sin alterar el resto de metadatos. |
| `delete_bookmark` | `bookmark_id` *(req)* | Elimina permanentemente un marcador por su ID numérico. |
| `get_tags` | `limit` *(def: 100)*, `offset` *(def: 0)* | Obtiene el listado de etiquetas disponibles y su fecha de creación. |

---

## ⚙️ Configuración y Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (puedes basarte en `.env.example`):

```bash
# URL base de tu instancia de Linkding
LINKDING_URL=http://localhost:9090

# Token API de Linkding (Obtener en: Configuración > Integraciones > API en Linkding)
LINKDING_API_TOKEN=tu_token_api_secreto_aqui

# Configuración opcional de transporte MCP
MCP_TRANSPORT=stdio
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

---

## 💻 Desarrollo y Ejecución Local con Devbox

El proyecto incluye un manifiesto `devbox.json` con Python 3.12 y `uv` aislados.

### 1. Inicializar el entorno
```bash
devbox run uv pip install -r requirements.txt
```

### 2. Ejecutar en modo Local (STDIO)
```bash
devbox run python server.py --transport stdio
```

### 3. Ejecutar en modo Servidor Web (SSE para pruebas de red)
```bash
devbox run python server.py --transport sse --host 0.0.0.0 --port 8000
```
El servidor expondrá el endpoint SSE en: `http://localhost:8000/sse` (o `/messages/`).

---

## 🐳 Despliegue con Docker / NAS (UGREEN, Synology, etc.)

Para mantener el servidor MCP corriendo de forma ininterrumpida en tu servidor o NAS:

### Opción 1: Docker Compose (Recomendada)
1. Edita el archivo `.env` con la URL y Token de tu Linkding.
2. Levanta el servicio:
```bash
docker compose up -d --build
```
3. Verifica los logs:
```bash
docker compose logs -f
```

### Opción 2: Docker CLI Directo
```bash
docker build -t linkding-mcp .

docker run -d \
  --name linkding-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LINKDING_URL="http://192.168.1.X:9090" \
  -e LINKDING_API_TOKEN="tu_token_aqui" \
  linkding-mcp
```

---

## 🔌 Configuración en Clientes MCP (`mcp_config.json`)

### A. Modo Remoto (Vía SSE en Docker / NAS)
Ideal si el contenedor corre en tu red local (por ejemplo en tu NAS `dxp4800.lan`):

```json
{
  "mcpServers": {
    "linkding": {
      "url": "http://linkding-mcp.dxp4800.lan:8000/sse"
    }
  }
}
```

### B. Modo Local con Devbox (STDIO)
Ideal para ejecutar directamente en tu máquina de desarrollo sin levantar contenedores:

```json
{
  "mcpServers": {
    "linkding": {
      "command": "devbox",
      "args": [
        "run",
        "-c",
        "/Users/mangrar/Workspace/Antigravity/linkding-mcp",
        "python",
        "server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "LINKDING_URL": "http://localhost:9090",
        "LINKDING_API_TOKEN": "tu_token_aqui"
      }
    }
  }
}
```

### C. Modo Local con Virtualenv (.venv)
Si prefieres invocar directamente el binario de Python generado por Devbox:

```json
{
  "mcpServers": {
    "linkding": {
      "command": "/Users/mangrar/Workspace/Antigravity/linkding-mcp/.venv/bin/python",
      "args": [
        "/Users/mangrar/Workspace/Antigravity/linkding-mcp/server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "LINKDING_URL": "http://localhost:9090",
        "LINKDING_API_TOKEN": "tu_token_aqui"
      }
    }
  }
}
```

---

## 🧪 Pruebas de Funcionamiento

Puedes verificar que las herramientas y esquemas responden adecuadamente ejecutando:

```bash
devbox run python -c "
import asyncio, server
tools = asyncio.run(server.mcp.list_tools())
print('Herramientas registradas:', [t.name for t in tools])
"
```

Resultado esperado:
```
Herramientas registradas: ['search_bookmarks', 'create_bookmark', 'update_bookmark', 'delete_bookmark', 'get_tags']
```
