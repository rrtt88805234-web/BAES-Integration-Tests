"""测试数据构建器 - 创建有效的RFC-050对象和M2a输入"""

from datetime import datetime, timezone, timedelta
from uuid import uuid4
import json

from runtime.canonical_envelope import (
    CanonicalEnvelope, MessageType, get_iso8601_now, generate_message_id
)
from runtime.default_deny_pdp import (
    VerifiedEnvelopeContext, ExecutionPlan, OperationCost
)


class TestEnvelopeBuilder:
    """RFC-050 CanonicalEnvelope构建器"""

    def __init__(self):
        self.reset()

    def reset(self):
        self._message_action = "module.invoke"
        self._payload = {}
        self._grant_id = str(uuid4())
        self._source_module = "test-client"
        self._source_instance = str(uuid4())
        self._destination_module = "test-module"
        self._destination_instance = str(uuid4())
        self._task_id = str(uuid4())
        self._parent_task_id = None
        self._correlation_id = str(uuid4())
        self._quota = {"max_calls": 1000, "max_bytes": 1000000, "max_tokens": 10000, "max_concurrency": 10}
        self._expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        return self

    def with_action(self, action: str):
        self._message_action = action
        return self

    def with_payload(self, payload: dict):
        self._payload = payload
        return self

    def with_grant_id(self, grant_id: str):
        self._grant_id = grant_id
        return self

    def with_source(self, module_id: str, instance_id: str = None):
        self._source_module = module_id
        self._source_instance = instance_id or str(uuid4())
        return self

    def with_destination(self, module_id: str, instance_id: str = None):
        self._destination_module = module_id
        self._destination_instance = instance_id or str(uuid4())
        return self

    def with_task(self, task_id: str = None, parent_task_id: str = None):
        self._task_id = task_id or str(uuid4())
        self._parent_task_id = parent_task_id
        return self

    def with_quota(self, calls=None, bytes_=None, tokens=None, concurrency=None):
        if calls is not None:
            self._quota["max_calls"] = calls
        if bytes_ is not None:
            self._quota["max_bytes"] = bytes_
        if tokens is not None:
            self._quota["max_tokens"] = tokens
        if concurrency is not None:
            self._quota["max_concurrency"] = concurrency
        return self

    def with_expires_at(self, expires_at: str):
        self._expires_at = expires_at
        return self

    def build(self) -> CanonicalEnvelope:
        """构建完整的CanonicalEnvelope"""
        now = get_iso8601_now()

        envelope_dict = {
            "schema": {
                "id": "urn:baes:rfc-050:message-envelope",
                "version": "0.1.0-candidate",
                "dialect": "https://json-schema.org/draft/2020-12/schema",
            },
            "message": {
                "id": generate_message_id(),
                "type": MessageType.REQUEST.value,
                "action": self._message_action,
                "content_type": "application/json",
            },
            "task": {
                "task_id": self._task_id,
                **({"parent_task_id": self._parent_task_id} if self._parent_task_id else {}),
            },
            "bridge": {
                "binding": "not_applicable",
            },
            "workspace": {
                "binding": "not_applicable",
            },
            "source": {
                "module_id": self._source_module,
                "instance_id": self._source_instance,
                "key_id": "source-key-1",
            },
            "destination": {
                "module_id": self._destination_module,
                "instance_id": self._destination_instance,
            },
            "sequence": {
                "stream_id": str(uuid4()),
                "number": 0,
            },
            "idempotency": {
                "key": str(uuid4()),
                "ttl_seconds": 3600,
            },
            "correlation": {
                "correlation_id": self._correlation_id,
                "trace_id": str(uuid4()),
                "causation_id": str(uuid4()),
            },
            "time": {
                "created_at": now,
                "not_before": now,
                "expires_at": self._expires_at,
            },
            "nonce": generate_message_id(),
            "content": {
                "payload": self._payload,
            },
            "claims": [],
            "data_policy": {
                "classification": "internal",
                "handling": "standard",
                "log_policy": "metadata_only",
                "residency": ["GLOBAL"],
                "retention_seconds": 86400,
            },
            "permission": {
                "capability_grant_id": self._grant_id,
                "revision": 1,
                "action": self._message_action,
                "scope": {"resource_type": "module", "resource_id": "any"},
                "quota": self._quota,
            },
            "provenance": {
                "producer": self._source_module,
                "source_refs": [],
                "transformations": [],
            },
            "integrity": {
                "digest": {
                    "algorithm": "sha-256",
                    "value": "0" * 64,
                },
                "signature": {
                    "algorithm": "ed25519",
                    "key_id": "test-key",
                    "value": "A" * 88,  # Base64-encoded Ed25519 signature is 88 chars
                    "signed_fields": ["/"],
                },
            },
        }

        return CanonicalEnvelope.from_dict(envelope_dict)


