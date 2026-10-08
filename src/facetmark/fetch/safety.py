"""Public-page HTTP transport with DNS validation at the actual connection.

Checking a hostname and then handing it back to a resolver leaves a rebinding
window. The backend below connects to the validated numeric address instead;
httpcore still owns the original origin, Host header and TLS server name.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl

import httpcore
import httpx

from ..normalize import host_excluded

# Azure's platform virtual IP is globally numbered but serves host metadata.
_PLATFORM_ADDRESSES = frozenset({"168.63.129.16"})


def public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if (not address.is_global or address.is_multicast or address.is_reserved
            or "%" in value or str(address) in _PLATFORM_ADDRESSES):
        return False
    if isinstance(address, ipaddress.IPv6Address):
        # Transition/tunnel addresses can carry an otherwise blocked IPv4
        # destination. Ordinary globally routed IPv6 remains supported.
        return not (address.ipv4_mapped or address.sixtofour or address.teredo)
    return True


async def resolve_addresses(host: str, port: int) -> list[str]:
    try:
        return [str(ipaddress.ip_address(host))]
    except ValueError:
        rows = await asyncio.get_running_loop().getaddrinfo(
            host, port, type=socket.SOCK_STREAM,
        )
        return list(dict.fromkeys(row[4][0] for row in rows))


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, *, excluded_domains=(), backend=None):
        self.excluded_domains = tuple(excluded_domains)
        self.backend = backend or httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host_excluded(host, self.excluded_domains):
            raise httpcore.ConnectError("Fetch destination is privacy-excluded")
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout if timeout is not None else None
        try:
            addresses = await asyncio.wait_for(resolve_addresses(host, port), timeout)
        except asyncio.TimeoutError as exc:
            raise httpcore.ConnectTimeout("Fetch destination DNS lookup timed out") from exc
        except (OSError, ValueError) as exc:
            raise httpcore.ConnectError("Fetch destination DNS lookup failed") from exc
        # Reject mixed public/private answers as a whole, including every
        # fallback address. A subsequent connection resolves and checks again.
        if not addresses or not all(public_address(address) for address in addresses):
            raise httpcore.ConnectError("Public-page fetch blocked a non-public destination")
        last_error = None
        for address in addresses:
            remaining = max(0.0, deadline - loop.time()) if deadline is not None else None
            if remaining == 0:
                raise httpcore.ConnectTimeout("Fetch connection timed out")
            try:
                return await self.backend.connect_tcp(
                    address, port, timeout=remaining, local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Public-page fetch does not use Unix sockets")

    async def sleep(self, seconds):
        await asyncio.sleep(seconds)


class PublicFetchTransport(httpx.AsyncHTTPTransport):
    """Apply destination policy to every HTTP request, redirects included."""

    def __init__(self, *, excluded_domains=(), max_connections=30, backend=None):
        self.excluded_domains = tuple(excluded_domains)
        # AsyncHTTPTransport delegates request/error/response adaptation to
        # this pool. httpx exposes no network_backend constructor parameter;
        # keep that one adapter detail here instead of rewriting its protocol.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(), max_connections=max_connections,
            max_keepalive_connections=max_connections,
            network_backend=PublicNetworkBackend(excluded_domains=excluded_domains, backend=backend),
        )

    async def handle_async_request(self, request):
        url = request.url
        if url.scheme not in {"http", "https"} or not url.host or url.username or url.password:
            raise httpx.ConnectError("Fetch requires an HTTP(S) URL without credentials", request=request)
        if host_excluded(url.host, self.excluded_domains):
            raise httpx.ConnectError("Fetch destination is privacy-excluded", request=request)
        return await super().handle_async_request(request)
