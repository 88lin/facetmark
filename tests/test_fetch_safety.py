"""Destination checks with simulated DNS and socket streams; no real network."""

from __future__ import annotations

from collections import deque

import httpcore
import httpx
import pytest

from facetmark.fetch import safety
from facetmark.fetch.client import FetchPolicy, Verdict, fetch_many
from facetmark.fetch.robots import RobotsCache


class RecordingStream(httpcore.AsyncMockStream):
    def __init__(self, response):
        super().__init__([response])
        self.writes = []
        self.server_hostname = None

    async def write(self, buffer, timeout=None):
        self.writes.append(buffer)

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        self.server_hostname = server_hostname
        return self


class RecordingBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, *responses):
        self.responses = deque(responses)
        self.connected = []
        self.streams = []

    async def connect_tcp(self, host, port, **kwargs):
        self.connected.append((host, port))
        stream = RecordingStream(self.responses.popleft())
        self.streams.append(stream)
        return stream


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.1.2.3", "172.20.0.1", "192.168.1.1", "169.254.169.254",
    "100.100.100.200", "168.63.129.16", "0.0.0.0", "224.0.0.1", "192.0.2.1",
    "::1", "fe80::1", "fc00::1", "ff02::1", "::ffff:127.0.0.1", "2002:7f00:1::",
])
def test_local_reserved_metadata_and_tunnel_addresses_are_not_public(address):
    assert not safety.public_address(address)


@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_globally_routed_addresses_are_supported(address):
    assert safety.public_address(address)


async def test_dns_answer_is_pinned_and_keeps_original_host_and_tls_name(monkeypatch):
    lookups = []

    async def resolve(host, port):
        lookups.append((host, port))
        # A second lookup would be unsafe; the TCP backend must receive the
        # first checked numeric address instead of resolving this name again.
        return ["93.184.216.34"] if len(lookups) == 1 else ["127.0.0.1"]

    monkeypatch.setattr(safety, "resolve_addresses", resolve)
    backend = RecordingBackend(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
    transport = safety.PublicFetchTransport(backend=backend)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        response = await client.get("https://public.test/article")
    assert response.text == "ok"
    assert lookups == [("public.test", 443)]
    assert backend.connected == [("93.184.216.34", 443)]
    assert backend.streams[0].server_hostname == "public.test"
    assert b"Host: public.test" in b"".join(backend.streams[0].writes)


async def test_mixed_dns_answers_fail_before_opening_any_socket(monkeypatch):
    async def resolve(host, port):
        return ["93.184.216.34", "10.0.0.1"]

    monkeypatch.setattr(safety, "resolve_addresses", resolve)
    backend = RecordingBackend()
    transport = safety.PublicFetchTransport(backend=backend)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(httpx.ConnectError, match="non-public"):
            await client.get("https://mixed.test")
    assert backend.connected == []


@pytest.mark.parametrize("destination", ["http://127.0.0.1/admin", "http://metadata.test/latest"])
async def test_each_redirect_destination_is_checked(monkeypatch, destination):
    async def resolve(host, port):
        return ["93.184.216.34"] if host == "public.test" else ["169.254.169.254"]

    monkeypatch.setattr(safety, "resolve_addresses", resolve)
    redirect = f"HTTP/1.1 302 Found\r\nLocation: {destination}\r\nContent-Length: 0\r\n\r\n".encode()
    backend = RecordingBackend(redirect)
    transport = safety.PublicFetchTransport(backend=backend)
    async with httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=True) as client:
        with pytest.raises(httpx.ConnectError, match="non-public"):
            await client.get("http://public.test/article")
    assert backend.connected == [("93.184.216.34", 80)]


async def test_privacy_excluded_redirect_is_rejected_before_dns(monkeypatch):
    lookups = []

    async def resolve(host, port):
        lookups.append(host)
        return ["93.184.216.34"]

    monkeypatch.setattr(safety, "resolve_addresses", resolve)
    backend = RecordingBackend(
        b"HTTP/1.1 302 Found\r\nLocation: https://secret.test/page\r\nContent-Length: 0\r\n\r\n",
    )
    transport = safety.PublicFetchTransport(backend=backend, excluded_domains=("secret.test",))
    async with httpx.AsyncClient(transport=transport, trust_env=False, follow_redirects=True) as client:
        with pytest.raises(httpx.ConnectError, match="privacy-excluded"):
            await client.get("https://public.test/article")
    assert lookups == ["public.test"]
    assert len(backend.connected) == 1


async def test_robots_redirect_cannot_reach_private_host(monkeypatch):
    async def resolve(host, port):
        return ["93.184.216.34"] if host == "public.test" else ["10.0.0.1"]

    monkeypatch.setattr(safety, "resolve_addresses", resolve)
    backend = RecordingBackend(
        b"HTTP/1.1 302 Found\r\nLocation: http://private.test/robots.txt\r\nContent-Length: 0\r\n\r\n",
    )
    transport = safety.PublicFetchTransport(backend=backend)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        rules = await RobotsCache("facetmark").get(client, "http://public.test/article")
    assert rules.unreachable
    assert backend.connected == [("93.184.216.34", 80)]
    assert b"GET /robots.txt" in b"".join(backend.streams[0].writes)


async def test_credential_urls_are_not_sent_to_the_network():
    backend = RecordingBackend()
    transport = safety.PublicFetchTransport(backend=backend)
    async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
        with pytest.raises(httpx.ConnectError, match="without credentials"):
            await client.get("https://name:password@public.test/article")
    assert backend.connected == []


async def test_owned_fetch_client_rejects_loopback_without_socket_or_proxy(monkeypatch):
    sockets = []

    async def connect(*args, **kwargs):
        sockets.append((args, kwargs))
        raise AssertionError("No socket should be opened for loopback")

    monkeypatch.setattr(httpcore.AnyIOBackend, "connect_tcp", connect)
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.test:8080")
    result = await fetch_many(["http://127.0.0.1/private"], policy=FetchPolicy())
    assert result.results[0].verdict is Verdict.UNREACHABLE
    assert not result.results[0].should_defer_to_browser
    assert sockets == []
