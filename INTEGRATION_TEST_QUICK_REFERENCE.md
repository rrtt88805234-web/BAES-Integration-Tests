# M1 → M2a 集成测试框架 - 快速参考指南

## 快速启动（5分钟）

### 1. 设置基本框架
```python
from tests.integration.testable_module import TestableModule
from tests.utils import IntegrationTestHarness

# 创建harness
harness = IntegrationTestHarness()
harness.setup_module(lambda: TestableModule("digit_counter_v2"))
harness.setup_gateway()
```

### 2. 注册Grant和策略
```python
from tests.utils import TestGrantBuilder

# 创建grant
grant = TestGrantBuilder().with_grant_id("my-grant").build()
harness.grant_resolver.register_grant("my-grant", grant)

# 设置策略决策
harness.pdp.set_allow()  # 允许请求
# 或
harness.pdp.set_deny(("POL-001",))  # 拒绝请求（原因代码）
```

### 3. 发送请求和验证
```python
from tests.utils import TestEnvelopeBuilder
from runtime.safety_gateway_pep import BoundaryOutcome

# 构建请求
envelope = (
    TestEnvelopeBuilder()
    .with_payload({"data": "test"})
    .with_grant_id("my-grant")
    .build()
)

# 分发请求
result = harness.dispatch_request(envelope)

# 验证结果
assert result.boundary == BoundaryOutcome.BOUNDARY_PASS
assert result.executed is True
```

---

## 常见测试场景

### Happy Path（成功流程）
```python
# 1. 注册有效grant
grant = TestGrantBuilder().with_grant_id("valid-grant").build()
harness.grant_resolver.register_grant("valid-grant", grant)

# 2. 设置允许策略
harness.pdp.set_allow()

# 3. 分发请求
envelope = TestEnvelopeBuilder().with_grant_id("valid-grant").build()
result = harness.dispatch_request(envelope)

# 4. 验证
assert result.boundary == BoundaryOutcome.BOUNDARY_PASS
assert result.executed is True

# 5. 检查审计记录
decision_id = result.policy_decision["decision_id"]
audit = harness.get_audit_record(decision_id)
assert audit.get("decision") == "BOUNDARY_PASS"
```

### 权限拒绝
```python
# 测试：Grant不存在
fake_grant_id = "00000000-0000-0000-0000-000000000000"
harness.pdp.set_allow()  # 即使允许，也会因为grant不存在而拒绝

envelope = TestEnvelopeBuilder().with_grant_id(fake_grant_id).build()
result = harness.dispatch_request(envelope)

# 验证
assert result.boundary == BoundaryOutcome.DENY
assert result.executed is False
assert "POL-001" in result.policy_decision.get("reason_codes", [])
```

### 配额限制
```python
# 创建限制配额的grant
grant = (
    TestGrantBuilder()
    .with_grant_id("limited-grant")
    .with_quota(calls=5)  # 限制5次调用
    .build()
)
harness.grant_resolver.register_grant("limited-grant", grant)

# 模拟配额超限
harness.pdp.set_deny(("POL-009",))  # POL-009: 配额超限

envelope = TestEnvelopeBuilder().with_grant_id("limited-grant").build()
result = harness.dispatch_request(envelope)

# 验证
assert result.boundary == BoundaryOutcome.DENY
assert "POL-009" in result.policy_decision.get("reason_codes", [])
```

### 过期Grant
```python
# 创建过期的grant
expired_grant = (
    TestGrantBuilder()
    .with_grant_id("expired-grant")
    .expired()  # 设置为已过期
    .build()
)
harness.grant_resolver.register_grant("expired-grant", expired_grant)

# 拒绝因为grant已过期
harness.pdp.set_deny(("POL-001",))  # POL-001: Grant已过期

envelope = TestEnvelopeBuilder().with_grant_id("expired-grant").build()
result = harness.dispatch_request(envelope)

# 验证
assert result.boundary == BoundaryOutcome.DENY
```

---

## 策略代码参考

| 代码 | 含义 | Gateway代码 |
|------|------|-----------|
| POL-001 | Grant不存在或已过期 | GW-007 |
| POL-002 | Grant格式/内容错误 | GW-007 |
| POL-003 | Grant验证失败 | GW-010 |
| POL-004 | 不支持的Action | GW-008 |
| POL-005 | 权限不足 | GW-008 |
| POL-006 | 资源不匹配 | GW-008 |
| POL-007 | Grant已撤销 | GW-004 |
| POL-008 | 授权信息缺失 | GW-007 |
| POL-009 | 配额超限 | GW-006 |
| POL-010 | 重放检测 | GW-007 |
| POL-011 | 重放超时 | GW-007 |
| POL-012 | 幂等性冲突 | GW-005 |
| POL-013 | 基础设施错误 | GW-009 |

---

## Harness API 速查

### 基本操作
```python
# 设置模块
harness.setup_module(factory: Callable[[], BaseModuleV2])

# 设置网关
harness.setup_gateway()

# 分发请求
result = harness.dispatch_request(envelope, context=None, plan=None)

# 简化分发
result = harness.dispatch_simple(payload={"key": "value"})

# 重置状态
harness.reset()
```

### 策略配置
```python
# 允许决策
harness.pdp.set_allow()

# 拒绝决策
harness.pdp.set_deny(("POL-001", "POL-002"))

# 设置自定义决策
from runtime.default_deny_pdp import PolicyDecision, PolicyOutcome
decision = PolicyDecision(
    outcome=PolicyOutcome.ALLOW,
    reason_codes=(),
    decision_id="...",
    timestamp=datetime.now(timezone.utc),
    pdp_version="0.1.0-test"
)
harness.pdp.set_decision(decision)
```

