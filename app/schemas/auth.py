"""
Authentication Pydantic schemas
"""
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from app.db.models.user import UserRole, UserCategory


def validate_password_length(value: str) -> str:
    """
    Validate password length: minimum 8 characters, maximum 128 characters.
    Note: bcrypt_sha256 handles passwords of any length, but we limit to 128 for security.

    Args:
        value: Password string

    Returns:
        Validated password string

    Raises:
        ValueError: If password doesn't meet requirements
    """
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")

    # Reasonable maximum length (bcrypt_sha256 handles any length, but we limit for security)
    if len(value) > 128:
        raise ValueError(
            "Password cannot exceed 128 characters. Please use a shorter password.")

    return value


class LoginRequest(BaseModel):
    """Request schema for login endpoint"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128,
                          description="User password (8-128 characters)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_length(v)


class RegisterRequest(BaseModel):
    """Request schema for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128,
                          description="User password (minimum 8 characters, max 128 characters)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_length(v)


class SignUpRequest(BaseModel):
    """Request schema for user sign up"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128,
                          description="User password (minimum 8 characters, max 128 characters)")
    category: Optional[str] = Field(None, description="User category: personal or organization")
    gst_number: Optional[str] = Field(None, max_length=15, description="GST number (required for organizations)")
    shipping_address1: Optional[str] = Field(None, max_length=255, description="Shipping address line 1")
    shipping_address2: Optional[str] = Field(None, max_length=255, description="Shipping address line 2")
    shipping_pin: Optional[str] = Field(None, max_length=10, description="PIN code")
    shipping_city: Optional[str] = Field(None, max_length=100, description="City")
    shipping_state: Optional[str] = Field(None, max_length=100, description="State")
    shipping_country: Optional[str] = Field(default="India", max_length=100, description="Country")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_length(v)
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_lower = v.lower()
            if v_lower not in ['personal', 'organization']:
                raise ValueError("Category must be 'personal' or 'organization'")
            return v_lower
        return v
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces and convert to uppercase
            v = v.replace(' ', '').replace('-', '').upper()
            if len(v) != 15:
                raise ValueError("GST number must be 15 characters")
            if not v.isalnum():
                raise ValueError("GST number must be alphanumeric")
        return v
    
    @field_validator('shipping_pin')
    @classmethod
    def validate_shipping_pin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces
            v = v.replace(' ', '')
            if not v.isdigit() or len(v) != 6:
                raise ValueError("PIN code must be 6 digits")
        return v
    
    @model_validator(mode='after')
    def validate_organization_gst(self):
        """Validate that GST number is provided for organizations"""
        if self.category == 'organization' and not self.gst_number:
            raise ValueError("GST number is required for organizations")
        return self
    
    @model_validator(mode='after')
    def validate_shipping_address(self):
        """Validate that shipping address fields are provided together"""
        address_fields = [
            self.shipping_address1,
            self.shipping_pin,
            self.shipping_city,
            self.shipping_state,
            self.shipping_country
        ]
        filled_fields = [f for f in address_fields if f]
        
        # If any address field is filled, all required fields must be filled
        if filled_fields:
            if not all([self.shipping_address1, self.shipping_pin, self.shipping_city, 
                       self.shipping_state, self.shipping_country]):
                raise ValueError("All shipping address fields (address1, pin, city, state, country) are required together")
        
        return self


class VerifyRequest(BaseModel):
    """Request schema for OTP verification endpoint"""
    email: EmailStr = Field(..., description="User email address")
    code: str = Field(..., min_length=6, max_length=6,
                      description="6-digit OTP code")


class ChangePasswordRequest(BaseModel):
    """Request schema for changing password"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128,
                              description="New password (minimum 8 characters, max 128 characters)")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_length(v)


class AssignRoleRequest(BaseModel):
    """Request schema for assigning user role"""
    email: EmailStr = Field(..., description="User email address")
    role: UserRole = Field(..., description="Role to assign (user or owner)")


