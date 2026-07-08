"""
Unit tests for the Entity Constraint Engine module.
Run from the project root with:
    python -m unittest src/tools/entity_constraint_engine/test_entity_constraint_engine.py
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from fastapi.testclient import TestClient
from src.tools.entity_constraint_engine.api import app
from src.tools.entity_constraint_engine.entity_constraint_engine import EntityConstraintEngine


class TestEntityConstraintEngineAPI(unittest.TestCase):
    """Tests for the Entity Constraint Engine FastAPI endpoints."""

    def setUp(self):
        """Sets up the FastAPI test client before each test."""
        self.client = TestClient(app)

    def test_health_check_returns_ok(self):
        """GET /health must return 200 with status ok and correct agent name."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["agent"], "entity_engine")

    def test_run_endpoint_exists(self):
        """POST /run must exist and return 422 (not 404) when given bad input, confirming route is registered."""
        response = self.client.post("/run", json={})
        self.assertNotEqual(response.status_code, 404)


class TestEntityConstraintEngineClass(unittest.TestCase):
    """Unit tests for the EntityConstraintEngine class logic."""

    def test_initialization_without_credentials(self):
        """Engine must initialize without raising even when Supabase credentials are missing."""
        with patch.dict(os.environ, {}, clear=True):
            try:
                engine = EntityConstraintEngine()
                self.assertIsNotNone(engine)
            except Exception as e:
                self.fail(f"EntityConstraintEngine raised unexpectedly: {e}")

    def test_get_entity_rules_returns_no_data_when_supabase_not_initialized(self):
        """
        get_entity_rules must return a dict with status 'no_data' when
        Supabase client is not available (credentials missing at startup).
        """
        engine = EntityConstraintEngine.__new__(EntityConstraintEngine)
        # Simulate engine with no supabase attribute (missing credentials)
        result = engine.get_entity_rules("bedroom")
        self.assertEqual(result.get("status"), "no_data")

    def test_get_entities_rules_returns_empty_dict_for_no_data(self):
        """
        get_entities_rules must return an empty dict when no entities have data
        (e.g., Supabase not initialized).
        """
        engine = EntityConstraintEngine.__new__(EntityConstraintEngine)
        result = engine.get_entities_rules(["bedroom", "bathroom"])
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_get_entity_rules_response_structure(self):
        """
        get_entity_rules must return a dict with version, size_rules,
        feature_rules, relational_rules, and area_rules when data is found.
        """
        engine = EntityConstraintEngine.__new__(EntityConstraintEngine)

        # Mock the Supabase client and its response
        mock_supabase = MagicMock()
        mock_spec_response = MagicMock()
        mock_spec_response.data = [{
            "entity_type": "bedroom",
            "min_area_ft2": 70.0,
            "min_side_ft": 7.0,
            "max_side_ft": 30.0,
            "min_aspect_ratio": 1.0,
            "max_aspect_ratio": 3.0,
            "habitable": True,
            "requires_exterior_window": True,
            "requires_egress": True,
            "ventilation_type": "natural",
            "requires_door": True,
            "requires_closet": True,
            "area_rules_json": "[]"
        }]
        mock_adj_response = MagicMock()
        mock_adj_response.data = []

        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
            mock_spec_response,
            mock_adj_response
        ]
        engine.supabase = mock_supabase

        result = engine.get_entity_rules("bedroom", include_relations=True)

        self.assertEqual(result["entity_type"], "bedroom")
        self.assertEqual(result["version"], "v1")
        self.assertIn("size_rules", result)
        self.assertIn("feature_rules", result)
        self.assertIn("relational_rules", result)
        self.assertIn("area_rules", result)
        self.assertEqual(result["size_rules"]["min_area_ft2"], 70.0)

    def test_get_entities_rules_filters_cross_entity_relations(self):
        """
        get_entities_rules must filter out relational rules that point to entities
        not in the requested list.
        """
        engine = EntityConstraintEngine.__new__(EntityConstraintEngine)

        # Simulate get_entity_rules returning a rule pointing to 'living' (not in request list)
        def fake_get_entity_rules(entity_type, include_relations=True):
            return {
                "entity_type": entity_type,
                "version": "v1",
                "size_rules": {},
                "feature_rules": {},
                "relational_rules": [
                    {"a": entity_type, "b": "bathroom", "relation": "adjacent"},
                    {"a": entity_type, "b": "living", "relation": "near"},  # should be filtered out
                ],
                "area_rules": []
            }

        engine.get_entity_rules = fake_get_entity_rules

        result = engine.get_entities_rules(["bedroom", "bathroom"])

        # For "bedroom", the rule pointing to "living" must be filtered out
        bedroom_relations = result["bedroom"]["relational_rules"]
        target_entities = [r["b"] for r in bedroom_relations]
        self.assertNotIn("living", target_entities)
        self.assertIn("bathroom", target_entities)


if __name__ == "__main__":
    unittest.main()
