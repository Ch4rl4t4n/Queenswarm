"""Bee-hive-specific runtime errors."""


class VerificationRequiredError(RuntimeError):
    """Raised when a bee attempts to finalize user-visible output without proof."""
