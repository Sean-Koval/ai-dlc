"""
Tests for the LLM client module.

This module implements targeted tests for the GeminiClient class and
render_template_via_llm function following the :LLMClientWrapper and
:ServiceFacade architectural patterns.
"""

import unittest
from unittest.mock import patch, MagicMock, Mock

# We'll use patch to mock the imports in the module under test
# This approach avoids the need for the actual google module
@patch('cli.llm_client.generativeai')
class TestGeminiClient(unittest.TestCase):
    """
    Tests for the GeminiClient class.
    
    Implements CORE LOGIC TESTING for the GeminiClient class, focusing on:
    - Initialization with default and custom model names
    - Generate method functionality
    - API error propagation
    """

    def test_init_with_default_model(self, mock_generativeai):
        """Test GeminiClient initialization with default model name."""
        client = GeminiClient()
        
        # Assert that generativeai.configure was called
        mock_generativeai.configure.assert_called_once()
        
        # Assert that the default model name was set
        self.assertEqual(client.model_name, "models/text-bison-001")

    def test_init_with_custom_model(self, mock_generativeai):
        """Test GeminiClient initialization with custom model name."""
        custom_model = "models/gemini-pro"
        client = GeminiClient(model_name=custom_model)
        
        # Assert that generativeai.configure was called
        mock_generativeai.configure.assert_called_once()
        
        # Assert that the custom model name was set
        self.assertEqual(client.model_name, custom_model)

    def test_generate_with_default_params(self, mock_generativeai):
        """Test generate method with default parameters."""
        # Set up the mock response
        mock_model = Mock()
        mock_generativeai.GenerativeModel.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = "Generated text response"
        mock_model.generate_content.return_value = mock_response
        
        # Create client and call generate
        client = GeminiClient()
        result = client.generate("Test prompt")
        
        # Assert GenerativeModel was initialized with the correct model name
        mock_generativeai.GenerativeModel.assert_called_once_with("models/text-bison-001")
        
        # Assert generate_content was called with the correct parameters
        mock_model.generate_content.assert_called_once_with(
            "Test prompt",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024
            }
        )
        
        # Assert the result is the text from the response
        self.assertEqual(result, "Generated text response")

    def test_generate_with_custom_params(self, mock_generativeai):
        """Test generate method with custom parameters."""
        # Set up the mock response
        mock_model = Mock()
        mock_generativeai.GenerativeModel.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = "Generated text response"
        mock_model.generate_content.return_value = mock_response
        
        # Create client and call generate with custom parameters
        client = GeminiClient()
        result = client.generate(
            prompt="Custom prompt",
            temperature=0.8,
            max_tokens=2048
        )
        
        # Assert generate_content was called with the correct parameters
        mock_model.generate_content.assert_called_once_with(
            "Custom prompt",
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 2048
            }
        )
        
        # Assert the result is the text from the response
        self.assertEqual(result, "Generated text response")

    def test_generate_api_error(self, mock_generativeai):
        """Test that API errors are propagated from the generate method."""
        # Set up the mock to raise an exception
        mock_model = Mock()
        mock_generativeai.GenerativeModel.return_value = mock_model
        mock_model.generate_content.side_effect = Exception("API Error")
        
        # Create client and attempt to call generate
        client = GeminiClient()
        
        # Assert that the exception is propagated
        with self.assertRaises(Exception) as context:
            client.generate("Test prompt")
        
        # Assert the exception message
        self.assertEqual(str(context.exception), "API Error")


@patch('cli.llm_client.GeminiClient')
class TestRenderTemplateViaLLM(unittest.TestCase):
    """
    Tests for the render_template_via_llm function.
    
    Implements CORE LOGIC TESTING for the render_template_via_llm function, focusing on:
    - Client instantiation and call
    - API error propagation
    """

    def test_client_instantiation_and_call(self, mock_gemini_client_class):
        """Test that GeminiClient is instantiated and called correctly."""
        # Set up the mock instance and its generate method
        mock_instance = mock_gemini_client_class.return_value
        mock_instance.generate.return_value = "Generated template"
        
        # Call the function
        result = render_template_via_llm("Test prompt")
        
        # Assert that GeminiClient was instantiated
        mock_gemini_client_class.assert_called_once()
        
        # Assert that generate was called with the correct prompt
        mock_instance.generate.assert_called_once_with("Test prompt")
        
        # Assert that the function returns the text from the generate method
        self.assertEqual(result, "Generated template")

    def test_api_error_propagation(self, mock_gemini_client_class):
        """Test that API errors are propagated from render_template_via_llm."""
        # Set up the mock instance to raise an exception
        mock_instance = mock_gemini_client_class.return_value
        mock_instance.generate.side_effect = Exception("API Error")
        
        # Assert that the exception is propagated
        with self.assertRaises(Exception) as context:
            render_template_via_llm("Test prompt")
        
        # Assert the exception message
        self.assertEqual(str(context.exception), "API Error")


