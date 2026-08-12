#!/usr/bin/env python3
"""Integration test framework verification script"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_setup():
    """Test basic framework setup"""
    print("=" * 60)
    print("Test 1: Basic Framework Import")
    print("=" * 60)

    try:
        from tests.utils import (
            TestEnvelopeBuilder,
            TestGrantBuilder,
            TestContextBuilder,
            TestPlanBuilder,
            IntegrationTestHarness,
        )
        print("[PASS] All builder and harness imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_envelope_building():
    """Test envelope construction"""
    print("\n" + "=" * 60)
    print("Test 2: RFC-050 Envelope Construction")
    print("=" * 60)

    try:
        from tests.utils import TestEnvelopeBuilder
        from uuid import uuid4

        grant_id = str(uuid4())
        envelope = (
            TestEnvelopeBuilder()
            .with_payload({"text": "hello"})
            .with_grant_id(grant_id)
            .with_destination("digit_counter_v2")
            .build()
        )

        # Verify key fields
        assert envelope.message.action == "module.invoke"
        assert envelope.content.payload == {"text": "hello"}
        assert envelope.destination.module_id == "digit_counter_v2"
        assert envelope.permission.capability_grant_id == grant_id

        print("[PASS] Envelope construction successful")
        print(f"   - action: {envelope.message.action}")
        print(f"   - grant_id: {envelope.permission.capability_grant_id}")
        print(f"   - destination: {envelope.destination.module_id}")
        return True
    except Exception as e:
        print(f"[FAIL] Envelope construction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_grant_building():
    """Test Grant construction"""
    print("\n" + "=" * 60)
    print("Test 3: RFC-070 Grant Construction")
    print("=" * 60)

    try:
        from tests.utils import TestGrantBuilder
        from uuid import uuid4

        # Build normal grant
        grant_id = str(uuid4())
        grant = TestGrantBuilder().with_grant_id(grant_id).build()

        # Verify key fields
        assert grant["grant_id"] == grant_id
        assert grant["actions"] == ["module.invoke"]
        assert "integrity" in grant
        assert "digest" in grant["integrity"]
        assert "signature" in grant["integrity"]

        print("[PASS] Grant construction successful")
        print(f"   - grant_id: {grant['grant_id']}")
        print(f"   - actions: {grant['actions']}")
        print(f"   - digest: {grant['integrity']['digest']['value'][:16]}...")

        # Build expired grant
        expired_grant_id = str(uuid4())
        expired_grant = TestGrantBuilder().with_grant_id(expired_grant_id).expired().build()
        print("[PASS] Expired grant construction successful")
        print(f"   - expires_at: {expired_grant['expires_at']}")

        return True
    except Exception as e:
        print(f"[FAIL] Grant construction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_harness_setup():
    """Test Harness setup"""
    print("\n" + "=" * 60)
    print("Test 4: IntegrationTestHarness Setup")
    print("=" * 60)

    try:
        from tests.integration.testable_module import TestableModule
        from tests.utils import IntegrationTestHarness

        harness = IntegrationTestHarness()
        harness.setup_module(lambda: TestableModule("digit_counter_v2"))
        harness.setup_gateway()

        assert harness.m1_module is not None
        assert harness.gateway is not None
        assert harness.m1_module.module_id == "digit_counter_v2"

        print("[PASS] Harness setup successful")
        print(f"   - module_id: {harness.m1_module.module_id}")
        print(f"   - module_state: {harness.m1_module._state.value}")
        print(f"   - gateway initialized: {harness.gateway is not None}")

        return True
    except Exception as e:
        print(f"[FAIL] Harness setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_happy_path_flow():
    """Test complete Happy Path flow"""
    print("\n" + "=" * 60)
    print("Test 5: TC-001 Happy Path Complete Flow")
    print("=" * 60)

    try:
        from tests.integration.testable_module import TestableModule
        from tests.utils import IntegrationTestHarness, TestEnvelopeBuilder, TestGrantBuilder
        from runtime.safety_gateway_pep import BoundaryOutcome

        # Setup harness
        harness = IntegrationTestHarness()
        harness.setup_module(lambda: TestableModule("digit_counter_v2"))
        harness.setup_gateway()

        # Load fixture grant
        with open('tests/fixtures/rfc070_valid_grants.json') as f:
            fixtures = json.load(f)
            fixture_grant = fixtures['module_invoke_standard']
            grant_id = fixture_grant['grant_id']

        # Register grant
        harness.grant_resolver.register_grant(grant_id, fixture_grant)
        harness.pdp.set_allow()

        # Build request
        envelope = (
            TestEnvelopeBuilder()
            .with_payload({"text": "abc"})
            .with_grant_id(grant_id)
            .with_destination('digit_counter_v2')
            .build()
        )

        # Dispatch request
        result = harness.dispatch_request(envelope)

        # Verify result
        assert result.boundary == BoundaryOutcome.BOUNDARY_PASS, f"Expected BOUNDARY_PASS, got {result.boundary}"
        assert result.executed is True, "Expected executed=True"
        assert result.policy_decision is not None, "Expected policy_decision"

        # Verify audit record
        decision_id = result.policy_decision["decision_id"]
        audit_record = harness.get_audit_record(decision_id)
        assert audit_record is not None, "Expected audit record"
        assert audit_record.get("decision") in ["BOUNDARY_PASS", "allow"], \
            f"Expected BOUNDARY_PASS decision, got {audit_record.get('decision')}"

        print("[PASS] Happy Path flow test passed")
        print(f"   - boundary: {result.boundary}")
        print(f"   - executed: {result.executed}")
        print(f"   - decision_id: {decision_id}")
        print(f"   - audit_decision: {audit_record.get('decision')}")

        return True
    except Exception as e:
        print(f"[FAIL] Happy Path flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permission_denial():
    """Test permission denial scenario"""
    print("\n" + "=" * 60)
    print("Test 6: TC-003 Permission Denial Scenario")
    print("=" * 60)

    try:
        from tests.integration.testable_module import TestableModule
        from tests.utils import IntegrationTestHarness, TestEnvelopeBuilder
        from runtime.safety_gateway_pep import BoundaryOutcome

        # Setup harness
        harness = IntegrationTestHarness()
        harness.setup_module(lambda: TestableModule("digit_counter_v2"))
        harness.setup_gateway()

        # Test: non-existent grant
        fake_grant_id = "00000000-0000-0000-0000-000000000000"
        harness.pdp.set_allow()

        envelope = (
            TestEnvelopeBuilder()
            .with_grant_id(fake_grant_id)
            .with_destination('digit_counter_v2')
            .build()
        )

        result = harness.dispatch_request(envelope)

        # Verify denial
        assert result.boundary == BoundaryOutcome.DENY, f"Expected DENY, got {result.boundary}"
        assert result.executed is False, "Expected executed=False"
        assert "POL-001" in result.policy_decision.get("reason_codes", []), \
            f"Expected POL-001 in reason_codes, got {result.policy_decision.get('reason_codes')}"

        print("[PASS] Permission denial test passed")
        print(f"   - boundary: {result.boundary}")
        print(f"   - executed: {result.executed}")
        print(f"   - reason_codes: {result.policy_decision.get('reason_codes')}")

        return True
    except Exception as e:
        print(f"[FAIL] Permission denial test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("M1 -> M2a Integration Test Framework Verification")
    print("=" * 60 + "\n")

    tests = [
        test_basic_setup,
        test_envelope_building,
        test_grant_building,
        test_harness_setup,
        test_happy_path_flow,
        test_permission_denial,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\nWarning: Test exception: {e}")
            results.append(False)

    # Generate report
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\n[PASS] Passed: {passed}/{total}")
    print(f"[FAIL] Failed: {total - passed}/{total}")

    if all(results):
        print("\nSUCCESS: All verification tests passed! Integration test framework is ready.")
        return 0
    else:
        print("\nWARNING: Some tests failed. Please check the above output.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
