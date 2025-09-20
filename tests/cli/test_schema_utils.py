#!/usr/bin/env python3
"""
Tests for the schema_utils module.
"""

import pytest
from pathlib import Path
import json

from ai_dlc.cli.schema_utils import load_and_validate_schema, InvalidSchemaError


class TestLoadAndValidateSchema:
    """Tests for the load_and_validate_schema function."""

    def test_valid_schema(self, tmp_path: Path):
        """Test loading a valid JSON schema file."""
        schema_content = {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        schema_file = tmp_path / "valid_schema.json"
        schema_file.write_text(json.dumps(schema_content))

        schema = load_and_validate_schema(schema_file)

        # Verify the schema was loaded correctly
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert "required" in schema
        assert "name" in schema["required"]

    def test_file_not_found(self, tmp_path: Path):
        """Test behavior when the schema file doesn't exist."""
        schema_path = tmp_path / "nonexistent_schema.json"

        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_path)

        # Verify the error message
        assert "Schema file not found" in str(excinfo.value)
        assert str(schema_path) in str(excinfo.value)

    def test_invalid_json(self, tmp_path: Path):
        """Test behavior when the schema file contains invalid JSON."""
        schema_file = tmp_path / "invalid_json_schema.json"
        schema_file.write_text("{'invalid_json': True,}") # Invalid JSON

        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_file)

        # Verify the error message
        assert "Schema file contains invalid JSON" in str(excinfo.value)

    def test_invalid_schema_structure(self, tmp_path: Path):
        """Test behavior when the schema file is not a valid JSON Schema document."""
        schema_file = tmp_path / "invalid_structure_schema.json"
        # This is valid JSON, but not a valid JSON schema (type is not a valid type)
        schema_file.write_text(json.dumps({"type": "invalid_type"}))

        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_file)

        # Verify the error message
        assert "Schema file is not a valid JSON Schema document" in str(excinfo.value)
