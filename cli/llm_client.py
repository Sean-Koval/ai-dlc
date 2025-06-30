"""
LLM Client module for interacting with various LLM APIs.

This module provides client classes for different LLM providers,
following the :LLMClientWrapper architectural pattern.
"""

from google import generativeai


class ValidationMarkerMissingError(Exception):
    """
    Exception raised when the validation marker is missing from the LLM response
    after the maximum number of retries.
    
    This exception is part of the :ErrorHandlingWithRetry architectural pattern
    and serves as a signal for the :LLMResponseValidation component.
    """
    pass


class GeminiClient:
    """
    Client for interacting with Google's Gemini API.
    
    This class follows the :LLMClientWrapper architectural pattern and serves
    as an :LLMInteractionService component.
    """
    
    def __init__(self, model_name: str = "gemini-1.5-flash-latest"):
        """
        Initialize the Gemini client.
        
        Args:
            model_name: The name of the Gemini model to use.
                        Defaults to "gemini-1.5-flash-latest".
        
        Notes:
            The SDK reads credentials from GOOGLE_APPLICATION_CREDENTIALS
            environment variable or from Application Default Credentials (ADC)
            configured via gcloud CLI.
        """
        self.model_name = model_name
        # Configure the generativeai SDK
        # No arguments needed if ADC is set up correctly
        generativeai.configure()
    
    def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int = 1024) -> str:
        """
        Generate text using the Gemini API.
        
        Args:
            prompt: The input prompt for text generation.
            temperature: Controls randomness in generation. Lower values make output
                         more deterministic. Defaults to 0.2.
            max_tokens: Maximum number of tokens to generate. Defaults to 1024.
        
        Returns:
            The generated text as a string.
            
        Raises:
            Various exceptions from the generativeai SDK if API errors occur.
        """
        # Initialize the model
        model = generativeai.GenerativeModel(self.model_name)
        
        # Generate content with the specified parameters
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens
            }
        )
        
        # Return the generated text
        return response.text


def render_template_via_llm(prompt_text: str) -> str:
    """
    Render a template using an LLM by sending a prompt and returning the response.
    
    This function follows the :ServiceFacade architectural pattern by providing
    a simplified interface to the LLM functionality through the GeminiClient.
    
    Args:
        prompt_text: The prompt text to send to the LLM.
        
    Returns:
        The raw text response from the LLM.
        
    Raises:
        Various exceptions from the GeminiClient.generate() method if API errors occur.
    """
    # Instantiate the GeminiClient
    client = GeminiClient()
    
    # Call the generate method with the provided prompt text
    # Let any API errors propagate as per the specifications
    response = client.generate(prompt_text)
    
    # Return the raw text response
    return response


def ensure_validation_section(response_text: str, client: GeminiClient, original_prompt_text: str, max_retries: int = 1) -> str:
    """
    Check for a "VALIDATION:" marker in the LLM's response and attempt to re-ask if it's missing.
    
    This function implements the :PostProcessingHook architectural pattern by validating
    and potentially enhancing the LLM's response. It also follows the :ErrorHandlingWithRetry
    pattern by attempting to re-ask the LLM if the validation section is missing.
    
    Args:
        response_text: The text response from the LLM to check.
        client: An instance of GeminiClient to use for re-asking if needed.
        original_prompt_text: The original prompt text (preserved for context).
        max_retries: Maximum number of retry attempts. Defaults to 1.
        
    Returns:
        The response text, either the original if it contains the validation marker,
        or a new response with the validation section if re-asking was successful.
        
    Raises:
        ValidationMarkerMissingError: If the validation marker is still missing after
                                      the maximum number of retries.
    """
    # Check for the "VALIDATION:" marker in the response
    if "VALIDATION:" in response_text:
        # Marker found, return the response as is
        return response_text
    
    # If we've exhausted our retries, raise an exception
    if max_retries <= 0:
        raise ValidationMarkerMissingError(
            "Failed to obtain a response with a 'VALIDATION:' section after maximum retries."
        )
    
    # Construct the follow-up prompt
    follow_up_prompt = (
        "\n\n---\n\n"
        "**CRITICAL CORRECTION:** The previous response you generated is missing the mandatory 'VALIDATION:' section. "
        "You MUST include a 'VALIDATION:' section in your response. "
        "Please review the original instructions, generate the Jinja2 template again, and this time, ensure you add a 'VALIDATION:' section that lists key fields the user should check. "
        "Return the COMPLETE template with the validation section included."
    )

    # Combine the original prompt with the follow-up instructions to provide context
    new_prompt = original_prompt_text + follow_up_prompt
    
    # Re-ask using the client
    new_response = client.generate(new_prompt)
    
    # Decrement max_retries and recursively call this function with the new response
    return ensure_validation_section(
        response_text=new_response,
        client=client,
        original_prompt_text=original_prompt_text,  # Preserve the original prompt
        max_retries=max_retries - 1
    )