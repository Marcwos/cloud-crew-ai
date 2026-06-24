"""Tests for CuratedCatalogKnowledgeSource — RED first."""
import pytest

from src.features.crew.infrastructure.knowledge.curated_catalog import (
    CuratedCatalogKnowledgeSource,
)
from src.features.crew.domain.value_objects.service_fact import ServiceFact


EXPECTED_COMPUTE_SERVICES = {
    "AWS Lambda",
    "Amazon ECS",
    "AWS Fargate",
    "Amazon API Gateway",
    "AWS App Runner",
    "Amazon EC2",
}

EXPECTED_DATA_SERVICES = {
    "Amazon S3",
    "Amazon RDS",
    "Amazon Aurora",
    "Amazon DynamoDB",
    "Amazon ElastiCache",
}

EXPECTED_SECURITY_SERVICES = {
    "AWS IAM",
    "Amazon Cognito",
    "AWS KMS",
    "AWS Secrets Manager",
    "AWS WAF",
}

EXPECTED_MONITORING_COST_SERVICES = {
    "Amazon CloudWatch",
    "AWS Budgets",
    "AWS Cost Explorer",
    "AWS X-Ray",
}

EXPECTED_NETWORKING_SERVICES = {
    "Amazon VPC",
    "Amazon EventBridge",
    "Amazon SQS",
    "Amazon SNS",
    "Amazon CloudFront",
}


@pytest.fixture
def catalog() -> CuratedCatalogKnowledgeSource:
    return CuratedCatalogKnowledgeSource()


class TestCuratedCatalogKnowledgeSource:
    async def test_returns_service_facts(self, catalog):
        facts = await catalog.services_for("compute", "variable load")
        assert len(facts) > 0
        for f in facts:
            assert isinstance(f, ServiceFact)

    async def test_compute_domain_returns_expected_services(self, catalog):
        facts = await catalog.services_for("compute", "")
        names = {f.name for f in facts}
        assert EXPECTED_COMPUTE_SERVICES.issubset(names)

    async def test_data_domain_returns_expected_services(self, catalog):
        facts = await catalog.services_for("data", "")
        names = {f.name for f in facts}
        assert EXPECTED_DATA_SERVICES.issubset(names)

    async def test_security_domain_returns_expected_services(self, catalog):
        facts = await catalog.services_for("security", "")
        names = {f.name for f in facts}
        assert EXPECTED_SECURITY_SERVICES.issubset(names)

    async def test_monitoring_cost_domain_returns_expected_services(self, catalog):
        facts = await catalog.services_for("monitoring_cost", "")
        names = {f.name for f in facts}
        assert EXPECTED_MONITORING_COST_SERVICES.issubset(names)

    async def test_networking_domain_returns_expected_services(self, catalog):
        facts = await catalog.services_for("networking", "")
        names = {f.name for f in facts}
        assert EXPECTED_NETWORKING_SERVICES.issubset(names)

    async def test_unknown_domain_returns_empty(self, catalog):
        facts = await catalog.services_for("unknown_domain", "anything")
        assert facts == []

    async def test_all_facts_have_non_empty_when_to_use(self, catalog):
        for domain in ("compute", "data", "security", "monitoring_cost", "networking"):
            facts = await catalog.services_for(domain, "")
            for f in facts:
                assert f.when_to_use != "", f"Empty when_to_use for {f.name}"

    async def test_all_facts_have_source(self, catalog):
        facts = await catalog.services_for("compute", "")
        for f in facts:
            assert f.source != ""

    async def test_catalog_does_not_return_invented_services(self, catalog):
        """Catalog must only return well-known AWS services that are seeded."""
        all_known = (
            EXPECTED_COMPUTE_SERVICES
            | EXPECTED_DATA_SERVICES
            | EXPECTED_SECURITY_SERVICES
            | EXPECTED_MONITORING_COST_SERVICES
            | EXPECTED_NETWORKING_SERVICES
        )
        for domain in ("compute", "data", "security", "monitoring_cost", "networking"):
            facts = await catalog.services_for(domain, "")
            for f in facts:
                assert f.name in all_known, f"Unknown service '{f.name}' in domain '{domain}'"
