"""Input validation for the leads API."""

import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

# Line breaks and tabs are normal in a multi-line message; "\r" covers CRLF line breaks.
MESSAGE_ALLOWED_CONTROLS = frozenset("\n\r\t")


def contains_control_chars(value: str, allowed: frozenset[str] = frozenset()) -> bool:
    """True if ``value`` has a Unicode control character (category Cc) outside ``allowed``."""
    return any(unicodedata.category(ch) == "Cc" and ch not in allowed for ch in value)


def _reject_control_chars(value: Any, allowed: frozenset[str] = frozenset()) -> Any:
    # A custom error type keeps the message fixed (no input echoed) and distinct from "value_error".
    if isinstance(value, str) and contains_control_chars(value, allowed):
        raise PydanticCustomError(
            "control_characters", "must not contain control characters"
        )
    return value


class LeadCreate(BaseModel):
    """A contact-form lead as submitted by the website.

    Control characters are checked on the raw value, before whitespace is stripped, so they are rejected
    rather than silently trimmed. Whitespace is stripped before the length checks, so blank values fail
    ``min_length``. Unknown fields are ignored; the honeypot field ``website`` is handled in ``app.py``.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("name", "email", mode="before")
    @classmethod
    def _single_line_fields(cls, value: Any) -> Any:
        return _reject_control_chars(value)

    @field_validator("message", mode="before")
    @classmethod
    def _message_field(cls, value: Any) -> Any:
        return _reject_control_chars(value, MESSAGE_ALLOWED_CONTROLS)
