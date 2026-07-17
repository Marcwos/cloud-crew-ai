"""FakeLLMProvider — deterministic, canned responses for testing.

Returns structured text that agents can parse into valid Proposals.
Never makes real LLM calls.
"""
from __future__ import annotations

from src.features.crew.domain.ports.llm_provider import LLMRequest, LLMResponse

# Canned responses keyed by agent name found in the system prompt.
# Each response is a JSON-like structured string that agent parsers expect.
_CANNED_RESPONSES: dict[str, str] = {
    "leslie_triage": (
        "CONSTRAINTS:\n"
        "- cost: Keep infrastructure costs predictable and under budget\n"
        "- scale: Must handle variable traffic without manual intervention\n"
        "- security: Enforce least-privilege access controls\n"
        "TASKS:\n"
        "- alan: Design compute and API strategy for variable workloads\n"
        "- edgar: Design storage, database, and caching strategy\n"
        "- hedy: Design security, identity, and secrets management\n"
        "- grace: Design monitoring, observability, and cost controls\n"
        "- vint: Design networking, event routing, and CDN strategy\n"
    ),
    "leslie_consolidate": (
        "SUMMARY: Serverless-first architecture with managed data stores, "
        "layered security, full observability, and event-driven networking.\n"
        "SERVICES: AWS Lambda, Amazon API Gateway, Amazon DynamoDB, Amazon S3, "
        "AWS IAM, Amazon Cognito, AWS Secrets Manager, Amazon CloudWatch, "
        "AWS X-Ray, Amazon VPC, Amazon EventBridge, Amazon SQS\n"
        "JUSTIFICATION:\n"
        "- AWS Lambda: Handles variable load without idle compute cost\n"
        "- Amazon API Gateway: Managed HTTP endpoint with auth integration\n"
        "- Amazon DynamoDB: NoSQL at scale with single-digit ms latency\n"
        "- Amazon S3: Durable object storage for files and artifacts\n"
        "- AWS IAM: Least-privilege roles for all services\n"
        "- Amazon Cognito: Managed user authentication and federation\n"
        "- AWS Secrets Manager: Secure rotation of credentials\n"
        "- Amazon CloudWatch: Unified metrics, logs, and alarms\n"
        "- AWS X-Ray: Distributed tracing for request visibility\n"
        "- Amazon VPC: Network isolation and private subnets\n"
        "- Amazon EventBridge: Decoupled event routing between services\n"
        "- Amazon SQS: Reliable async message queuing\n"
        "DIAGRAM_HINT: API Gateway -> Lambda -> DynamoDB/S3, with EventBridge for async flows\n"
    ),
    "alan": (
        "PROPOSAL for alan:\n"
        "SERVICES: AWS Lambda, Amazon API Gateway\n"
        "RATIONALE: Lambda suits variable-load, event-driven workloads without idle cost. "
        "API Gateway provides managed HTTP endpoints with built-in auth, throttling, and caching.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- Amazon ECS: Overkill for stateless functions; requires cluster management\n"
        "- Amazon EC2: Fixed cost, manual scaling; not cost-efficient for variable load\n"
        "TRADE_OFFS: Cold-start latency (mitigated by provisioned concurrency) vs zero idle cost\n"
    ),
    "edgar": (
        "PROPOSAL for edgar:\n"
        "SERVICES: Amazon DynamoDB, Amazon S3, Amazon ElastiCache\n"
        "RATIONALE: DynamoDB provides single-digit ms latency for operational data at scale. "
        "S3 for durable object storage. ElastiCache for session and query result caching.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- Amazon RDS: Requires cluster management; relational model may not fit all use cases\n"
        "- Amazon Aurora: Higher cost for the scale of this workload\n"
        "TRADE_OFFS: DynamoDB's eventual consistency vs RDS transactional guarantees\n"
    ),
    "hedy": (
        "PROPOSAL for hedy:\n"
        "SERVICES: AWS IAM, Amazon Cognito, AWS Secrets Manager\n"
        "RATIONALE: IAM least-privilege roles for all services. Cognito handles user auth "
        "and federation without managing passwords. Secrets Manager rotates credentials securely.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- AWS KMS standalone: Adequate only for encryption; no identity management\n"
        "- Self-managed auth: High maintenance; security risk without dedicated team\n"
        "TRADE_OFFS: Cognito lock-in vs flexibility of self-hosted identity provider\n"
    ),
    "grace": (
        "PROPOSAL for grace:\n"
        "SERVICES: Amazon CloudWatch, AWS X-Ray, AWS Budgets\n"
        "RATIONALE: CloudWatch provides unified metrics and logs. X-Ray enables distributed "
        "tracing. Budgets sets financial guardrails with alerts.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- AWS Cost Explorer alone: Reactive analysis; no proactive budget enforcement\n"
        "- Third-party APM: Additional cost and complexity; CloudWatch covers core needs\n"
        "TRADE_OFFS: CloudWatch cost increases with log volume; log sampling may be needed\n"
    ),
    "vint": (
        "PROPOSAL for vint:\n"
        "SERVICES: Amazon VPC, Amazon EventBridge, Amazon SQS\n"
        "RATIONALE: VPC provides network isolation with private subnets. EventBridge enables "
        "decoupled event routing. SQS ensures reliable async processing with DLQ support.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- Amazon SNS alone: Fan-out only; no queue semantics or retry with backoff\n"
        "- Direct Lambda invocations: Tight coupling; no retry/backoff guarantees\n"
        "TRADE_OFFS: EventBridge rules complexity vs direct invocations simplicity\n"
    ),
}

