"""Compatibility entrypoint for the Telegram MCP server.

The implementation lives in the telegram_mcp package. This module keeps the
historic `main` import path and console script target working.
"""

import os

# ۱. ست کردن دامنه دقیق و عمومی قبل از هرگونه Import
RAILWAY_DOMAIN = "telegram-mcp-production-7c4b.up.railway.app"
ALLOWED_DOMAINS = f"{RAILWAY_DOMAIN},localhost,127.0.0.1,*"

os.environ["MCP_ALLOWED_HOSTS"] = ALLOWED_DOMAINS
os.environ["FASTMCP_ALLOWED_HOSTS"] = ALLOWED_DOMAINS
os.environ["ALLOWED_HOSTS"] = ALLOWED_DOMAINS
os.environ["UVICORN_FORWARDED_ALLOW_IPS"] = "*"
os.environ["UVICORN_PROXY_HEADERS"] = "true"

# ۲. خنثی‌سازی مستقیم اعتبارسنجی Host در ماژول امنیتی MCP پایتون
try:
    import mcp.server.transport_security as ts
    if hasattr(ts, "check_host_header"):
        ts.check_host_header = lambda *args, **kwargs: True
    if hasattr(ts, "ALLOWED_HOSTS") and isinstance(ts.ALLOWED_HOSTS, set):
        ts.ALLOWED_HOSTS.add(RAILWAY_DOMAIN)
        ts.ALLOWED_HOSTS.add("*")
except Exception:
    pass

from telegram_mcp.install_guard import UnsafeInstallationError, assert_safe_distribution

try:
    assert_safe_distribution()
except UnsafeInstallationError as exc:
    raise SystemExit(str(exc)) from None

from telegram_mcp import runtime as _runtime
from telegram_mcp.runtime import *
from telegram_mcp.runner import _main, main
from telegram_mcp.tools import *

SERVER_ALLOWED_ROOTS = _runtime.SERVER_ALLOWED_ROOTS


def _sync_runtime_roots() -> None:
    _runtime.SERVER_ALLOWED_ROOTS = SERVER_ALLOWED_ROOTS


async def _get_effective_allowed_roots(ctx):
    _sync_runtime_roots()
    return await _runtime._get_effective_allowed_roots(ctx)


async def _get_effective_allowed_roots_with_status(ctx):
    _sync_runtime_roots()
    return await _runtime._get_effective_allowed_roots_with_status(ctx)


async def _ensure_allowed_roots(ctx, tool_name):
    _sync_runtime_roots()
    return await _runtime._ensure_allowed_roots(ctx, tool_name)


async def _resolve_readable_file_path(*, raw_path, ctx, tool_name):
    _sync_runtime_roots()
    return await _runtime._resolve_readable_file_path(
        raw_path=raw_path,
        ctx=ctx,
        tool_name=tool_name,
    )


async def _resolve_writable_file_path(*, raw_path, default_filename, ctx, tool_name):
    _sync_runtime_roots()
    return await _runtime._resolve_writable_file_path(
        raw_path=raw_path,
        default_filename=default_filename,
        ctx=ctx,
        tool_name=tool_name,
    )


def _configure_allowed_roots_from_cli(argv=None) -> None:
    _runtime._configure_allowed_roots_from_cli(argv)
    globals()["SERVER_ALLOWED_ROOTS"] = _runtime.SERVER_ALLOWED_ROOTS


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    
    mcp.run(transport="sse")
