"""Stable application error categories."""


class AppError(Exception):
    """Base class for errors safe to translate at an interface boundary."""


class ConfigurationError(AppError):
    """Required configuration is missing or invalid."""


class AuthenticationError(AppError):
    """A provider rejected the configured credentials or permissions."""


class RateLimitError(AppError):
    """A provider rate limit remained after the allowed retries."""


class TimeoutError(AppError):
    """An operation exceeded its configured time limit."""


class ProviderError(AppError):
    """An external provider failed or rejected a request."""


class ResponseFormatError(AppError):
    """An external response did not satisfy the project contract."""
