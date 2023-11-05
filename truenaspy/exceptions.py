"""Exceptions for Truenas connect."""


class TruenasError(Exception):
    """General exception."""


class TruenasConnectionError(TruenasError):
    """Connection exception."""


class TruenasAuthenticationError(TruenasError):
    """Tailscale authentication exception."""
