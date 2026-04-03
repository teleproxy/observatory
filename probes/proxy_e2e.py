"""End-to-end proxy connectivity probe.

Connects a Telethon client through a teleproxy instance using fake-TLS
transport, authenticates with a bot token, and calls get_me() to verify
the full data path works.
"""

import asyncio
import os
import time

from probes.faketls_patches import patch_telethon_faketls

patch_telethon_faketls()


def _get_required_env(name):
    """Get a required environment variable or raise."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


async def _probe_proxy_async():
    """Run the proxy E2E probe.

    Returns:
        Dict with connected/authenticated/get_me booleans and timing.
    """
    from TelethonFakeTLS import ConnectionTcpMTProxyFakeTLS
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    host = _get_required_env("PROXY_HOST")
    port = int(_get_required_env("PROXY_PORT"))
    secret = _get_required_env("PROXY_SECRET")
    domain = _get_required_env("PROXY_DOMAIN")
    bot_token = _get_required_env("TG_BOT_TOKEN")
    api_id = int(os.environ.get("TG_API_ID", "2834"))
    api_hash = os.environ.get("TG_API_HASH", "68875f756c9b437a8b916ca3de215815")

    proxy_secret = secret + domain.encode().hex()

    result = {
        "transport": "fake-tls",
        "connected": False,
        "authenticated": False,
        "get_me": False,
        "connect_ms": None,
        "auth_ms": None,
        "total_ms": None,
        "error": None,
    }

    client = TelegramClient(
        StringSession(),
        api_id,
        api_hash,
        connection=ConnectionTcpMTProxyFakeTLS,
        proxy=(host, port, proxy_secret),
    )

    total_start = time.monotonic()

    try:
        connect_start = time.monotonic()
        await asyncio.wait_for(client.connect(), timeout=30)
        result["connect_ms"] = round((time.monotonic() - connect_start) * 1000)

        if not client.is_connected():
            result["error"] = "connect() returned but client not connected"
            return result
        result["connected"] = True

        auth_start = time.monotonic()
        await asyncio.wait_for(client.sign_in(bot_token=bot_token), timeout=15)
        result["auth_ms"] = round((time.monotonic() - auth_start) * 1000)
        result["authenticated"] = True

        await asyncio.wait_for(client.get_me(), timeout=15)
        result["get_me"] = True

    except asyncio.TimeoutError:
        result["error"] = "timeout"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
    finally:
        result["total_ms"] = round((time.monotonic() - total_start) * 1000)
        try:
            await client.disconnect()
        except Exception:
            pass

    return result


def probe_proxy():
    """Run the proxy E2E probe synchronously.

    Returns:
        Dict with probe results.
    """
    return asyncio.run(_probe_proxy_async())
