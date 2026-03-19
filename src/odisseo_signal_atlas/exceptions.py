"""Custom exceptions for the Odisseo Signal Atlas runtime."""


class OdisseoError(Exception):
    """Base exception for project-specific failures."""


class ConfigurationError(OdisseoError):
    """Raised when local configuration is missing or invalid."""


class RemoteAPIError(OdisseoError):
    """Raised when a remote API call fails in a meaningful way."""

