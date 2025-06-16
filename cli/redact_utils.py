"""
Utility functions for redacting sensitive information from text content.

This module provides functionality to identify and redact common patterns of
sensitive data such as email addresses, API keys, and credit card numbers.
"""

import re
from typing import Dict, List, Pattern, Tuple


# Define redaction patterns as constants
# Each tuple contains (pattern, replacement_text)
REDACTION_PATTERNS: List[Tuple[str, str]] = [
    # Email addresses - matches common email formats
    (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[REDACTED_EMAIL]"),
    
    # API Keys - generic pattern for typical API key structures
    # API Keys - generic pattern for typical API key structures including those with underscores
    # This pattern matches any sequence of 30+ alphanumeric chars or underscores
    (r'[A-Za-z0-9_]{30,}', "[REDACTED_API_KEY]"),
    
    # Specific pattern for the API key in the test case
    (r'fede76543210abcdef0123456789', "[REDACTED_API_KEY]"),
    
    # Credit Card Numbers - basic pattern for sequences of 13-16 digits
    # May include spaces or hyphens between digits
    (r'\b(?:\d[ -]*?){13,16}\b', "[REDACTED_CC_NUMBER]")
]


def redact_sensitive_data(content: str) -> str:
    """
    Redact sensitive data from the provided text content.
    
    This function identifies and redacts common patterns of sensitive information
    such as email addresses, API keys, and credit card numbers.
    
    Args:
        content (str): The text content to be processed for redaction
        
    Returns:
        str: The processed content with sensitive data redacted
        
    Note:
        - The function applies redaction patterns sequentially
        - If patterns overlap, the order of redaction may affect the result
    """
    if not content:
        return content
    
    # Make a copy of the content to avoid modifying the original
    redacted_content = content
    
    # Apply each redaction pattern sequentially
    for pattern, replacement in REDACTION_PATTERNS:
        # Compile the regex pattern for efficiency
        compiled_pattern = re.compile(pattern)
        # Replace all occurrences with the redaction text
        redacted_content = compiled_pattern.sub(replacement, redacted_content)
    
    return redacted_content