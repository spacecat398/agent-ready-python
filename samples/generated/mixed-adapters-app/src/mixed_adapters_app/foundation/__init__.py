"""Provider-independent application foundation."""

from .config import CoreSettings, load_core_settings
from .errors import (
    AppError,
    AuthenticationError,
    ConfigurationError,
    ProviderError,
    RateLimitError,
    ResponseFormatError,
    TimeoutError,
)

__all__ = [
    "AppError",
    "AuthenticationError",
    "ConfigurationError",
    "CoreSettings",
    "ProviderError",
    "RateLimitError",
    "ResponseFormatError",
    "TimeoutError",
    "load_core_settings",
]
