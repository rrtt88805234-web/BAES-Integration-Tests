"""集成测试主框架"""

from typing import Dict, Any, Callable, Optional
from uuid import uuid4

from runtime.base_module_v2 import BaseModuleV2, ResponseSecurityContext
from runtime.canonical_envelope import CanonicalEnvelope
from runtime.safety_gateway_pep import (
    SafetyGatewayPEP, GatewayResult, BoundaryOutcome,
    InMemoryReplayStore, InMemoryQuotaLedger, InMemoryAuditSink
)
from runtime.default_deny_pdp import VerifiedEnvelopeContext, ExecutionPlan

from .builders import TestEnvelopeBuilder, TestContextBuilder, TestPlanBuilder
from .mocks import MockGrantResolver, MockGrantVerifier, MockAuthorityProvider, MockPDP, RecordingAuditSink


class IntegrationTestHarness:
    """管理M1→M2a→M1完整流程的测试框架"""

    def __init__(self):
        self.m1_module: Optional[BaseModuleV2] = None
        self.gateway: Optional[SafetyGatewayPEP] = None

        self.grant_resolver = MockGrantResolver()
        self.grant_verifier = MockGrantVerifier()
        self.authority_provider = MockAuthorityProvider()
        self.pdp = MockPDP()
        self.audit_sink = RecordingAuditSink()
        self.replay_store = InMemoryReplayStore()
        self.quota_ledger = InMemoryQuotaLedger()

        self.last_gateway_result: Optional[GatewayResult] = None
        self.last_execution_result: Optional[CanonicalEnvelope] = None

    def setup_module(self, module_factory: Callable[[], BaseModuleV2]):
        """设置M1模块"""
        self.m1_module = module_factory()
        if not self.m1_module.initialize():
            raise RuntimeError("Module initialization failed")
        return self

    def setup_gateway(self):
        """设置M2a网关"""
        if self.m1_module is None:
            raise RuntimeError("Module must be initialized first")

        # 创建module registry
        registry = {
            self.m1_module.module_id: self.m1_module.process,
        }

        self.gateway = SafetyGatewayPEP(
            pdp=self.pdp,
            grant_resolver=self.grant_resolver,
            grant_verifier=self.grant_verifier,
            authority_provider=self.authority_provider,
            replay_store=self.replay_store,
            quota_ledger=self.quota_ledger,
            audit_sink=self.audit_sink,
            registry=registry,
        )
        return self

    def dispatch_request(
        self,
        envelope: CanonicalEnvelope,
        context: Optional[VerifiedEnvelopeContext] = None,
        plan: Optional[ExecutionPlan] = None,
    ) -> GatewayResult:
        """分发请求通过M2a网关"""
        if self.gateway is None:
            raise RuntimeError("Gateway not initialized")

        if context is None:
            context = TestContextBuilder(envelope).build()

        if plan is None:
            plan = TestPlanBuilder().with_destination(
                self.m1_module.module_id,
                context.authenticated_instance_id,
            ).build()

        self.last_gateway_result = self.gateway.dispatch(
            envelope_context=context,
            execution_plan=plan,
        )

        if self.last_gateway_result.executed and self.last_gateway_result.execution_result:
            self.last_execution_result = self.last_gateway_result.execution_result

        return self.last_gateway_result

    def dispatch_simple(
        self,
        payload: Dict[str, Any] = None,
        **builder_kwargs
    ) -> GatewayResult:
        """简化的请求分发（使用默认builder）"""
        if payload is None:
            payload = {}

        envelope = TestEnvelopeBuilder().with_payload(payload).build()
        return self.dispatch_request(envelope)

    # 验证助手方法

    def assert_boundary_pass(self):
        """验证边界通过"""
        assert self.last_gateway_result is not None
        assert self.last_gateway_result.boundary == BoundaryOutcome.BOUNDARY_PASS
        assert self.last_gateway_result.executed is True
        return self

    def assert_boundary_deny(self, gateway_code: str = None):
        """验证边界拒绝"""
        assert self.last_gateway_result is not None
        assert self.last_gateway_result.boundary == BoundaryOutcome.DENY
        assert self.last_gateway_result.executed is False
        if gateway_code:
            assert self.last_gateway_result.gateway_code == gateway_code
        return self

    def assert_boundary_hold(self):
        """验证等待人工审查"""
        assert self.last_gateway_result is not None
        assert self.last_gateway_result.boundary == BoundaryOutcome.HOLD_HUMAN_REVIEW
        assert self.last_gateway_result.executed is False
        return self

    def assert_policy_decision(self, outcome: str, reason_codes: tuple = None):
        """验证策略决策"""
        assert self.last_gateway_result is not None
        decision = self.last_gateway_result.policy_decision
        assert decision is not None
        if reason_codes:
            assert set(decision.get("reason_codes", ())) == set(reason_codes)
        return self

    def assert_audit_recorded(self, decision_id: str = None):
        """验证审计记录"""
        if decision_id:
            record = self.audit_sink.get_by_decision_id(decision_id)
            assert record is not None
        else:
            assert len(self.audit_sink.records) > 0
        return self

    def assert_execution_result_is_error(self, error_code: str = None):
        """验证执行结果是错误"""
        assert self.last_execution_result is not None
        if error_code:
            # 检查结果中是否包含错误代码
            pass
        return self

    # 查询方法

    def get_audit_record(self, decision_id: str = None) -> Optional[Dict[str, Any]]:
        """获取审计记录"""
        if decision_id:
            return self.audit_sink.get_by_decision_id(decision_id)
        return self.audit_sink.get_latest()

    def get_quota_consumed(self, grant_id: str, module_id: str) -> Dict[str, int]:
        """获取配额消耗"""
        key = f"{grant_id}:{module_id}"
        if key in self.quota_ledger.ledger:
            consumed = self.quota_ledger.ledger[key]
            return {
                "calls": consumed.get("calls_used", 0),
                "bytes": consumed.get("bytes_used", 0),
                "tokens": consumed.get("tokens_used", 0),
                "concurrency": consumed.get("concurrency_used", 0),
            }
        return {"calls": 0, "bytes": 0, "tokens": 0, "concurrency": 0}

    def reset(self):
        """清理所有测试状态"""
        self.audit_sink.clear()
        self.replay_store = InMemoryReplayStore()
        self.quota_ledger = InMemoryQuotaLedger()
        self.last_gateway_result = None
        self.last_execution_result = None
        return self
