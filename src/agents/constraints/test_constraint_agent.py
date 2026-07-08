"""
Unit tests for the Constraint Agent module.
Run from the project root with:
    python -m unittest src/agents/constraints/test_constraint_agent.py
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from fastapi.testclient import TestClient
from src.agents.constraints.api import app
from src.agents.constraints.constraint_agent import ConstraintAgent
from src.agents.constraints.validator import ConstraintValidationError


class TestConstraintAgentAPI(unittest.TestCase):
    """Tests for the Constraint Agent FastAPI endpoints."""

    def setUp(self):
        """Sets up the FastAPI test client before each test."""
        self.client = TestClient(app)

    def test_health_check_returns_ok(self):
        """GET /health must return 200 with status ok and correct agent name."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["agent"], "constraint_agent")

    def test_run_endpoint_exists(self):
        """POST /run must exist and return 422 (not 404) when given bad input, confirming route is registered."""
        response = self.client.post("/run", json={})
        self.assertNotEqual(response.status_code, 404)


class TestConstraintAgentClass(unittest.TestCase):
    """Unit tests for the ConstraintAgent class logic."""

    def test_initialization_with_custom_url(self):
        """ConstraintAgent must store the provided entity_engine_url."""
        agent = ConstraintAgent(entity_engine_url="http://test-engine:9999")
        self.assertEqual(agent.entity_engine_url, "http://test-engine:9999")

    def test_initialization_default_url_from_env(self):
        """ConstraintAgent must fall back to ENTITY_ENGINE_URL env var if no url is provided."""
        with patch.dict(os.environ, {"ENTITY_ENGINE_URL": "http://env-engine:1234"}):
            agent = ConstraintAgent()
            self.assertEqual(agent.entity_engine_url, "http://env-engine:1234")

    def test_default_descriptions_contains_required_keys(self):
        """DEFAULT_DESCRIPTIONS must contain all standard setback and coverage keys."""
        agent = ConstraintAgent()
        required_keys = [
            "front_setback_ft",
            "rear_setback_ft",
            "side_setback_ft",
            "max_height_ft",
            "max_lot_coverage_fraction",
        ]
        for key in required_keys:
            self.assertIn(key, agent.DEFAULT_DESCRIPTIONS, f"Missing key: {key}")

    def test_legal_keys_set_contains_setbacks(self):
        """LEGAL_KEYS must include the standard setback fields."""
        self.assertIn("front_setback_ft", ConstraintAgent.LEGAL_KEYS)
        self.assertIn("rear_setback_ft", ConstraintAgent.LEGAL_KEYS)
        self.assertIn("side_setback_ft", ConstraintAgent.LEGAL_KEYS)

    def test_process_zoning_input_returns_dict_with_required_keys(self):
        """
        process_zoning_input must return a dict containing jurisdiction, exterior,
        interior, descriptions, and constraint_levels — even with an empty zoning payload.
        """
        agent = ConstraintAgent(entity_engine_url="http://localhost:9999")

        # Mock the httpx.post call so we don't need a live ECE server
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entities": {}}

        with patch("httpx.post", return_value=mock_response):
            result = agent.process_zoning_input(
                data={"jurisdiction": "Redmond, WA"},
                user_text=None
            )

        self.assertIsInstance(result, dict)
        for key in ["jurisdiction", "exterior", "interior", "descriptions", "constraint_levels"]:
            self.assertIn(key, result, f"Missing key in output schema: {key}")

    def test_process_zoning_input_applies_setback_overrides(self):
        """process_zoning_input must correctly extract setback values into exterior constraints."""
        agent = ConstraintAgent(entity_engine_url="http://localhost:9999")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"entities": {}}

        zoning_data = {
            "jurisdiction": "Redmond, WA",
            "offsets": {"front": 20.0, "rear": 15.0, "side": 5.0}
        }

        with patch("httpx.post", return_value=mock_response):
            result = agent.process_zoning_input(data=zoning_data, user_text=None)

        self.assertEqual(result["exterior"]["front_setback_ft"], 20.0)
        self.assertEqual(result["exterior"]["rear_setback_ft"], 15.0)
        self.assertEqual(result["exterior"]["side_setback_ft"], 5.0)

    @patch("src.agents.constraints.llm_parser.parse_user_constraints")
    def test_process_zoning_input_raises_validation_error(self, mock_parse):
        """process_zoning_input must raise ConstraintValidationError if habitability is violated."""
        # Mock the LLM returning only bedrooms (violates building codes requiring bath/kitchen)
        mock_parse.return_value = {
            "required_instances": ["bedroom_1", "bedroom_2"]
        }
        
        agent = ConstraintAgent()
        zoning_data = {"jurisdiction": "Redmond, WA"}

        with self.assertRaises(ConstraintValidationError) as context:
            agent.process_zoning_input(data=zoning_data, user_text="I want 2 bedrooms")

        # Verify the exception reasons mention the missing rooms
        reasons_text = " ".join(context.exception.reasons)
        self.assertIn("bathroom", reasons_text.lower())
        self.assertIn("kitchen", reasons_text.lower())


if __name__ == "__main__":
    unittest.main()
