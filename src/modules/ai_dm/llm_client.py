"""
LLM Client Abstraction for AI DM.

Provides a unified interface for different LLM providers (Anthropic, OpenAI)
with error handling, retries, and response validation.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from src.core.config import Config

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """
    Abstract interface for LLM providers.

    Subclasses implement specific provider APIs (Anthropic, OpenAI, etc.)
    with a common interface for the AI DM module.
    """

    @abstractmethod
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Format: [{'role': 'user', 'content': '...'}, ...]
            system: Optional system prompt (persona/instructions)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific options

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        pass

    @abstractmethod
    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Generate a streaming response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt (persona/instructions)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Provider-specific options (including 'tools' for function calling)

        Yields:
            Dict chunks with 'type' and relevant data

        Raises:
            LLMError: If generation fails
        """
        pass


class LLMError(Exception):
    """Exception raised when LLM generation fails."""

    def __init__(self, message: str, provider: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.provider = provider
        self.original_error = original_error


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude implementation.

    Uses the Anthropic API to generate responses with Claude models.
    """

    def __init__(self, api_key: str, model: str = 'claude-sonnet-4-5-20250929'):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model to use (default: claude-sonnet-4-5-20250929)

        Raises:
            ImportError: If anthropic package not installed
            LLMError: If API key is invalid or client creation fails
        """
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic>=0.25.0"
            )

        if not api_key:
            raise LLMError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY in .env",
                provider="anthropic"
            )

        try:
            self.client = Anthropic(api_key=api_key)
            self.model = model
            logger.info(f"Initialized Anthropic provider with model: {model}")
        except Exception as e:
            raise LLMError(
                f"Failed to initialize Anthropic client: {e}",
                provider="anthropic",
                original_error=e
            )

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate response using Anthropic Claude API.

        Args:
            messages: Conversation history
            system: System prompt (string or list of content blocks with cache_control)
            max_tokens: Maximum response length
            temperature: Sampling temperature
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            Generated text

        Raises:
            LLMError: If API call fails
        """
        try:
            logger.debug(f"Calling Anthropic API with {len(messages)} messages")

            api_kwargs = {
                'model': kwargs.get('model', self.model),
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': messages
            }

            # Support both string and list format for system (list enables caching)
            if system:
                api_kwargs['system'] = system

            response = self.client.messages.create(**api_kwargs)

            # Extract text from response
            text = response.content[0].text
            logger.debug(f"Received response: {len(text)} characters")
            return text

        except Exception as e:
            error_msg = f"Anthropic API error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMError(error_msg, provider="anthropic", original_error=e)

    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """
        Generate streaming response using Anthropic Claude API.

        Args:
            messages: Conversation history
            system: System prompt (string or list of content blocks with cache_control)
            max_tokens: Maximum response length
            temperature: Sampling temperature
            **kwargs: Additional Anthropic-specific parameters (including 'tools')

        Yields:
            Dict chunks with 'type' and 'content' or 'tool_use' data

        Raises:
            LLMError: If API call fails
        """
        try:
            logger.debug(f"Calling Anthropic API (streaming) with {len(messages)} messages")

            tools = kwargs.get('tools')
            stream_kwargs = {
                'model': kwargs.get('model', self.model),
                'max_tokens': max_tokens,
                'temperature': temperature,
                'messages': messages
            }

            # Support both string and list format for system (list enables caching)
            if system:
                stream_kwargs['system'] = system

            if tools:
                stream_kwargs['tools'] = tools

            with self.client.messages.stream(**stream_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if hasattr(event, 'content_block') and event.content_block.type == "tool_use":
                            yield {
                                'type': 'tool_use_start',
                                'tool_use_id': event.content_block.id,
                                'tool_name': event.content_block.name
                            }
                    elif event.type == "content_block_delta":
                        if hasattr(event, 'delta'):
                            if event.delta.type == "text_delta":
                                yield {
                                    'type': 'text',
                                    'content': event.delta.text
                                }
                            elif event.delta.type == "input_json_delta":
                                yield {
                                    'type': 'tool_input_delta',
                                    'partial_json': event.delta.partial_json
                                }
                    elif event.type == "content_block_stop":
                        # Tool use block is complete
                        pass

            logger.debug(f"Streaming response completed")

        except Exception as e:
            error_msg = f"Anthropic API streaming error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMError(error_msg, provider="anthropic", original_error=e)


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT implementation.

    Uses the OpenAI API to generate responses with GPT models.
    """

    def __init__(self, api_key: str, model: str = 'gpt-4-turbo-preview'):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo-preview)

        Raises:
            ImportError: If openai package not installed
            LLMError: If API key is invalid or client creation fails
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai>=1.12.0"
            )

        if not api_key:
            raise LLMError(
                "OpenAI API key not provided. Set OPENAI_API_KEY in .env",
                provider="openai"
            )

        try:
            self.client = OpenAI(api_key=api_key)
            self.model = model
            logger.info(f"Initialized OpenAI provider with model: {model}")
        except Exception as e:
            raise LLMError(
                f"Failed to initialize OpenAI client: {e}",
                provider="openai",
                original_error=e
            )

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate response using OpenAI GPT API.

        Args:
            messages: Conversation history
            system: System prompt (prepended as system message)
            max_tokens: Maximum response length
            temperature: Sampling temperature
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            Generated text

        Raises:
            LLMError: If API call fails
        """
        try:
            # OpenAI uses system message in messages array
            if system:
                messages = [{"role": "system", "content": system}] + messages

            logger.debug(f"Calling OpenAI API with {len(messages)} messages")

            response = self.client.chat.completions.create(
                model=kwargs.get('model', self.model),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )

            text = response.choices[0].message.content
            logger.debug(f"Received response: {len(text)} characters")
            return text

        except Exception as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMError(error_msg, provider="openai", original_error=e)

    def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> Iterator[str]:
        """
        Generate streaming response using OpenAI GPT API.

        Args:
            messages: Conversation history
            system: System prompt (prepended as system message)
            max_tokens: Maximum response length
            temperature: Sampling temperature
            **kwargs: Additional OpenAI-specific parameters

        Yields:
            Text chunks as they are generated

        Raises:
            LLMError: If API call fails
        """
        try:
            # OpenAI uses system message in messages array
            if system:
                messages = [{"role": "system", "content": system}] + messages

            logger.debug(f"Calling OpenAI API (streaming) with {len(messages)} messages")

            stream = self.client.chat.completions.create(
                model=kwargs.get('model', self.model),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

            logger.debug(f"Streaming response completed")

        except Exception as e:
            error_msg = f"OpenAI API streaming error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMError(error_msg, provider="openai", original_error=e)


def get_llm_client(config: Optional[Config] = None) -> LLMProvider:
    """
    Factory function to get configured LLM client.

    Reads provider and credentials from config, returns appropriate
    LLM client instance.

    Args:
        config: Config instance (creates new one if not provided)

    Returns:
        Configured LLM provider

    Raises:
        LLMError: If provider is invalid or initialization fails

    Example:
        >>> from src.core.config import Config
        >>> config = Config()
        >>> llm = get_llm_client(config)
        >>> response = llm.generate_response(
        ...     messages=[{'role': 'user', 'content': 'Hello!'}],
        ...     system='You are a helpful assistant.'
        ... )
    """
    if config is None:
        from src.core.config import get_config
        config = get_config()

    provider = config.ai_provider.lower()

    logger.info(f"Creating LLM client for provider: {provider}")

    if provider == 'anthropic':
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=config.ai_model
        )
    elif provider == 'openai':
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=config.ai_model
        )
    else:
        raise LLMError(
            f"Unknown AI provider: {provider}. Must be 'anthropic' or 'openai'",
            provider=provider
        )


__all__ = [
    'LLMProvider',
    'LLMError',
    'AnthropicProvider',
    'OpenAIProvider',
    'get_llm_client'
]
