"""
Standard API response schemas following REST API best practices
"""
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class APIResponse(BaseModel):
    """
    Standard API response wrapper.
    Provides consistent structure for all API responses.
    """
    status: str = Field(default="success", description="Response status")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(default=None, description="Response data payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {},
                "timestamp": "2024-01-01T00:00:00"
            }
        }


class ErrorDetail(BaseModel):
    """Error detail structure"""
    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Standard error response structure.
    Used for error responses across the API.
    """
    status: str = "error"
    message: str
    error: ErrorDetail
    timestamp: datetime = datetime.utcnow()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    size: int
    total: int
    pages: int


class PaginatedResponse(BaseModel):
    """
    Paginated response structure.
    Includes data array and pagination metadata.
    """
    status: str = "success"
    message: str = "Data retrieved successfully"
    data: list[Any]
    meta: PaginationMeta
    timestamp: datetime = datetime.utcnow()

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
