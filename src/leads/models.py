"""Input validation for the leads API."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LeadCreate(BaseModel):
    """A contact-form lead as submitted by the website.

    Whitespace is stripped before the length checks, so blank values fail ``min_length``.
    Unknown fields are ignored so the form can add fields (e.g. a honeypot) without breaking the API.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)
