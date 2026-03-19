"""Custom exceptions for the Odisseo Signal Atlas runtime."""

from __future__ import annotations

from datetime import datetime


class OdisseoError(Exception):
    """Base exception for project-specific failures."""


class ConfigurationError(OdisseoError):
    """Raised when local configuration is missing or invalid."""


class RemoteAPIError(OdisseoError):
    """Raised when a remote API call fails in a meaningful way."""


class RateLimitError(RemoteAPIError):
    """Raised when the X API asks the client to back off temporarily."""

    def __init__(
        self,
        message: str,
        *,
        retry_after_seconds: int,
        reset_at: datetime | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
        self.reset_at = reset_at
