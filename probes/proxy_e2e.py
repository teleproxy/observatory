"""End-to-end proxy connectivity probe.

Connects a Telethon client through a teleproxy instance, authenticates
with a bot token, and calls get_me() to verify the full data path.

Supports two transport modes:
  - obfs2 (dd-prefix): always tested when PROXY_SECRET is set
  - fake-TLS (ee-prefix): tested when PROXY_DOMAIN is also set
"""

import asyncio
import os
import time


def _get_required_env(name):
    """Get a required environment variable or raise."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


async def _test_transport(host, port, proxy_tuple, connection_cls,
                          bot_token, api_id, api_hash, transport_label):
    """Test a single transport mode through the proxy.

    Returns:
        Dict with connected/authenticated/get_me booleans and timing.
    """
    from telethon import TelegramClient
    from telethon.sessions import StringSession

    result = {
        "transport": transport_label,
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
        connection=connection_cls,
        proxy=proxy_tuple,
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


async def _probe_proxy_async():
    """Run proxy E2E probes for all available transports.

    Returns:
        List of result dicts (one per transport tested).
    """
    from telethon.network.connection import (
        ConnectionTcpMTProxyRandomizedIntermediate,
    )

    host = _get_required_env("PROXY_HOST")
    port = int(_get_required_env("PROXY_PORT"))
    secret = _get_required_env("PROXY_SECRET")
    bot_token = _get_required_env("TG_BOT_TOKEN")
    api_id = int(os.environ.get("TG_API_ID") or "2834")
    api_hash = os.environ.get("TG_API_HASH") or "68875f756c9b437a8b916ca3de215815"
    domain = os.environ.get("PROXY_DOMAIN") or None

    results = []

    # obfs2 (dd-prefix, randomized padding)
    obfs2_proxy = (host, port, "dd" + secret)
    obfs2_result = await _test_transport(
        host, port, obfs2_proxy,
        ConnectionTcpMTProxyRandomizedIntermediate,
        bot_token, api_id, api_hash, "obfs2",
    )
    results.append(obfs2_result)

    # fake-TLS (ee-prefix) — only if domain is configured
    if domain:
        from probes.faketls_patches import patch_telethon_faketls
        patch_telethon_faketls()
        from TelethonFakeTLS import ConnectionTcpMTProxyFakeTLS

        faketls_secret = secret + domain.encode().hex()
        faketls_proxy = (host, port, faketls_secret)
        faketls_result = await _test_transport(
            host, port, faketls_proxy,
            ConnectionTcpMTProxyFakeTLS,
            bot_token, api_id, api_hash, "fake-tls",
        )
        results.append(faketls_result)

    return results


def probe_proxy():
    """Run the proxy E2E probes synchronously.

    Returns:
        List of result dicts (one per transport tested).
    """
    return asyncio.run(_probe_proxy_async())
