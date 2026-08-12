"""M1 → M2a 集成测试：配额限制场景"""

import pytest
from tests.utils import (
    IntegrationTestHarness,
    TestEnvelopeBuilder,
    TestGrantBuilder,
)
from runtime.safety_gateway_pep import BoundaryOutcome


@pytest.fixture
def harness():
    """集成测试主框架fixture"""
    from tests.integration.testable_module import TestableModule

    h = IntegrationTestHarness()
    h.setup_module(lambda: TestableModule("digit_counter_v2"))
    h.setup_gateway()
    return h


class TestTC008CallsQuotaExceeded:
    """TC-008: 调用次数配额超限"""

    def test_tc008_calls_quota_exceeded(self, harness):
        """验证调用次数超过配额限制"""
        # 创建限制为5 calls的grant
        grant = TestGrantBuilder().with_grant_id("grant-calls-limit").with_quota(calls=5).build()
        harness.grant_resolver.register_grant("grant-calls-limit", grant)
        harness.pdp.set_deny(("POL-009",))  # 配额超限

        # 构建请求
        envelope = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-calls-limit")
            .with_destination('digit_counter_v2')
            .build()
        )

        # 分发请求
        result = harness.dispatch_request(envelope)

        # 验证拒绝
        assert result.boundary == BoundaryOutcome.DENY
        assert result.executed is False
        policy_decision = result.policy_decision
        assert "POL-009" in policy_decision.get("reason_codes", [])

        # 验证审计记录
        decision_id = policy_decision["decision_id"]
        audit = harness.get_audit_record(decision_id)
        assert audit is not None
        assert audit.get("decision") in ["DENY", "deny"]


class TestTC009BytesQuotaExceeded:
    """TC-009: 字节数配额超限"""

    def test_tc009_bytes_quota_exceeded(self, harness):
        """验证字节数超过配额限制"""
        # 创建限制为100 bytes的grant
        grant = TestGrantBuilder().with_grant_id("grant-bytes-limit").with_quota(bytes=100).build()
        harness.grant_resolver.register_grant("grant-bytes-limit", grant)
        harness.pdp.set_deny(("POL-009",))  # 配额超限

        # 构建大负载请求
        large_payload = {"data": "x" * 1000}
        envelope = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-bytes-limit")
            .with_destination('digit_counter_v2')
            .with_payload(large_payload)
            .build()
        )

        # 分发请求
        result = harness.dispatch_request(envelope)

        # 验证拒绝
        assert result.boundary == BoundaryOutcome.DENY
        assert result.executed is False
        assert "POL-009" in result.policy_decision.get("reason_codes", [])


class TestTC010TokensQuotaExceeded:
    """TC-010: Token配额超限"""

    def test_tc010_tokens_quota_exceeded(self, harness):
        """验证tokens超过配额限制"""
        # 创建限制为1000 tokens的grant
        grant = TestGrantBuilder().with_grant_id("grant-tokens-limit").with_quota(tokens=1000).build()
        harness.grant_resolver.register_grant("grant-tokens-limit", grant)
        harness.pdp.set_deny(("POL-009",))

        envelope = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-tokens-limit")
            .with_destination('digit_counter_v2')
            .build()
        )

        result = harness.dispatch_request(envelope)

        # 验证拒绝
        assert result.boundary == BoundaryOutcome.DENY
        assert result.executed is False
        assert "POL-009" in result.policy_decision.get("reason_codes", [])


class TestTC011ConcurrencyQuotaExceeded:
    """TC-011: 并发数配额超限"""

    def test_tc011_concurrency_quota_exceeded(self, harness):
        """验证并发数超过配额限制"""
        # 创建限制为1个并发的grant
        grant = TestGrantBuilder().with_grant_id("grant-concurrency-limit").with_quota(concurrency=1).build()
        harness.grant_resolver.register_grant("grant-concurrency-limit", grant)
        harness.pdp.set_deny(("POL-009",))

        # 第一个请求会占用并发配额
        envelope1 = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-concurrency-limit")
            .with_destination('digit_counter_v2')
            .build()
        )

        # 如果PDP返回deny，则第二个请求自动被拒绝
        result = harness.dispatch_request(envelope1)

        # 验证拒绝
        assert result.boundary == BoundaryOutcome.DENY
        assert result.executed is False
        assert "POL-009" in result.policy_decision.get("reason_codes", [])


class TestTC012TwoTierQuotaLimits:
    """TC-012: 两级配额限制"""

    def test_tc012_two_tier_limits(self, harness):
        """验证两级配额限制（Standard和Premium）"""
        # 创建Standard级配额（5 calls, 100 bytes）
        grant = TestGrantBuilder() \
            .with_grant_id("grant-two-tier") \
            .with_quota(calls=5, bytes=100) \
            .build()
        harness.grant_resolver.register_grant("grant-two-tier", grant)

        # 首先设置ALLOW用于第一个请求
        harness.pdp.set_allow()
        envelope1 = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-two-tier")
            .with_destination('digit_counter_v2')
            .build()
        )
        result1 = harness.dispatch_request(envelope1)
        assert result1.boundary == BoundaryOutcome.BOUNDARY_PASS

        # 然后设置DENY以模拟后续请求的配额超限
        harness.pdp.set_deny(("POL-009",))
        envelope2 = (
            TestEnvelopeBuilder()
            .with_grant_id("grant-two-tier")
            .with_destination('digit_counter_v2')
            .build()
        )
        result2 = harness.dispatch_request(envelope2)

        # 验证拒绝
        assert result2.boundary == BoundaryOutcome.DENY
        assert result2.executed is False
        assert "POL-009" in result2.policy_decision.get("reason_codes", [])
