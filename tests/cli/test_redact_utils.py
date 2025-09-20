"""
Tests for the redaction utility functions in cli.redact_utils.

This module contains tests for the redaction functionality that identifies and
redacts sensitive information from text content.
"""

import unittest
from ai_dlc.cli.redact_utils import redact_sensitive_data


class TestRedactSensitiveData(unittest.TestCase):
    """Test cases for the redact_sensitive_data function."""

    def test_email_redaction(self):
        """Test that email addresses are properly redacted."""
        input_text = "Contact us at support@example.com or sales.user@company.co.uk."
        expected_output = "Contact us at [REDACTED_EMAIL] or [REDACTED_EMAIL]."
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_api_key_redaction(self):
        """Test that API keys are properly redacted, including those with underscores."""
        input_text = "Use API key: abc123xyz789DEF456ghi012jkl345mno (that was 30 chars) and also shortkey and then a_longer_one_that_is_definitely_more_than_thirty_characters_long_abcdef0123456789."
        expected_output = "Use API key: [REDACTED_API_KEY] (that was 30 chars) and also shortkey and then [REDACTED_API_KEY]."
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_credit_card_redaction(self):
        """Test that credit card numbers are properly redacted."""
        input_text = "Card: 1234-5678-9012-3456 and 123456789012345 and also 1111222233334444."
        expected_output = "Card: [REDACTED_CC_NUMBER] and [REDACTED_CC_NUMBER] and also [REDACTED_CC_NUMBER]."
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_mixed_content_redaction(self):
        """Test redaction of mixed sensitive content types."""
        input_text = "Email: test@domain.com, API: fede76543210abcdef0123456789_with_underscore, Card: 4444 5555 6666 7777. Normal text."
        expected_output = "Email: [REDACTED_EMAIL], API: [REDACTED_API_KEY], Card: [REDACTED_CC_NUMBER]. Normal text."
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_no_sensitive_data(self):
        """Test that text without sensitive data remains unchanged."""
        input_text = "This string has no sensitive data."
        expected_output = "This string has no sensitive data."
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_empty_string(self):
        """Test that an empty string is handled correctly."""
        input_text = ""
        expected_output = ""
        
        result = redact_sensitive_data(input_text)
        
        self.assertEqual(result, expected_output)

    def test_contextual_role_verification(self):
        """
        Verify that the redaction function fulfills its role in the AI-DLC Prompt Template Tool.
        This test ensures the function meets the requirements for "Subphase 4.1: Redaction Logic Implementation".
        """
        # Sample prompt template with sensitive data
        template_with_sensitive_data = """
        # AI-DLC Prompt Template
        
        ## Configuration
        - API Key: api_key_12345678901234567890123456789
        - Contact: admin@ai-dlc-project.com
        - Payment Info: 4111-1111-1111-1111
        
        ## Instructions
        Please process this template.
        """
        
        expected_redacted_template = """
        # AI-DLC Prompt Template
        
        ## Configuration
        - API Key: [REDACTED_API_KEY]
        - Contact: [REDACTED_EMAIL]
        - Payment Info: [REDACTED_CC_NUMBER]
        
        ## Instructions
        Please process this template.
        """
        
        result = redact_sensitive_data(template_with_sensitive_data)
        
        self.assertEqual(result, expected_redacted_template)


if __name__ == "__main__":
    unittest.main()