if __name__ == '__main__':
    unittest.main()


class TestGeminiClient(unittest.TestCase):
    """
    Tests for the GeminiClient class.
    
    Implements CORE LOGIC TESTING for the GeminiClient class, focusing on:
    - Initialization with default and custom model names
    - Generate method functionality
    - API error propagation
    """

    @patch('google.generativeai.configure')
    def test_init_with_default_model(self, mock_configure):
        """Test GeminiClient initialization with default model name."""
        client = GeminiClient()
        
        # Assert that generativeai.configure was called
        mock_configure.assert_called_once()
        
        # Assert that the default model name was set
        self.assertEqual(client.model_name, "models/text-bison-001")

    @patch('google.generativeai.configure')
    def test_init_with_custom_model(self, mock_configure):
        """Test GeminiClient initialization with custom model name."""
        custom_model = "models/gemini-pro"
        client = GeminiClient(model_name=custom_model)
        
        # Assert that generativeai.configure was called
        mock_configure.assert_called_once()
        
        # Assert that the custom model name was set
        self.assertEqual(client.model_name, custom_model)

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_generate_with_default_params(self, mock_configure, mock_generative_model):
        """Test generate method with default parameters."""
        # Set up the mock response
        mock_instance = mock_generative_model.return_value
        mock_response = MagicMock()
        mock_response.text = "Generated text response"
        mock_instance.generate_content.return_value = mock_response
        
        # Create client and call generate
        client = GeminiClient()
        result = client.generate("Test prompt")
        
        # Assert GenerativeModel was initialized with the correct model name
        mock_generative_model.assert_called_once_with("models/text-bison-001")
        
        # Assert generate_content was called with the correct parameters
        mock_instance.generate_content.assert_called_once_with(
            "Test prompt",
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024
            }
        )
        
        # Assert the result is the text from the response
        self.assertEqual(result, "Generated text response")

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_generate_with_custom_params(self, mock_configure, mock_generative_model):
        """Test generate method with custom parameters."""
        # Set up the mock response
        mock_instance = mock_generative_model.return_value
        mock_response = MagicMock()
        mock_response.text = "Generated text response"
        mock_instance.generate_content.return_value = mock_response
        
        # Create client and call generate with custom parameters
        client = GeminiClient()
        result = client.generate(
            prompt="Custom prompt",
            temperature=0.8,
            max_tokens=2048
        )
        
        # Assert generate_content was called with the correct parameters
        mock_instance.generate_content.assert_called_once_with(
            "Custom prompt",
            generation_config={
                "temperature": 0.8,
                "max_output_tokens": 2048
            }
        )
        
        # Assert the result is the text from the response
        self.assertEqual(result, "Generated text response")

    @patch('google.generativeai.GenerativeModel')
    @patch('google.generativeai.configure')
    def test_generate_api_error(self, mock_configure, mock_generative_model):
        """Test that API errors are propagated from the generate method."""
        # Set up the mock to raise an exception
        mock_instance = mock_generative_model.return_value
        mock_instance.generate_content.side_effect = Exception("API Error")
        
        # Create client and attempt to call generate
        client = GeminiClient()
        
        # Assert that the exception is propagated
        with self.assertRaises(Exception) as context:
            client.generate("Test prompt")
        
        # Assert the exception message
        self.assertEqual(str(context.exception), "API Error")


