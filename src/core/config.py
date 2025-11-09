"""
Configuration management for Arcane Arsenal.

Provides centralized configuration loading from environment variables
with sensible defaults for all settings.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Centralized configuration management for Arcane Arsenal.

    Loads configuration from environment variables with fallback defaults.
    Supports .env files via python-dotenv.

    Example:
        config = Config()
        print(config.ai_model)  # claude-3-5-sonnet-20241022
        print(config.port)      # 5000
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            env_file: Optional path to .env file. If None, auto-discovers .env
                     in project root or skips if not found.
        """
        # Try to load dotenv if available
        try:
            from dotenv import load_dotenv

            if env_file:
                load_dotenv(env_file)
                logger.info(f"Loaded configuration from {env_file}")
            else:
                # Auto-discover .env in project root
                project_root = Path(__file__).parent.parent.parent
                env_path = project_root / '.env'
                if env_path.exists():
                    load_dotenv(env_path)
                    logger.info(f"Loaded configuration from {env_path}")
                else:
                    logger.debug("No .env file found, using environment variables and defaults")
        except ImportError:
            logger.warning("python-dotenv not installed, .env files not supported")

        # === API Keys ===
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY', '')
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')

        # === Server Settings ===
        self.host = os.getenv('HOST', '0.0.0.0')
        self.port = int(os.getenv('PORT', '5000'))
        self.debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
        self.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

        # === Logging ===
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_file = os.getenv('LOG_FILE', None)

        # === AI Settings ===
        self.ai_provider = os.getenv('AI_PROVIDER', 'anthropic')  # anthropic or openai
        self.ai_model = os.getenv('AI_MODEL', 'claude-3-5-sonnet-20241022')
        self.ai_max_tokens = int(os.getenv('AI_MAX_TOKENS', '4096'))
        self.ai_temperature = float(os.getenv('AI_TEMPERATURE', '0.7'))

        # Prompt configuration
        self.ai_system_prompt_path = os.getenv(
            'AI_SYSTEM_PROMPT_PATH',
            str(Path(__file__).parent.parent / 'modules' / 'ai_dm' / 'prompts' / 'dm_system.txt')
        )

        # AI behavior settings
        self.ai_max_context_messages = int(os.getenv('AI_MAX_CONTEXT_MESSAGES', '10'))
        self.ai_max_context_events = int(os.getenv('AI_MAX_CONTEXT_EVENTS', '5'))
        self.ai_include_nearby_entities = os.getenv('AI_INCLUDE_NEARBY_ENTITIES', 'True').lower() in ('true', '1', 'yes')

        # === Database ===
        self.worlds_directory = os.getenv('WORLDS_DIR', 'worlds')

        # === Security ===
        self.enable_cors = os.getenv('ENABLE_CORS', 'False').lower() in ('true', '1', 'yes')
        self.allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')

    def validate(self) -> bool:
        """
        Validate configuration and log warnings for missing required values.

        Returns:
            True if config is valid, False if critical values are missing
        """
        valid = True

        # Check AI provider is configured
        if self.ai_provider not in ('anthropic', 'openai'):
            logger.error(f"Invalid AI_PROVIDER: {self.ai_provider}. Must be 'anthropic' or 'openai'")
            valid = False

        # Check API key for selected provider
        if self.ai_provider == 'anthropic' and not self.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not set. AI DM will not function.")
            # Not critical - might not be using AI features
        elif self.ai_provider == 'openai' and not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set. AI DM will not function.")

        # Warn about dev secret key in non-debug mode
        if not self.debug and self.secret_key == 'dev-secret-key-change-in-production':
            logger.warning("Using default SECRET_KEY in production mode! Set SECRET_KEY environment variable.")

        return valid

    def __repr__(self) -> str:
        """Safe representation hiding sensitive values."""
        return (
            f"Config("
            f"ai_provider={self.ai_provider}, "
            f"ai_model={self.ai_model}, "
            f"host={self.host}, "
            f"port={self.port}, "
            f"debug={self.debug})"
        )


# Global config instance (lazy-loaded)
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global config instance (singleton pattern).

    Returns:
        Global Config instance

    Example:
        from src.core.config import get_config
        config = get_config()
        print(config.ai_model)
    """
    global _config
    if _config is None:
        _config = Config()
        _config.validate()
    return _config


__all__ = ['Config', 'get_config']
