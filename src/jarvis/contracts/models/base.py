"""Shared base types used across contract groups."""

from pydantic import BaseModel


class JarvisBaseModel(BaseModel):
    """Base model for all Jarvis contracts.

    Provides common configuration for validation and serialization.
    """

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "extra": "forbid",
    }