class CreateOwnerRequest(BaseModel):
    """Request schema for creating the first owner user"""
    email: EmailStr = Field(..., description="Owner email address")
    password: str = Field(..., min_length=8, max_length=128,
                          description="Owner password (minimum 8 characters, max 128 characters)")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_length(v)


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user (admin only)"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128,
                          description="User password (minimum 8 characters, max 128 characters)")
    category: Optional[str] = Field(None, description="User category: personal or organization")
    gst_number: Optional[str] = Field(None, max_length=15, description="GST number (required for organizations)")
    shipping_address1: Optional[str] = Field(None, max_length=255, description="Shipping address line 1")
    shipping_address2: Optional[str] = Field(None, max_length=255, description="Shipping address line 2")
    shipping_pin: Optional[str] = Field(None, max_length=10, description="PIN code")
    shipping_city: Optional[str] = Field(None, max_length=100, description="City")
    shipping_state: Optional[str] = Field(None, max_length=100, description="State")
    shipping_country: Optional[str] = Field(default="India", max_length=100, description="Country")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_length(v)
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_lower = v.lower()
            if v_lower not in ['personal', 'organization']:
                raise ValueError("Category must be 'personal' or 'organization'")
            return v_lower
        return v
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces and convert to uppercase
            v = v.replace(' ', '').replace('-', '').upper()
            if len(v) != 15:
                raise ValueError("GST number must be 15 characters")
            if not v.isalnum():
                raise ValueError("GST number must be alphanumeric")
        return v
    
    @field_validator('shipping_pin')
    @classmethod
    def validate_shipping_pin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces
            v = v.replace(' ', '')
            if not v.isdigit() or len(v) != 6:
                raise ValueError("PIN code must be 6 digits")
        return v
    
    @model_validator(mode='after')
    def validate_organization_gst(self):
        """Validate that GST number is provided for organizations"""
        if self.category == 'organization' and not self.gst_number:
            raise ValueError("GST number is required for organizations")
        return self
    
    @model_validator(mode='after')
    def validate_shipping_address(self):
        """Validate that shipping address fields are provided together"""
        address_fields = [
            self.shipping_address1,
            self.shipping_pin,
            self.shipping_city,
            self.shipping_state,
            self.shipping_country
        ]
        filled_fields = [f for f in address_fields if f]
        
        # If any address field is filled, all required fields must be filled
        if filled_fields:
            if not all([self.shipping_address1, self.shipping_pin, self.shipping_city, 
                       self.shipping_state, self.shipping_country]):
                raise ValueError("All shipping address fields (address1, pin, city, state, country) are required together")
        
        return self


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    role: UserRole
    is_active: bool
    category: Optional[str] = None
    gst_number: Optional[str] = None
    shipping_address1: Optional[str] = None
    shipping_address2: Optional[str] = None
    shipping_pin: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_country: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    total_quotes: Optional[int] = 0

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile"""
    category: Optional[str] = Field(None, description="User category: personal or organization")
    gst_number: Optional[str] = Field(None, max_length=15, description="GST number (required for organizations)")
    shipping_address1: Optional[str] = Field(None, max_length=255, description="Shipping address line 1")
    shipping_address2: Optional[str] = Field(None, max_length=255, description="Shipping address line 2")
    shipping_pin: Optional[str] = Field(None, max_length=10, description="PIN code")
    shipping_city: Optional[str] = Field(None, max_length=100, description="City")
    shipping_state: Optional[str] = Field(None, max_length=100, description="State")
    shipping_country: Optional[str] = Field(None, max_length=100, description="Country")

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_lower = v.lower()
            if v_lower not in ['personal', 'organization']:
                raise ValueError("Category must be 'personal' or 'organization'")
            return v_lower
        return v
    
    @field_validator('gst_number')
    @classmethod
    def validate_gst_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces and convert to uppercase
            v = v.replace(' ', '').replace('-', '').upper()
            if len(v) != 15:
                raise ValueError("GST number must be 15 characters")
            if not v.isalnum():
                raise ValueError("GST number must be alphanumeric")
        return v
    
    @field_validator('shipping_pin')
    @classmethod
    def validate_shipping_pin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Remove spaces
            v = v.replace(' ', '')
            if not v.isdigit() or len(v) != 6:
                raise ValueError("PIN code must be 6 digits")
        return v
    
    @model_validator(mode='after')
    def validate_organization_gst(self):
        """Validate that GST number is provided for organizations"""
        if self.category == 'organization' and not self.gst_number:
            raise ValueError("GST number is required for organizations")
        return self
    
    @model_validator(mode='after')
    def validate_shipping_address(self):
        """Validate that shipping address fields are provided together"""
        address_fields = [
            self.shipping_address1,
            self.shipping_pin,
            self.shipping_city,
            self.shipping_state,
            self.shipping_country
        ]
        filled_fields = [f for f in address_fields if f]
        
        # If any address field is filled, all required fields must be filled
        if filled_fields:
            if not all([self.shipping_address1, self.shipping_pin, self.shipping_city, 
                       self.shipping_state, self.shipping_country]):
                raise ValueError("All shipping address fields (address1, pin, city, state, country) are required together")
        
        return self


class AuthTokenData(BaseModel):
    """Authentication token data"""
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class TokenResponse(BaseModel):
    """Token response schema with user data"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    # Optional, as it's set in HTTP-only cookie
    refresh_token: Optional[str] = None


class UserStats(BaseModel):
    """User statistics schema"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    inactive_users: int = Field(..., description="Number of inactive users")
    users_created_this_month: int = Field(
        ..., description="Number of users created in the current month")


class UsersListResponse(BaseModel):
    """Users list response with pagination and statistics"""
    items: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")
    stats: UserStats = Field(..., description="User statistics")
