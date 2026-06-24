"""CuratedCatalogKnowledgeSource — real starter implementation backed by an in-code AWS catalog.

This is the source of truth for the MVP. Every service listed here is a real, well-known
AWS service with accurate when_to_use text. Agents must ONLY recommend services from this
catalog — never invent services.

Extend this catalog with more services before enabling RAG.
"""
from __future__ import annotations

from src.features.crew.domain.value_objects.service_fact import ServiceFact

_SOURCE = "curated_catalog_v1"

# ---------------------------------------------------------------------------
# Catalog — keyed by domain
# ---------------------------------------------------------------------------
_CATALOG: dict[str, list[ServiceFact]] = {
    "compute": [
        ServiceFact(
            name="AWS Lambda",
            category="compute",
            when_to_use=(
                "Event-driven, short-lived workloads with unpredictable or variable traffic. "
                "Ideal when you want zero idle cost, sub-second billing, and automatic scaling "
                "from zero to thousands of concurrent executions. Best for API backends, "
                "file processing triggers, scheduled tasks, and data transformation pipelines."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon ECS",
            category="compute",
            when_to_use=(
                "Long-running containerized services that require persistent connections, "
                "predictable latency, or sustained throughput. Use when your workload does not "
                "fit Lambda's 15-minute limit or needs fine-grained control over container "
                "networking and task placement. Pair with Fargate to eliminate EC2 management."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS Fargate",
            category="compute",
            when_to_use=(
                "Serverless compute engine for containers running on ECS or EKS. Use when you "
                "want to run containers without managing EC2 instances. Ideal for microservices "
                "with variable but sustained traffic, and when infrastructure management overhead "
                "should be minimized. Pay per vCPU and memory consumed by the task."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon API Gateway",
            category="compute",
            when_to_use=(
                "Managed HTTP/REST/WebSocket API endpoint. Use to expose Lambda functions or "
                "backend services as APIs with built-in auth (Cognito, IAM, Lambda authorizer), "
                "throttling, caching, and usage plans. Eliminates the need to manage a reverse "
                "proxy or load balancer for API workloads."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS App Runner",
            category="compute",
            when_to_use=(
                "Fully managed service to deploy containerized web applications and APIs directly "
                "from source code or container image. Use when you want the simplest path to "
                "running a web service without configuring load balancers, clusters, or VPCs. "
                "Good for small to medium web apps that need automatic scaling."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon EC2",
            category="compute",
            when_to_use=(
                "Virtual machines with full OS control. Use when workloads require persistent "
                "state, specific OS configuration, custom networking, GPU/FPGA hardware, or "
                "software that cannot run in containers. Suitable for lift-and-shift migrations, "
                "HPC, gaming servers, and workloads with licensing tied to physical hardware."
            ),
            source=_SOURCE,
        ),
    ],
    "data": [
        ServiceFact(
            name="Amazon S3",
            category="data",
            when_to_use=(
                "Durable, highly available object storage for any volume of data. Use for "
                "storing files, backups, static website assets, data lake raw zones, ML training "
                "datasets, and application artifacts. Supports lifecycle policies, versioning, "
                "replication, and fine-grained access control."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon RDS",
            category="data",
            when_to_use=(
                "Managed relational database service supporting MySQL, PostgreSQL, MariaDB, "
                "Oracle, and SQL Server. Use when your workload requires ACID transactions, "
                "complex SQL queries, or existing relational schemas. Handles backups, patching, "
                "and Multi-AZ failover automatically."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon Aurora",
            category="data",
            when_to_use=(
                "MySQL/PostgreSQL-compatible relational database with up to 5x performance over "
                "standard MySQL. Use for high-throughput OLTP workloads, read-heavy applications "
                "needing read replicas, or when you need Aurora Serverless for variable database "
                "load. Better throughput than RDS for demanding workloads."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon DynamoDB",
            category="data",
            when_to_use=(
                "Fully managed NoSQL database delivering single-digit millisecond latency at any "
                "scale. Use for key-value or document data models, session stores, gaming "
                "leaderboards, IoT telemetry, and e-commerce carts. Supports DynamoDB Streams "
                "for change data capture and Global Tables for multi-region replication."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon ElastiCache",
            category="data",
            when_to_use=(
                "Managed in-memory caching using Redis or Memcached. Use to reduce database "
                "read latency by caching frequently accessed data, session state, computed "
                "results, or API responses. Redis mode supports pub/sub, sorted sets, "
                "and persistence; Memcached for pure horizontal caching."
            ),
            source=_SOURCE,
        ),
    ],
    "security": [
        ServiceFact(
            name="AWS IAM",
            category="security",
            when_to_use=(
                "Identity and access management for all AWS resources. Use to define least-privilege "
                "roles, policies, and permission boundaries for users, services, and cross-account "
                "access. IAM roles should be the default mechanism for granting AWS service "
                "permissions — avoid long-lived access keys."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon Cognito",
            category="security",
            when_to_use=(
                "Managed user authentication, authorization, and federation for web and mobile "
                "apps. Use when you need sign-up/sign-in, MFA, social identity federation "
                "(Google, Apple, Facebook), or enterprise SSO via SAML/OIDC without building "
                "an auth system from scratch."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS KMS",
            category="security",
            when_to_use=(
                "Managed key management for creating and controlling encryption keys. Use when "
                "data must be encrypted at rest or in transit with customer-managed keys, "
                "compliance requires key rotation auditing, or services need envelope encryption. "
                "Integrates natively with S3, RDS, DynamoDB, and Lambda."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS Secrets Manager",
            category="security",
            when_to_use=(
                "Secure storage and automatic rotation of secrets such as database credentials, "
                "API keys, and OAuth tokens. Use to eliminate hardcoded secrets in code or "
                "config files, enforce rotation policies, and audit secret access via CloudTrail. "
                "Integrates with Lambda and ECS for runtime secret injection."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS WAF",
            category="security",
            when_to_use=(
                "Web application firewall to protect HTTP endpoints from OWASP Top 10 threats, "
                "SQL injection, XSS, and bot traffic. Use in front of API Gateway, CloudFront, "
                "or Application Load Balancer. Define managed rule groups or custom rules based "
                "on IP reputation, rate limiting, and request patterns."
            ),
            source=_SOURCE,
        ),
    ],
    "monitoring_cost": [
        ServiceFact(
            name="Amazon CloudWatch",
            category="monitoring_cost",
            when_to_use=(
                "Unified observability service for metrics, logs, and alarms across all AWS "
                "services. Use to collect application and infrastructure telemetry, set "
                "threshold-based alarms, create dashboards, and trigger automated responses "
                "to operational events. The default observability backbone for any AWS workload."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS Budgets",
            category="monitoring_cost",
            when_to_use=(
                "Proactive cost and usage monitoring with configurable alerts. Use to set "
                "monthly spend limits per service or overall, receive notifications before "
                "budgets are exceeded, and trigger automated cost-control actions via SNS or "
                "Lambda. Essential for teams with hard cost constraints."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS Cost Explorer",
            category="monitoring_cost",
            when_to_use=(
                "Historical cost and usage analysis to understand spending patterns and identify "
                "optimization opportunities. Use after deployments to analyze cost by service, "
                "tag, or time period. Provides rightsizing recommendations for EC2 and "
                "Reserved Instance purchase planning."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="AWS X-Ray",
            category="monitoring_cost",
            when_to_use=(
                "Distributed tracing for debugging and analyzing microservices and serverless "
                "applications. Use to trace requests end-to-end across Lambda, ECS, API Gateway, "
                "and other services, identify latency bottlenecks, and visualize service maps. "
                "Integrates with CloudWatch for correlated logs and traces."
            ),
            source=_SOURCE,
        ),
    ],
    "networking": [
        ServiceFact(
            name="Amazon VPC",
            category="networking",
            when_to_use=(
                "Virtual private network isolation within AWS. Use to segment resources into "
                "public and private subnets, control inbound/outbound traffic with security "
                "groups and network ACLs, establish VPN or Direct Connect to on-premises, "
                "and enable VPC endpoints for private access to AWS services."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon EventBridge",
            category="networking",
            when_to_use=(
                "Serverless event bus for routing events between AWS services, SaaS providers, "
                "and custom applications. Use to decouple producers from consumers, implement "
                "event-driven architectures, schedule cron-based tasks, and build reactive "
                "workflows without polling. Supports content-based filtering and archive/replay."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon SQS",
            category="networking",
            when_to_use=(
                "Managed message queuing for decoupling and scaling microservices. Use for "
                "reliable async processing with at-least-once delivery, dead-letter queues "
                "for failed messages, and backpressure handling. FIFO queues guarantee exactly-once "
                "processing. Integrates directly with Lambda for event-driven consumption."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon SNS",
            category="networking",
            when_to_use=(
                "Managed pub/sub messaging for fan-out to multiple subscribers. Use to broadcast "
                "notifications to SQS queues, Lambda functions, HTTP endpoints, email, or SMS "
                "simultaneously. Ideal for alert broadcasting, push notifications, and "
                "decoupled event distribution across multiple consumers."
            ),
            source=_SOURCE,
        ),
        ServiceFact(
            name="Amazon CloudFront",
            category="networking",
            when_to_use=(
                "Global content delivery network (CDN) for low-latency delivery of static and "
                "dynamic content. Use to accelerate web applications, APIs, and media streaming "
                "by caching at edge locations close to users. Integrates with S3, API Gateway, "
                "and WAF for security. Reduces origin load and improves global performance."
            ),
            source=_SOURCE,
        ),
    ],
}


class CuratedCatalogKnowledgeSource:
    """Real starter KnowledgeSource backed by an in-code curated AWS catalog.

    Returns only well-known, verified AWS services. Never invents services.
    The `need` parameter is currently unused (filtering will be added when RAG replaces this).
    """

    async def services_for(self, domain: str, need: str) -> list[ServiceFact]:
        """Return all ServiceFacts for the given domain.

        Returns an empty list for unknown domains — never raises.
        """
        return list(_CATALOG.get(domain, []))

    def all_service_names(self) -> set[str]:
        """Return every service name across all domains in the catalog.

        Used by the orchestrator to ground the FinalPlan against the full catalog.
        """
        return {fact.name for facts in _CATALOG.values() for fact in facts}
