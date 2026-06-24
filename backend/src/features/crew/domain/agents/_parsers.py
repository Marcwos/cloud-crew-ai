"""Shared parsing helpers for extracting structured data from LLM text responses.

These parsers are intentionally simple and deterministic — they handle the canned
format produced by FakeLLMProvider and the same format real adapters should emit.
"""
from __future__ import annotations

import re


def parse_list_section(text: str, header: str) -> list[str]:
    """Extract a list of items following a header line (e.g. 'SERVICES: item1, item2')."""
    pattern = rf"^{re.escape(header)}:\s*(.+)$"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return []
    items = [item.strip() for item in match.group(1).split(",")]
    return [item for item in items if item]


def parse_multiline_section(text: str, header: str) -> list[str]:
    """Extract bullet items (lines starting with '-') under a header."""
    lines = text.splitlines()
    collecting = False
    items: list[str] = []
    for line in lines:
        if line.strip().upper().startswith(header.upper() + ":"):
            collecting = True
            continue
        if collecting:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("-"):
                items.append(stripped.lstrip("-").strip())
            elif stripped and not stripped[0].isspace() and ":" in stripped:
                # New header encountered — stop collecting
                break
    return items


def parse_single_line_section(text: str, header: str) -> str:
    """Extract the value on a single-line header (e.g. 'RATIONALE: ...')."""
    pattern = rf"^{re.escape(header)}:\s*(.+)$"
    match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def parse_kv_section(text: str, header: str) -> dict[str, str]:
    """Extract key-value pairs (lines starting with '- key: value') under a header."""
    lines = text.splitlines()
    collecting = False
    result: dict[str, str] = {}
    for line in lines:
        if line.strip().upper().startswith(header.upper() + ":"):
            collecting = True
            continue
        if collecting:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("-"):
                content = stripped.lstrip("-").strip()
                if ":" in content:
                    key, _, value = content.partition(":")
                    result[key.strip()] = value.strip()
            elif stripped and ":" in stripped and not stripped[0].isspace():
                # New section header — stop
                break
    return result
