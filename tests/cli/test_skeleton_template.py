#!/usr/bin/env python3
"""
Tests for the skeleton.j2 Jinja2 template.

This module contains tests for the master meta-prompt template (skeleton.j2)
that implements the :ArchitecturalPattern:MetaPrompting pattern.
"""

import unittest
from pathlib import Path


class TestSkeletonTemplate(unittest.TestCase):
    """Test cases for the skeleton.j2 template."""

    def setUp(self):
        """Set up the test environment."""
        # Set up path to the template file
        self.template_dir = Path(__file__).parent.parent.parent / "cli" / "prompt_skeletons"
        self.template_path = self.template_dir / "skeleton.j2"
        
        # Sample data for testing (not used for rendering, but for reference)
        self.sample_data = {
            "role": "Data Analyst",
            "task": "Generate a monthly sales report template.",
            "directives": ["list items", "include totals"],
            "schema": '{"sales_data": {"type": "array", "items": {"type": "object", "properties": {"product_name": {"type": "string"}, "quantity_sold": {"type": "integer"}, "revenue": {"type": "number"}}}}, "report_month": {"type": "string"}}'
        }

    def test_template_exists(self):
        """Test that the skeleton.j2 template file exists."""
        self.assertTrue(self.template_path.exists(),
                        f"Template file not found at {self.template_path}")

    def test_placeholder_presence(self):
        """Test that all required placeholders are present in the template."""
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for all required placeholders
        self.assertIn("{{ role }}", content,
                      "Role placeholder not found in template")
        self.assertIn("{{ task }}", content,
                      "Task placeholder not found in template")
        self.assertIn("{{ directives }}", content,
                      "Directives placeholder not found in template")
        self.assertIn("{{ schema }}", content,
                      "Schema placeholder not found in template")

    def test_validation_marker_presence(self):
        """Test that the VALIDATION: marker is present in the template."""
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for validation marker
        self.assertIn("VALIDATION:", content,
                      "VALIDATION: marker not found in template")

    def test_template_structure(self):
        """Test that the template contains the expected structural elements."""
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for key structural elements
        self.assertIn("ANALYZE THE INPUTS", content,
                      "ANALYZE THE INPUTS section not found in template")
        self.assertIn("PROPOSE A HIGH-LEVEL STRUCTURE", content,
                      "PROPOSE A HIGH-LEVEL STRUCTURE section not found in template")
        self.assertIn("MAP SCHEMA ENTITIES TO JINJA2 SYNTAX", content,
                      "MAP SCHEMA ENTITIES TO JINJA2 SYNTAX section not found in template")
        self.assertIn("IMPLEMENT THE TEMPLATE", content,
                      "IMPLEMENT THE TEMPLATE section not found in template")
        self.assertIn("VALIDATION", content,
                      "VALIDATION section not found in template")


if __name__ == "__main__":
    unittest.main()