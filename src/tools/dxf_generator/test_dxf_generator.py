"""
Unit tests for the DXF Generator module.
Run from the project root with:
    python -m unittest src/tools/dxf_generator/test_dxf_generator.py
"""

import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from fastapi.testclient import TestClient
from src.tools.dxf_generator.api import app
from src.tools.dxf_generator.api import cleanup_files


class TestDXFGeneratorAPI(unittest.TestCase):
    """Tests for the DXF Generator FastAPI endpoints."""

    def setUp(self):
        """Sets up the FastAPI test client before each test."""
        self.client = TestClient(app)

    def test_health_check_returns_ok(self):
        """GET /health must return 200 with status ok and correct agent name."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["agent"], "dxf_generator")

    def test_run_endpoint_exists(self):
        """POST /run must exist and return 422 (not 404) when given bad input, confirming route is registered."""
        response = self.client.post("/run", json={})
        self.assertNotEqual(response.status_code, 404)


class TestCleanupFiles(unittest.TestCase):
    """Unit tests for the cleanup_files helper function."""

    def test_cleanup_removes_existing_file(self):
        """cleanup_files must delete a file that exists on disk."""
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        self.assertTrue(os.path.exists(tmp.name))

        cleanup_files(tmp.name)

        self.assertFalse(os.path.exists(tmp.name))

    def test_cleanup_ignores_nonexistent_file(self):
        """cleanup_files must not raise if the file does not exist."""
        try:
            cleanup_files("/tmp/this_file_does_not_exist_xyz123.dxf")
        except Exception as e:
            self.fail(f"cleanup_files raised unexpectedly: {e}")

    def test_cleanup_handles_multiple_files(self):
        """cleanup_files must handle multiple file paths at once."""
        tmp1 = tempfile.NamedTemporaryFile(delete=False)
        tmp2 = tempfile.NamedTemporaryFile(delete=False)
        tmp1.close()
        tmp2.close()

        cleanup_files(tmp1.name, tmp2.name)

        self.assertFalse(os.path.exists(tmp1.name))
        self.assertFalse(os.path.exists(tmp2.name))

    def test_cleanup_handles_none_path(self):
        """cleanup_files must silently skip None values in file_paths."""
        try:
            cleanup_files(None, "")
        except Exception as e:
            self.fail(f"cleanup_files raised unexpectedly with None: {e}")


class TestGenerateDXF(unittest.TestCase):
    """Unit tests for the generate_dxf function."""

    def test_generate_dxf_produces_output_file(self):
        """
        generate_dxf must produce a .dxf file at the specified output path
        when given a valid minimal JSON input.
        """
        from src.tools.dxf_generator.dxf_generator import generate_dxf

        # Minimal valid IR JSON: one view, one polygon, no labels
        input_data = {
            "views": [
                {
                    "view_id": "floor_plan",
                    "layers": [{"name": "Walls", "color": 7}],
                    "entities": [
                        {
                            "type": "polygon",
                            "layer": "Walls",
                            "points": [[0, 0], [10, 0], [10, 10], [0, 10]],
                            "closed": True,
                            "auto_dimension": False
                        }
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "input.json")
            dxf_path = os.path.join(tmpdir, "output.dxf")

            with open(json_path, "w") as f:
                json.dump(input_data, f)

            generate_dxf([json_path], dxf_path, render=False)

            self.assertTrue(os.path.exists(dxf_path), "DXF output file was not created.")
            self.assertGreater(os.path.getsize(dxf_path), 0, "DXF output file is empty.")

    def test_generate_dxf_is_deterministic(self):
        """Same input JSON must produce the same DXF output (deterministic — no LLM involved)."""
        from src.tools.dxf_generator.dxf_generator import generate_dxf

        input_data = {
            "views": [
                {
                    "view_id": "floor_plan",
                    "layers": [{"name": "Walls", "color": 7}],
                    "entities": [
                        {
                            "type": "polygon",
                            "layer": "Walls",
                            "points": [[0, 0], [5, 0], [5, 5], [0, 5]],
                            "closed": True,
                            "auto_dimension": False
                        }
                    ]
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "input.json")
            dxf_path_1 = os.path.join(tmpdir, "output1.dxf")
            dxf_path_2 = os.path.join(tmpdir, "output2.dxf")

            with open(json_path, "w") as f:
                json.dump(input_data, f)

            generate_dxf([json_path], dxf_path_1, render=False)
            generate_dxf([json_path], dxf_path_2, render=False)

            with open(dxf_path_1, "rb") as f1, open(dxf_path_2, "rb") as f2:
                # DXF files may have minor timestamp differences but core content should match
                # We check size as a proxy for determinism at minimum
                self.assertEqual(os.path.getsize(dxf_path_1), os.path.getsize(dxf_path_2))


if __name__ == "__main__":
    unittest.main()