### Grant管理
```python
# 注册grant
grant = TestGrantBuilder().build()
harness.grant_resolver.register_grant(grant_id, grant)

# 查询已注册的grant
grant = harness.grant_resolver.resolve(grant_id)
```

### 验证方法
```python
# 验证边界通过
harness.assert_boundary_pass()

# 验证边界拒绝
harness.assert_boundary_deny(gateway_code="GW-007")

# 验证等待人工审查
harness.assert_boundary_hold()

# 验证策略决策
harness.assert_policy_decision(outcome="allow", reason_codes=())

# 验证审计记录
harness.assert_audit_recorded(decision_id)

# 验证执行结果是错误
harness.assert_execution_result_is_error(error_code="MODULE-001")
```

### 查询方法
```python
# 获取审计记录
audit = harness.get_audit_record(decision_id)

# 获取配额消耗
consumed = harness.get_quota_consumed(grant_id, module_id)
# 返回: {"calls": 0, "bytes": 0, "tokens": 0, "concurrency": 0}
```

---

## Builder API 速查

### Envelope构建
```python
envelope = (
    TestEnvelopeBuilder()
    .with_action("module.invoke")
    .with_payload({"key": "value"})
    .with_grant_id("grant-id")
    .with_source("source-module", "source-instance")
    .with_destination("dest-module", "dest-instance")
    .with_task("task-id", "parent-task-id")
    .with_quota(calls=100, bytes_=1000, tokens=10000, concurrency=5)
    .with_expires_at("2026-12-31T23:59:59Z")
    .build()
)
```

### Grant构建
```python
grant = (
    TestGrantBuilder()
    .with_grant_id("grant-id")
    .with_issuer("issuer-id")
    .with_subject("subject-module")
    .with_audience("audience-module")
    .with_actions(["module.invoke"])
    .with_quota(calls=1000, bytes_=1000000, tokens=10000)
    .with_expiration("2026-12-31T23:59:59Z")
    .expired()  # 标记为过期
    .revoked()  # 标记为已撤销
    .build()
)
```

### Context构建
```python
context = (
    TestContextBuilder(envelope)
    .build()
)
```

### Plan构建
```python
plan = (
    TestPlanBuilder()
    .with_destination("dest-module", "dest-instance")
    .with_action("module.invoke")
    .with_resource("resource-type", "resource-id")
    .with_cost(calls=1, bytes_=100, tokens=50, concurrency=1)
    .build()
)
```

---

## 完整示例

### 集成测试模板
```python
import pytest
from tests.integration.testable_module import TestableModule
from tests.utils import IntegrationTestHarness, TestEnvelopeBuilder, TestGrantBuilder

@pytest.fixture
def harness():
    """Setup test harness"""
    h = IntegrationTestHarness()
    h.setup_module(lambda: TestableModule("test-module"))
    h.setup_gateway()
    return h

def test_my_scenario(harness):
    """Test specific scenario"""
    # 1. Prepare grant
    grant = TestGrantBuilder().with_grant_id("test-grant").build()
    harness.grant_resolver.register_grant("test-grant", grant)
    
    # 2. Set policy
    harness.pdp.set_allow()
    
    # 3. Build and dispatch request
    envelope = (
        TestEnvelopeBuilder()
        .with_payload({"data": "test"})
        .with_grant_id("test-grant")
        .build()
    )
    result = harness.dispatch_request(envelope)
    
    # 4. Verify
    harness.assert_boundary_pass()
    audit = harness.get_audit_record(result.policy_decision["decision_id"])
    assert audit.get("grant_id") == "test-grant"
```

---

## 故障排查

### 问题：Invalid UUID
**原因**: grant_id 必须是有效的UUID格式
```python
# 错误
.with_grant_id("my-grant")  # 字符串不是UUID

# 正确
from uuid import uuid4
.with_grant_id(str(uuid4()))  # 有效的UUID
```

### 问题：Missing integrity field
**原因**: Grant必须包含integrity字段
```python
# 自动处理
grant = TestGrantBuilder().build()  # 自动添加integrity

# 手动处理
grant_dict = TestGrantBuilder().build()
assert "integrity" in grant_dict
assert "digest" in grant_dict["integrity"]
```

### 问题：execution_result=None
**原因**: ResponseSecurityContext需要envelope_finalizer
```python
# TestableModule已正确实现
from tests.integration.testable_module import TestableModule
module = TestableModule("module-id")  # 包含envelope_finalizer
```

---

## 性能建议

1. **批量测试**: 使用循环而不是逐个创建testcase
2. **Grant复用**: 创建一次，多次使用同一个grant
3. **Reset周期**: 每个测试集的末尾调用 `harness.reset()`
4. **并发限制**: 避免在同一harness中运行并发测试

---

## 相关文件

| 文件 | 描述 |
|------|------|
| tests/integration/testable_module.py | TestableModule实现 |
| tests/utils/builders.py | 所有Builder类 |
| tests/utils/mocks.py | 模拟依赖 |
| tests/utils/harness.py | IntegrationTestHarness |
| tests/fixtures/rfc070_valid_grants.json | 预构建的fixtures |

---

**最后更新**: 2026-08-12  
**版本**: Phase 2 Release
