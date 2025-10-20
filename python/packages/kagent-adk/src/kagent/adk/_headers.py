"""Header forwarding configuration and utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

_HEADER_ENV_VAR = "KAGENT_FORWARD_HEADERS"
_STATE_PREFIX = "kagent:header:"


@dataclass(frozen=True)
class ForwardedHeader:
    """Represents a request header that should be forwarded to MCP servers."""

    name: str
    normalized_name: str
    state_key: str


def _normalize(header_name: str) -> str:
    return header_name.strip().lower()


def _build_state_key(normalized_name: str) -> str:
    return f"{_STATE_PREFIX}{normalized_name}"


@lru_cache(maxsize=1)
def get_forwarded_headers() -> tuple[ForwardedHeader, ...]:
    """Returns the configured headers that should be forwarded to MCP requests."""
    raw_value = os.getenv(_HEADER_ENV_VAR, "")
    if not raw_value:
        return ()

    headers: list[ForwardedHeader] = []
    seen: set[str] = set()
    for part in raw_value.split(","):
        header = part.strip()
        if not header:
            continue
        normalized = _normalize(header)
        if normalized in seen:
            continue
        seen.add(normalized)
        headers.append(
            ForwardedHeader(
                name=header,
                normalized_name=normalized,
                state_key=_build_state_key(normalized),
            )
        )
    return tuple(headers)


def iter_forwarded_header_names() -> Iterator[str]:
    """Yields the configured header names in insertion order."""
    for item in get_forwarded_headers():
        yield item.name


def get_state_key_for_header(header_name: str) -> str | None:
    """Returns the session state key corresponding to ``header_name`` if tracked."""
    normalized = _normalize(header_name)
    for item in get_forwarded_headers():
        if item.normalized_name == normalized:
            return item.state_key
    return None


def iter_state_items() -> Iterator[tuple[str, str]]:
    """Yields ``(header_name, state_key)`` pairs for forwarding."""
    for item in get_forwarded_headers():
        yield (item.name, item.state_key)


def has_forwarded_headers() -> bool:
    """Returns True when at least one header is configured for forwarding."""
    return bool(get_forwarded_headers())
