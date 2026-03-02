"""
Shipping address request/response schemas
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ShippingAddressBase(BaseModel):
    name: str = Field(..., description="Recipient name")
    phone: str = Field(..., description="Contact phone number")
    country: str = Field(default="India", description="Country")
    state: str = Field(..., description="State or region")
    city: str = Field(..., description="City")
    address1: str = Field(..., description="Address line 1")
    address2: Optional[str] = Field(default=None, description="Address line 2")
    postal_code: str = Field(..., description="Postal/ZIP code")
    company: Optional[str] = Field(default=None, description="Company name")
    instructions: Optional[str] = Field(default=None, description="Delivery instructions")
    is_default: bool = Field(default=False, description="Whether this is the default address")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must contain between 7 and 15 digits")
        return value.strip()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        normalized = value.replace(" ", "")
        if len(normalized) < 4 or len(normalized) > 10:
            raise ValueError("Postal code must be between 4 and 10 characters")
        return normalized


class ShippingAddressCreate(ShippingAddressBase):
    """Payload for creating a shipping address"""
    pass


class ShippingAddressUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="Recipient name")
    phone: Optional[str] = Field(default=None, description="Contact phone number")
    country: Optional[str] = Field(default=None, description="Country")
    state: Optional[str] = Field(default=None, description="State or region")
    city: Optional[str] = Field(default=None, description="City")
    address1: Optional[str] = Field(default=None, description="Address line 1")
    address2: Optional[str] = Field(default=None, description="Address line 2")
    postal_code: Optional[str] = Field(default=None, description="Postal/ZIP code")
    company: Optional[str] = Field(default=None, description="Company name")
    instructions: Optional[str] = Field(default=None, description="Delivery instructions")
    is_default: Optional[bool] = Field(default=None, description="Whether this is the default address")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 7 or len(digits) > 15:
            raise ValueError("Phone number must contain between 7 and 15 digits")
        return value.strip()

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.replace(" ", "")
        if len(normalized) < 4 or len(normalized) > 10:
            raise ValueError("Postal code must be between 4 and 10 characters")
        return normalized

    @model_validator(mode="after")
    def ensure_updates_present(self):
        if not any(
            [
                self.name,
                self.phone,
                self.country,
                self.state,
                self.city,
                self.address1,
                self.address2,
                self.postal_code,
                self.company,
                self.instructions,
                self.is_default is not None,
            ]
        ):
            raise ValueError("At least one field must be provided to update the address")
        return self


class ShippingAddressResponse(ShippingAddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

