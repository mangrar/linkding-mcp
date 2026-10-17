# Linkding MCP Server 🔖

Servidor desacoplado de alto rendimiento basado en el protocolo **Model Context Protocol (MCP)** para interactuar con una instancia autoalojada de **[Linkding](https://github.com/sissbruecker/linkding)**.

Permite a cualquier cliente de IA compatible (Google Antigravity, Claude Desktop, Cursor, etc.) realizar el ciclo CRUD completo de marcadores y consulta de etiquetas de forma nativa mediante llamadas a herramientas (Tool Calling).

---

## 🚀 Características

- **Gestión completa de marcadores:** Búsqueda avanzada (por texto o tags como `#dev`), creación, edición parcial sin pérdida de datos (`PATCH`), y borrado permanente.
- **Consulta de etiquetas:** Inspección de todas las etiquetas (*tags*) existentes en Linkding con paginación.
- **Doble soporte de transporte:**
  - `streamable-http` / `sse`: Para despliegue continuo como microservicio en contenedores Docker o servidores/NAS (ej. UGREEN NAS, Synology, Raspberry Pi).
  - `stdio`: Para ejecución directa local gestionada por el cliente de IA.
- **Entorno reproducible con Devbox:** Sin ensuciar el Python del sistema operativo host.
- **Asíncrono y resiliente:** Desarrollado con compatibilidad dual `MCPServer` (MCP 2.x) y `FastMCP` (MCP 1.x) junto a `httpx` asíncrono, con manejo exhaustivo de excepciones y respuestas estructuradas.

---

## 🛠️ Herramientas MCP Expuestas

| Herramienta | Parámetros | Descripción |
| :--- | :--- | :--- |
| `search_bookmarks` | `query` *(opc)*, `limit` *(def: 20)*, `offset` *(def: 0)* | Busca marcadores por texto, URL, notas o tags (`#tag`). Devuelve ID, título, URL, descripción, notas y tags estructurados. |
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

# Configuración opcional de transporte MCP (streamable-http, sse, o stdio)
MCP_TRANSPORT=streamable-http
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

### 2. Ejecutar en modo Servidor Web (Streamable HTTP / SSE)
```bash
# Modo recomendado Streamable HTTP (endpoint: /mcp)
devbox run python server.py --transport streamable-http --host 0.0.0.0 --port 8000

# O modo SSE (endpoint: /sse)
devbox run python server.py --transport sse --host 0.0.0.0 --port 8000
```

### 3. Ejecutar en modo Local (STDIO)
```bash
devbox run python server.py --transport stdio
```

---

## 🐳 Despliegue con Docker / NAS / Raspberry Pi

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

### Opción 2: Usar imagen publicada desde Docker Hub
```bash
docker run -d \
  --name linkding-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e LINKDING_URL="http://linkding.local:9090" \
  -e LINKDING_API_TOKEN="tu_token_aqui" \
  -e MCP_TRANSPORT="streamable-http" \
  mangrar/linkding-mcp:latest
```

---

## 🔌 Configuración en Clientes MCP (`mcp_config.json`)

### A. Modo Remoto (Streamable HTTP - Recomendado)
Ideal si el contenedor corre en tu red local o tras un proxy inverso (Nginx / NPM / Traefik):

```json
{
  "mcpServers": {
    "linkding": {
      "url": "http://linkding-mcp.local:8000/mcp"
    }
  }
}
```
*(Si utilizas el modo heredado SSE, usa la URL con terminación `/sse`)*.

### B. Modo Local con Docker (`stdio`)
Si prefieres que tu cliente de IA levante el contenedor directamente por `stdio`:

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
        "-e", "LINKDING_API_TOKEN=tu_token_aqui",
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

### C. Modo Local con Devbox (STDIO)
Ideal para desarrollo local directo:

```json
{
  "mcpServers": {
    "linkding": {
      "command": "devbox",
      "args": [
        "run",
        "-c",
        "/ruta/hacia/linkding-mcp",
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

---

## 📄 Licencia

MIT License.