class TestContextBuilder:
    """VerifiedEnvelopeContext构建器"""

    def __init__(self, envelope: CanonicalEnvelope = None):
        if envelope is None:
            envelope = TestEnvelopeBuilder().build()
        self._envelope = envelope
        self._authenticated_module = "authenticated-client"
        self._authenticated_instance = str(uuid4())
        self._authenticated_key = "auth-key-1"
        self._digest = "a" * 64
        self._evidence_id = str(uuid4())
        self._observed_at = datetime.now(timezone.utc)
        self._received_bytes = 1024

    def with_authenticated(self, module_id: str, instance_id: str = None, key_id: str = None):
        self._authenticated_module = module_id
        self._authenticated_instance = instance_id or str(uuid4())
        self._authenticated_key = key_id or "auth-key"
        return self

    def with_digest(self, digest: str):
        self._digest = digest
        return self

    def with_evidence_id(self, evidence_id: str):
        self._evidence_id = evidence_id
        return self

    def with_observed_at(self, observed_at: datetime):
        self._observed_at = observed_at
        return self

    def with_received_bytes(self, received_bytes: int):
        self._received_bytes = received_bytes
        return self

    def build(self) -> VerifiedEnvelopeContext:
        """构建VerifiedEnvelopeContext"""
        return VerifiedEnvelopeContext(
            envelope=self._envelope,
            authenticated_module_id=self._authenticated_module,
            authenticated_instance_id=self._authenticated_instance,
            authenticated_key_id=self._authenticated_key,
            envelope_digest=self._digest,
            verification_evidence_id=self._evidence_id,
            observed_at=self._observed_at,
            received_bytes=self._received_bytes,
        )


class TestPlanBuilder:
    """ExecutionPlan构建器"""

    def __init__(self):
        self._destination_module = "test-module"
        self._destination_instance = str(uuid4())
        self._action = "module.invoke"
        self._resource_type = "test-resource"
        self._resource_id = "test-resource-1"
        self._cost_calls = 1
        self._cost_bytes = 0
        self._cost_tokens = 0
        self._cost_concurrency = 1

    def with_destination(self, module_id: str, instance_id: str = None):
        self._destination_module = module_id
        self._destination_instance = instance_id or str(uuid4())
        return self

    def with_action(self, action: str):
        self._action = action
        return self

    def with_resource(self, resource_type: str, resource_id: str):
        self._resource_type = resource_type
        self._resource_id = resource_id
        return self

    def with_cost(self, calls=None, bytes_=None, tokens=None, concurrency=None):
        if calls is not None:
            self._cost_calls = calls
        if bytes_ is not None:
            self._cost_bytes = bytes_
        if tokens is not None:
            self._cost_tokens = tokens
        if concurrency is not None:
            self._cost_concurrency = concurrency
        return self

    def build(self) -> ExecutionPlan:
        """构建ExecutionPlan"""
        return ExecutionPlan(
            destination_module_id=self._destination_module,
            destination_instance_id=self._destination_instance,
            action=self._action,
            resource_type=self._resource_type,
            resource_id=self._resource_id,
            cost=OperationCost(
                calls=self._cost_calls,
                bytes=self._cost_bytes,
                tokens=self._cost_tokens,
                concurrency=self._cost_concurrency,
            ),
        )