class TestRenderTemplateViaLLM(unittest.TestCase):
    """
    Tests for the render_template_via_llm function.
    
    Implements CORE LOGIC TESTING for the render_template_via_llm function, focusing on:
    - Client instantiation and call
    - API error propagation
    """

    @patch('cli.llm_client.GeminiClient')
    def test_client_instantiation_and_call(self, mock_gemini_client_class):
        """Test that GeminiClient is instantiated and called correctly."""
        # Set up the mock instance and its generate method
        mock_instance = mock_gemini_client_class.return_value
        mock_instance.generate.return_value = "Generated template"
        
        # Call the function
        result = render_template_via_llm("Test prompt")
        
        # Assert that GeminiClient was instantiated
        mock_gemini_client_class.assert_called_once()
        
        # Assert that generate was called with the correct prompt
        mock_instance.generate.assert_called_once_with("Test prompt")
        
        # Assert that the function returns the text from the generate method
        self.assertEqual(result, "Generated template")

    @patch('cli.llm_client.GeminiClient')
    def test_api_error_propagation(self, mock_gemini_client_class):
        """Test that API errors are propagated from render_template_via_llm."""
        # Set up the mock instance to raise an exception
        mock_instance = mock_gemini_client_class.return_value
        mock_instance.generate.side_effect = Exception("API Error")
        
        # Assert that the exception is propagated
        with self.assertRaises(Exception) as context:
            render_template_via_llm("Test prompt")
        
        # Assert the exception message
        self.assertEqual(str(context.exception), "API Error")


if __name__ == '__main__':
    unittest.main()


# Import Mock first to use in patching
from unittest.mock import patch, MagicMock, Mock

# We need to patch the google module before importing from cli.llm_client
with patch.dict('sys.modules', {'google': MagicMock(), 'google.generativeai': MagicMock()}):
    from cli.llm_client import GeminiClient, render_template_via_llm, ensure_validation_section, ValidationMarkerMissingError


@patch.dict('sys.modules', {'google': MagicMock(), 'google.generativeai': MagicMock()})
class TestLLMClientInteraction(unittest.TestCase):
    """
    Tests for the ensure_validation_section function.
    
    Implements TARGETED TESTING STRATEGY for the ensure_validation_section function:
    
    CORE LOGIC TESTING:
    - Validation marker present in response
    - Validation marker missing with successful retry
    - Validation marker missing with retries exhausted
    - Validation marker missing with zero retries
    
    This function implements the :PostProcessingHook and :ErrorHandlingWithRetry
    architectural patterns for :LLMResponseValidation.
    """
    
    def test_ensure_validation_marker_present(self):
        """Test that when validation marker is present, original response is returned."""
        # Setup
        response_with_marker = "Some response text\nVALIDATION: field1, field2"
        mock_client = Mock(spec=GeminiClient)
        
        # Execute
        result = ensure_validation_section(
            response_text=response_with_marker,
            client=mock_client,
            original_prompt_text="Original prompt",
            max_retries=1
        )
        
        # Assert
        self.assertEqual(result, response_with_marker)
        # Assert that generate was not called
        mock_client.generate.assert_not_called()
    
    def test_ensure_validation_marker_missing_retry_success(self):
        """Test that when validation marker is missing, retry succeeds with new response."""
        # Setup
        response_without_marker = "Some response text without validation"
        response_with_marker = "New response\nVALIDATION: field1, field2"
        
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate.return_value = response_with_marker
        
        # Execute
        result = ensure_validation_section(
            response_text=response_without_marker,
            client=mock_client,
            original_prompt_text="Original prompt",
            max_retries=1
        )
        
        # Assert
        self.assertEqual(result, response_with_marker)
        # Assert that generate was called once with the correct follow-up prompt
        mock_client.generate.assert_called_once()
        # Check that the call contains the expected text about missing VALIDATION section
        call_args = mock_client.generate.call_args[0][0]
        self.assertIn("missing the 'VALIDATION:' section", call_args)
    
    def test_ensure_validation_marker_missing_retries_exhausted(self):
        """Test that when validation marker is missing after max retries, exception is raised."""
        # Setup
        response_without_marker = "Some response text without validation"
        new_response_still_without_marker = "New response still without validation"
        
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate.return_value = new_response_still_without_marker
        
        # Execute and Assert
        with self.assertRaises(ValidationMarkerMissingError):
            ensure_validation_section(
                response_text=response_without_marker,
                client=mock_client,
                original_prompt_text="Original prompt",
                max_retries=2
            )
        
        # Assert that generate was called exactly max_retries times
        self.assertEqual(mock_client.generate.call_count, 2)
    
    def test_ensure_validation_marker_missing_zero_retries(self):
        """Test that when validation marker is missing with zero retries, exception is raised immediately."""
        # Setup
        response_without_marker = "Some response text without validation"
        mock_client = Mock(spec=GeminiClient)
        
        # Execute and Assert
        with self.assertRaises(ValidationMarkerMissingError):
            ensure_validation_section(
                response_text=response_without_marker,
                client=mock_client,
                original_prompt_text="Original prompt",
                max_retries=0
            )
        
        # Assert that generate was not called
        mock_client.generate.assert_not_called()