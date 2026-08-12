"""TestableModule for integration testing"""

from runtime.base_module_v2 import BaseModuleV2


class TestableModule(BaseModuleV2):
    """Testable M1 module implementation"""

    def __init__(self, module_id: str = "test-module-001"):
        from runtime.base_module_v2 import ResponseSecurityContext
        from tests.utils import MockEnvelopeFinalizer
        from uuid import uuid4

        # Set up complete ResponseSecurityContext (including envelope_finalizer)
        response_context = ResponseSecurityContext(
            responder_module_id=module_id,
            responder_instance_id=str(uuid4()),
            responder_key_id="test-key",
            envelope_finalizer=MockEnvelopeFinalizer(),
        )
        super().__init__(module_id, response_context=response_context)

    def _execute(self, envelope_payload: dict) -> dict:
        """Simple echo implementation for testing"""
        return {
            "status": "success",
            "received": envelope_payload,
            "module_id": self.module_id,
        }