class TestGrantBuilder:
    """CapabilityGrant构建器"""

    def __init__(self):
        self._grant_id = str(uuid4())
        self._issuer = "test-issuer"
        self._subject_module = "test-subject"
        self._audience = "test-audience"
        self._actions = ["module.invoke"]
        self._quota = {"max_calls": 1000, "max_bytes": 1000000, "max_tokens": 10000, "max_concurrency": 10}
        self._expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        self._is_delegable = False
        self._revocation_status = None  # "active" | "revoked"
        self._is_expired = False

    def with_grant_id(self, grant_id: str):
        self._grant_id = grant_id
        return self

    def with_issuer(self, issuer: str):
        self._issuer = issuer
        return self

    def with_subject(self, module_id: str):
        self._subject_module = module_id
        return self

    def with_audience(self, audience: str):
        self._audience = audience
        return self

    def with_actions(self, actions: list):
        self._actions = actions
        return self

    def with_quota(self, calls=None, bytes_=None, tokens=None, concurrency=None):
        if calls is not None:
            self._quota["max_calls"] = calls
        if bytes_ is not None:
            self._quota["max_bytes"] = bytes_
        if tokens is not None:
            self._quota["max_tokens"] = tokens
        if concurrency is not None:
            self._quota["max_concurrency"] = concurrency
        return self

    def with_expiration(self, expires_at: str):
        self._expires_at = expires_at
        return self

    def expired(self):
        """创建已过期的Grant"""
        # 设置 issued_at 为2小时前，expires_at 为1小时前
        # 这样 not_before（issued_at）会早于 expires_at
        past_issued = datetime.now(timezone.utc) - timedelta(hours=2)
        self._expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        # 需要重新计算发行时间以确保 not_before < expires_at
        # 但这会影响构建逻辑，所以我们在 build() 中处理
        self._is_expired = True
        return self

    def revoked(self):
        """创建被撤销的Grant"""
        self._revocation_status = "revoked"
        return self

    def build(self) -> dict:
        """构建Grant字典（RFC-070格式，用于grant_resolver返回）"""
        # 处理过期 grant：issued_at 在过期时间之后
        if self._is_expired:
            issued_time = datetime.now(timezone.utc) - timedelta(hours=1)
            expires_time = datetime.now(timezone.utc) - timedelta(hours=0.5)
        else:
            issued_time = datetime.now(timezone.utc)
            expires_time = datetime.fromisoformat(self._expires_at.replace("Z", "+00:00"))

        now_iso = issued_time.isoformat().replace("+00:00", "Z")
        expires_iso = expires_time.isoformat().replace("+00:00", "Z")

        # 构建核心 grant（添加临时的 integrity 以便能够创建对象）
        grant_core = {
            "schema_version": "0.1.0-candidate",
            "grant_id": self._grant_id,
            "issuer": {
                "authority_id": "baes.policy.authority",
                "key_id": "key:baes-policy-root"
            },
            "subject": {
                "module_id": self._subject_module,
                "instance_id": str(uuid4())
            },
            "audience": [self._audience],
            "actions": self._actions,
            "scope": {"resource_type": "module", "resource_id": self._audience},  # 必须匹配 audience
            "quota": self._quota,
            "issued_at": now_iso,
            "not_before": now_iso,
            "expires_at": expires_iso,
            "ttl_seconds": 3600,
            "permission_revision": 1,
            "delegable": self._is_delegable,
            "nonce": "A" * 44,
            "revocation": {
                "list_uri": "urn:baes:revocation:test",
                "revision": 1
            },
            "constraints": {
                "require_human_review": False,
                "allowed_data_classifications": ["internal"]
            },
            "integrity": {
                "digest": {
                    "algorithm": "sha-256",
                    "value": "0" * 64  # 临时占位符
                },
                "signature": {
                    "algorithm": "ed25519",
                    "key_id": "key:baes-policy-root",
                    "value": "B" * 88,
                    "signed_fields": [
                        "/schema_version", "/grant_id", "/issuer", "/subject",
                        "/audience", "/actions", "/scope", "/quota",
                        "/issued_at", "/not_before", "/expires_at",
                        "/ttl_seconds", "/permission_revision", "/delegable",
                        "/nonce", "/revocation", "/constraints"
                    ]
                }
            }
        }

        # 计算正确的 digest
        from runtime.capability_grant import CapabilityGrant, capability_grant_snapshot_digest
        grant_obj = CapabilityGrant.from_dict(grant_core)
        correct_digest = capability_grant_snapshot_digest(grant_obj)

        # 更新 integrity 信息中的 digest
        grant_core["integrity"]["digest"]["value"] = correct_digest

        return grant_core
