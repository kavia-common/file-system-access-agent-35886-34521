# Backend API Usage

This backend exposes REST endpoints for:
- Filesystem operations under /api/fs/*
- MCP integration under /api/mcp/*

Base URL
- Swagger UI: /docs
- ReDoc: /redoc
- OpenAPI JSON: /swagger.json
- API prefix: /api

Security and sandboxing
- All filesystem operations are sandboxed to BASE_DIR one level above Django's settings BASE_DIR (the repository root by default).
- Path traversal is prevented by resolve_safe_path.
- CORS is enabled for development and should be hardened for production.

Filesystem endpoints
- GET /api/fs/list/?path=...&recursive=false&include_hidden=false
- GET /api/fs/read/?path=...&offset=0&length=&encoding=utf-8
- POST /api/fs/write/ { path, content, encoding='utf-8', append=false }
- POST /api/fs/mkdir/ { path, parents=true, exist_ok=true }
- POST /api/fs/remove/ { path, recursive=false, force=false }
- POST /api/fs/copy/ { src, dst, overwrite=false }
- POST /api/fs/move/ { src, dst, overwrite=false }
- POST /api/fs/rename/ { path, new_name, overwrite=false }
- GET /api/fs/search/?path=...&pattern=**/*.py&include_hidden=false

MCP endpoints
- GET /api/mcp/tools/ -> { success, data: { tools: [...] } }
- POST /api/mcp/call/ { tool_name, arguments } -> { success, data|error }

Environment variables
- See .env.example for MCP_SERVER_URL and MCP_API_KEY placeholders.
