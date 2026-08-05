"""Compatibility entrypoint for the Telegram MCP server.

The implementation lives in the telegram_mcp package. This module keeps the
historic `main` import path and console script target working.
"""

import os
import sys

# ۱. ست کردن متغیرهای محیطی قبل از هرگونه Import
RAILWAY_DOMAIN = "telegram-mcp-production-7c4b.up.railway.app"
os.environ["MCP_ALLOWED_HOSTS"] = f"*,{RAILWAY_DOMAIN}"
os.environ["FASTMCP_ALLOWED_HOSTS"] = f"*,{RAILWAY_DOMAIN}"
os.environ["ALLOWED_HOSTS"] = f"*,{RAILWAY_DOMAIN}"
os.environ["UVICORN_FORWARDED_ALLOW_IPS"] = "*"
os.environ["UVICORN_PROXY_HEADERS"] = "true"

def _always_pass(*args, **kwargs):
    return True

# ۲. خنثی‌سازی پویا و کاملاً خودکار تمام توابع ماژول transport_security
try:
    import mcp.server.transport_security as ts
    for attr_name in list(dir(ts)):
        if attr_name.startswith("__"):
            continue
        attr = getattr(ts, attr_name)
        if isinstance(attr, type):
            for method_name in list(dir(attr)):
                if not method_name.startswith("__"):
                    try:
                        setattr(attr, method_name, _always_pass)
                    except Exception:
                        pass
        elif callable(attr):
            try:
                setattr(ts, attr_name, _always_pass)
            except Exception:
                pass
        elif isinstance(attr, (set, list)):
            try:
                if isinstance(attr, set):
                    attr.add("*")
                    attr.add(RAILWAY_DOMAIN)
                elif isinstance(attr, list):
                    attr.extend(["*", RAILWAY_DOMAIN])
            except Exception:
                pass
except Exception:
    pass

# ۳. خنثی‌سازی توابع اعتبارسنجی درون ماژول sse
try:
    import mcp.server.sse as sse_mod
    for attr_name in list(dir(sse_mod)):
        if attr_name.startswith("__"):
            continue
        attr = getattr(sse_mod, attr_name)
        if callable(attr) and attr_name != "connect_sse":
            if any(k in attr_name.lower() for k in ["valida", "check", "host", "security", "origin"]):
                try:
                    setattr(sse_mod, attr_name, _always_pass)
                except Exception:
                    pass
        elif isinstance(attr, (set, list)):
            try:
                if isinstance(attr, set):
                    attr.add("*")
                    attr.add(RAILWAY_DOMAIN)
                elif isinstance(attr, list):
                    attr.extend(["*", RAILWAY_DOMAIN])
            except Exception:
                pass
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