_REVIEW_TEMPLATE = (
    "REVIEW:\n"
    "REVIEWER: grace\n"
    "TARGET: alan\n"
    "CHALLENGE: For sustained workloads, Amazon ECS with Fargate may offer lower total cost "
    "than Lambda with provisioned concurrency. The cold-start mitigation adds cost.\n"
    "TRADE_OFF: Lambda flexibility vs ECS predictable pricing for constant load\n"
)

# Re-proposal canned responses, keyed by the specialist being re-proposed to.
# Only "alan" is defined: it is the only target the canned _REVIEW_TEMPLATE
# ever names (grace -> alan), so it is the only re-proposal fake mode can
# deterministically trigger. Any other target falls back to the specialist's
# ORIGINAL canned response via .get(name, _CANNED_RESPONSES[name]) below — an
# inert no-op replacement, never a KeyError.
_RE_PROPOSAL_RESPONSES: dict[str, str] = {
    "alan": (
        "PROPOSAL for alan:\n"
        "SERVICES: Amazon ECS, AWS Fargate, Amazon API Gateway\n"
        "RATIONALE: Grace's cost challenge holds for sustained traffic — provisioned "
        "concurrency erases Lambda's zero-idle advantage. ECS on Fargate gives predictable "
        "per-task pricing with no cold starts; API Gateway still fronts the service.\n"
        "ALTERNATIVES_REJECTED:\n"
        "- AWS Lambda: Cold-start mitigation via provisioned concurrency erodes the cost edge at sustained load\n"
        "- Amazon EC2: Fixed cost and manual scaling; Fargate removes instance management\n"
        "TRADE_OFFS: Higher baseline cost than scale-to-zero, in exchange for predictable latency and spend\n"
    ),
}

_SPECIALISTS = ("alan", "edgar", "hedy", "grace", "vint")


def _pick_canned_response(request: LLMRequest) -> str:
    """Select a canned response based ONLY on `request.system`.

    `request.messages` (user-supplied text) MUST NOT participate in dispatch —
    letting user input steer control flow lets a challenge like "build a code
    review tool" hijack any agent's canned response (R10). Order is
    specific-to-general so structural phrases win over incidental keyword
    overlap (R11, R13).
    """
    system_lower = request.system.lower()

    if "revising your earlier proposal" in system_lower:
        # Re-proposal: check BEFORE the generic specialist-name loop so a
        # prompt mentioning the target's name doesn't fall through to its
        # original proposal (R13).
        for name in _SPECIALISTS:
            if name in system_lower:
                return _RE_PROPOSAL_RESPONSES.get(name, _CANNED_RESPONSES[name])
    if "cross-reviewer" in system_lower:
        return _REVIEW_TEMPLATE
    if "triage" in system_lower:
        return _CANNED_RESPONSES["leslie_triage"]
    if "final architecture plan" in system_lower:
        # Consolidate: matched by a structural phrase, not "consolidat" or
        # "review" — _CONSOLIDATE_SYSTEM contains "reviews" but not
        # "consolidat", so a substring check on those words alone would fall
        # into the review branch instead (R11).
        return _CANNED_RESPONSES["leslie_consolidate"]

    for name in _SPECIALISTS:
        if name in system_lower:
            return _CANNED_RESPONSES[name]

    return "SERVICES: AWS Lambda\nRATIONALE: Default fallback response\nALTERNATIVES_REJECTED:\n- EC2: too heavy\nTRADE_OFFS: cost vs simplicity\n"


class FakeLLMProvider:
    """Deterministic LLM provider for tests. Returns canned responses, never hits a real API."""

    async def complete(self, request: LLMRequest) -> LLMResponse:
        text = _pick_canned_response(request)
        return LLMResponse(text=text, model=request.model)
