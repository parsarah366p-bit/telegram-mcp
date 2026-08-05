import os
import sys

os.environ["MCP_TRANSPORT"] = os.getenv("MCP_TRANSPORT", "sse")
os.environ["MCP_HOST"] = os.getenv("MCP_HOST", "0.0.0.0")

if "PORT" in os.environ:
    os.environ["MCP_PORT"] = os.environ["PORT"]

os.environ["MCP_ALLOWED_HOSTS"] = "*"
os.environ["FASTMCP_ALLOWED_HOSTS"] = "*"
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["UVICORN_FORWARDED_ALLOW_IPS"] = "*"
os.environ["UVICORN_PROXY_HEADERS"] = "true"

from telegram_mcp.runner import main

if __name__ == "__main__":
    main()
