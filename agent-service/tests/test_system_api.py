import unittest

from fastapi.testclient import TestClient

from app.main import app


class SystemApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)

    def test_health_returns_agent_service_identity(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual("UP", response.json()["status"])
        self.assertEqual("eduops-agent", response.json()["service"])

    def test_metadata_distinguishes_existing_specialists_from_unbuilt_durability(self) -> None:
        response = self.client.get("/api/v1/meta")
        payload = response.json()

        self.assertEqual(200, response.status_code)
        self.assertIn(
            "explicit-java-service-boundary",
            payload["implemented_capabilities"],
        )
        self.assertEqual("bounded-multi-specialist-workflow", payload["stage"])
        self.assertIn("ticket-specialist", payload["implemented_capabilities"])
        self.assertIn(
            "ticket-to-knowledge-sequential-collaboration",
            payload["implemented_capabilities"],
        )
        self.assertIn("persistent-checkpoint", payload["planned_capabilities"])
        self.assertIn(
            "persistent-human-handoff-task", payload["planned_capabilities"]
        )
        self.assertIn("runtime-trace", payload["planned_capabilities"])
        self.assertFalse(payload["can_execute_external_actions"])


if __name__ == "__main__":
    unittest.main()
