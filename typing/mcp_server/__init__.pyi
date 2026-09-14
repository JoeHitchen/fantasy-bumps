from typing import Any

from django.http import HttpRequest


class MCPToolset:
    mcp_server: Any
    context: Any
    request: HttpRequest | None

    def __init__(self, context: Any = ..., request: HttpRequest | None = ...) -> None:
        ...
