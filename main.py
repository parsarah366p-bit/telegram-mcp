import os
import sys

os.environ["MCP_ALLOWED_HOSTS"] = "*"
os.environ["FASTMCP_ALLOWED_HOSTS"] = "*"
os.environ["ALLOWED_HOSTS"] = "*"
os.environ["UVICORN_FORWARDED_ALLOW_IPS"] = "*"
os.environ["UVICORN_PROXY_HEADERS"] = "true"

from telegram_mcp.runner import main

if __name__ == "__main__":
    main()
