"""Input validation for the leads API."""

import unicodedata
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic_core import PydanticCustomError

# Rejected Unicode categories: Cc control (NUL, ESC, ...), Cf invisible format (bidi overrides such as U+202E,
# zero-width space, BOM), Zl/Zp line and paragraph separators (U+2028, U+2029).
REJECTED_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})
# A multi-line message needs line breaks and tabs ("\r" covers CRLF). Kept so normal text works: zero-width
# joiner/non-joiner (emoji sequences such as family or flag emoji, some scripts) and the soft hyphen (pasted text).
MESSAGE_ALLOWED = frozenset("\n\r\t\u200d\u200c\u00ad")


def contains_forbidden_chars(value: str, allowed: frozenset[str] = frozenset()) -> bool:
    """True if ``value`` has a control, format or separator character outside ``allowed``."""
    return any(
        unicodedata.category(ch) in REJECTED_CATEGORIES and ch not in allowed
        for ch in value
    )


def _reject_forbidden_chars(value: Any, allowed: frozenset[str] = frozenset()) -> Any:
    # A custom error type keeps the message fixed (no input echoed) and distinct from "value_error".
    if isinstance(value, str) and contains_forbidden_chars(value, allowed):
        raise PydanticCustomError(
            "control_characters", "must not contain control or formatting characters"
        )
    return value


class LeadCreate(BaseModel):
    """A contact-form lead as submitted by the website.

    Control, format and separator characters are checked on the raw value, before whitespace is stripped, so they are rejected
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
        return _reject_forbidden_chars(value)

    @field_validator("message", mode="before")
    @classmethod
    def _message_field(cls, value: Any) -> Any:
        return _reject_forbidden_chars(value, MESSAGE_ALLOWED)
