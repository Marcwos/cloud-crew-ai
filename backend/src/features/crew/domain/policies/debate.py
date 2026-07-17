"""Strong-conflict detection (R3) — pure domain rule: no LLM, no graph, no I/O.

"Strong conflict" (design §2.1): the review's challenge mentions a catalog
service that the target explicitly rejected in `alternatives_rejected`. This
detects MENTION, not defense — a documented, accepted false positive (design
§2.1, §11.3). The cost of a false positive is one extra re-proposal, bounded
to a single round by the graph's topology (D5) — never an incorrect plan.
"""
from __future__ import annotations

from src.features.crew.domain.entities.proposal import Proposal
from src.features.crew.domain.entities.review import Review
from src.features.crew.domain.policies.service_names import (
    build_index,
    canonicalize,
    mentions,
)


def find_contested_service(
    review: Review,
    target_proposal: Proposal,
    catalog_names: frozenset[str],
) -> str | None:
    """Canonical name of the service the reviewer contests and the target
    already rejected. `None` if there is no strong conflict. Deterministic:
    with several matches, the first one in `target_proposal.alternatives_rejected`
    order wins.
    """
    index = build_index(catalog_names)
    for entry in target_proposal.alternatives_rejected:
        raw, separator, _reason = entry.partition(":")
        if not separator:
            continue
        canonical = canonicalize(raw.strip(), index)
        if canonical is None:
            continue
        if mentions(canonical, review.challenge, index):
            return canonical
    return None


def has_strong_conflict(
    review: Review,
    target_proposal: Proposal,
    catalog_names: frozenset[str],
) -> bool:
    """Boolean wrapper over `find_contested_service` — the graph's router only
    needs the yes/no signal; the node that triggers `re_propose` needs the name.
    """
    return find_contested_service(review, target_proposal, catalog_names) is not None
