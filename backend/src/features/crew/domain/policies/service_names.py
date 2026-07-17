"""Service name normalization — canonicalizes free-text mentions of AWS services
against the curated catalog, the single source of truth (design §2.4).

Pure functions only: no LLM, no graph, no I/O. The catalog is the only thing
these functions trust — nothing is compared string-to-string without going
through it first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_VENDOR_PREFIXES = ("Amazon ", "AWS ")


def core_alias(canonical: str) -> str:
    """Strip a leading vendor prefix: 'Amazon ECS' -> 'ECS'; 'AWS X-Ray' -> 'X-Ray'.

    Returns the name unchanged if it carries no recognized vendor prefix.
    """
    for prefix in _VENDOR_PREFIXES:
        if canonical.startswith(prefix):
            return canonical[len(prefix) :]
    return canonical


@dataclass(frozen=True)
class ServiceNameIndex:
    """casefold(full name) -> canonical, and casefold(core alias) -> canonical.

    Built once per `catalog_names` set via `build_index`. Relies on the catalog
    invariant that core aliases are unique (see `test_debate_policy.py`,
    `TestCatalogCoreUniqueness`) — a collision would silently drop an entry.
    """

    by_full: dict[str, str]
    by_core: dict[str, str]


def build_index(catalog_names: frozenset[str]) -> ServiceNameIndex:
    """Build a lookup index from the catalog's canonical names."""
    by_full = {name.casefold(): name for name in catalog_names}
    by_core = {core_alias(name).casefold(): name for name in catalog_names}
    return ServiceNameIndex(by_full=by_full, by_core=by_core)


def canonicalize(raw: str, index: ServiceNameIndex) -> str | None:
    """EXACT match (casefold, collapsed whitespace) against the full name or its
    core alias. NEVER substring — a substring match on free text like
    'Direct Lambda invocations' would fabricate a rejection ('AWS Lambda') that
    was never made (design §2.4). `None` if `raw` does not map to the catalog.
    """
    normalized = " ".join(raw.split()).casefold()
    if normalized in index.by_full:
        return index.by_full[normalized]
    if normalized in index.by_core:
        return index.by_core[normalized]
    return None


def mentions(canonical: str, text: str, index: ServiceNameIndex) -> bool:
    """True if `text` names `canonical` via its full name or core alias.

    Uses lookaround word boundaries (`(?<!\\w)...(?!\\w)`) instead of `\\b` so
    names with non-word characters (e.g. 'X-Ray', 'S3') still match correctly,
    and so 'Amazon EC2' does not falsely match inside 'Amazon ECS' (design §2.4).
    `index` is accepted for symmetry with `canonicalize` and to keep both
    normalization entry points on the same signature shape.
    """
    del index
    for term in (canonical, core_alias(canonical)):
        pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
