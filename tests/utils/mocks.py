"""M2a依赖的模拟实现"""

from typing import Any, Optional, Dict
from datetime import datetime, timezone
from uuid import uuid4
import json

from runtime.default_deny_pdp import (
    PolicyDecision, PolicyOutcome, DefaultDenyPDP,
    VerifiedEnvelopeContext, ExecutionPlan, AuthoritySnapshot
)


class MockGrantResolver:
    """授权解析器的模拟"""

    def __init__(self):
        self.grants: Dict[str, dict] = {}
        self.should_fail = False

    def register_grant(self, grant_id: str, grant_dict: dict):
        """注册一个Grant"""
        self.grants[grant_id] = grant_dict

    def resolve(self, grant_id: str) -> Optional[dict]:
        """解析Grant ID为Grant字典"""
        if self.should_fail:
            raise RuntimeError("Grant resolver is broken")
        return self.grants.get(grant_id)


class MockGrantVerifier:
    """Grant验证器的模拟"""

    def __init__(self):
        self.verified_grants: Dict[str, Any] = {}
        self.should_fail = False

    def register_verified(self, grant_id: str, verified_grant: Any):
        """注册已验证的Grant"""
        self.verified_grants[grant_id] = verified_grant

    def verify(self, grant: Any, observed_at: datetime) -> Any:
        """验证Grant"""
        if self.should_fail:
            raise RuntimeError("Grant verification failed")

        grant_id = grant.get("grant_id") if isinstance(grant, dict) else grant.grant_id
        if grant_id in self.verified_grants:
            return self.verified_grants[grant_id]

        # 返回模拟的已验证Grant
        from runtime.capability_grant import VerifiedCapabilityGrant, CapabilityGrant, capability_grant_snapshot_digest
        grant_obj = CapabilityGrant.from_dict(grant) if isinstance(grant, dict) else grant
        # 计算正确的 snapshot_digest
        correct_digest = capability_grant_snapshot_digest(grant_obj)
        return VerifiedCapabilityGrant(
            grant=grant_obj,
            snapshot_digest=correct_digest,
            evidence_id=str(uuid4()),
            verified_at=observed_at,
        )


class MockAuthorityProvider:
    """权限提供者的模拟"""

    def __init__(self):
        self.should_fail = False

    def snapshot(
        self,
        envelope_context: VerifiedEnvelopeContext,
        verified_grant: Any,
        execution_plan: ExecutionPlan,
    ) -> AuthoritySnapshot:
        """提供权限快照"""
        if self.should_fail:
            raise RuntimeError("Authority provider failed")

        from runtime.default_deny_pdp import AuthoritySnapshot
        return AuthoritySnapshot(
            available=True,
            current_permission_revision=1,
            current_revocation_revision=1,
            revoked=False,
            observed_at=datetime.now(timezone.utc),
            snapshot_id=str(uuid4()),
        )


class MockPDP(DefaultDenyPDP):
    """策略决策点的模拟"""

    def __init__(self):
        super().__init__()
        self.decision: Optional[PolicyDecision] = None
        self.should_fail = False

    def set_decision(self, decision: PolicyDecision):
        """设置要返回的决策"""
        self.decision = decision

    def set_allow(self):
        """设置允许决策"""
        self.decision = PolicyDecision(
            outcome=PolicyOutcome.ALLOW,
            reason_codes=(),
            decision_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            pdp_version="0.1.0-test",
        )

    def set_deny(self, reason_codes: tuple = ("POL-001",)):
        """设置拒绝决策"""
        self.decision = PolicyDecision(
            outcome=PolicyOutcome.DENY,
            reason_codes=reason_codes,
            decision_id=str(uuid4()),
            timestamp=datetime.now(timezone.utc),
            pdp_version="0.1.0-test",
        )

    def evaluate(self, **kwargs) -> PolicyDecision:
        """评估策略"""
        if self.should_fail:
            raise RuntimeError("PDP evaluation failed")

        if self.decision is None:
            self.set_allow()

        return self.decision


class RecordingAuditSink:
    """记录所有审计操作的Sink"""

    def __init__(self):
        self.records: list[Dict[str, Any]] = []
        self.append_attempts = 0
        self.should_fail = False

    def append(self, record: Dict[str, Any]) -> bool:
        """追加审计记录"""
        self.append_attempts += 1
        if self.should_fail:
            return False

        # 确保可JSON序列化
        encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), default=str)
        self.records.append(json.loads(encoded))
        return True

    def get_by_decision_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """按decision_id查找记录"""
        for record in self.records:
            if record.get("decision_id") == decision_id:
                return record
        return None

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """获取最新记录"""
        return self.records[-1] if self.records else None

    def get_all_by_decision(self, decision: str) -> list[Dict[str, Any]]:
        """按decision类型查找所有记录"""
        return [r for r in self.records if r.get("decision") == decision]

    def clear(self):
        """清空所有记录"""
        self.records.clear()
        self.append_attempts = 0


class MockEnvelopeFinalizer:
    """信封完成器的模拟实现"""

    def finalize(
        self,
        unsigned_wire: Dict[str, Any],
        *,
        responder_module_id: str,
        responder_instance_id: Optional[str] = None,
        responder_key_id: Optional[str] = None,
    ) -> Any:
        """完成信封并返回 Integrity 对象"""
        from runtime.canonical_envelope import Digest, Signature, Integrity

        # 创建简单的 Integrity 对象用于测试
        digest = Digest(
            algorithm="sha-256",
            value="0" * 64,  # 测试用占位符
        )
        signature = Signature(
            algorithm="ed25519",
            key_id=responder_key_id or "test-key",
            value="A" * 88,  # 测试用占位符
            signed_fields=["/"],
        )
        return Integrity(digest=digest, signature=signature)
