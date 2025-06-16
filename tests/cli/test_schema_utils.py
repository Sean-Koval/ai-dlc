#!/usr/bin/env python3
"""
Tests for the schema_utils module.

This module contains tests for the schema_utils module, specifically for the
load_and_validate_schema function which is part of the :ArchitecturalPattern:DataValidation
implementation.
"""

import os
import pytest
from pathlib import Path

from cli.schema_utils import load_and_validate_schema, InvalidSchemaError


class TestLoadAndValidateSchema:
    """Tests for the load_and_validate_schema function."""

    def test_valid_schema(self):
        """Test loading a valid JSON schema file."""
        schema_path = Path("valid_schema.json")
        schema = load_and_validate_schema(schema_path)
        
        # Verify the schema was loaded correctly
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert "required" in schema
        assert "name" in schema["required"]

    def test_file_not_found(self):
        """Test behavior when the schema file doesn't exist."""
        schema_path = Path("nonexistent_schema.json")
        
        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_path)
        
        # Verify the error message
        assert "Schema file not found" in str(excinfo.value)
        assert str(schema_path) in str(excinfo.value)

    def test_invalid_json(self):
        """Test behavior when the schema file contains invalid JSON."""
        schema_path = Path("invalid_json_schema.json")
        
        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_path)
        
        # Verify the error message
        assert "Schema file contains invalid JSON" in str(excinfo.value)

    def test_invalid_schema_structure(self):
        """Test behavior when the schema file is not a valid JSON Schema document."""
        schema_path = Path("invalid_structure_schema.json")
        
        # Verify that the function raises the expected exception
        with pytest.raises(InvalidSchemaError) as excinfo:
            load_and_validate_schema(schema_path)
        
        # Verify the error message
        assert "Schema file is not a valid JSON Schema document" in str(excinfo.value)


if __name__ == "__main__":
    # Run the tests directly if this file is executed
    pytest.main(["-xvs", __file__])