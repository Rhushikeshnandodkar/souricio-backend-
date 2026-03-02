"""
Dashboard statistics schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.schemas.auth import UserResponse
from app.schemas.quote import OwnerQuoteSummaryResponse


class OverviewStats(BaseModel):
    """Overview statistics"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    total_quotes: int = Field(..., description="Total number of quotes")
    total_products: int = Field(..., description="Total number of products")
    total_revenue: Optional[Decimal] = Field(
        None, description="Total revenue from all quotes")


class QuoteStats(BaseModel):
    """Quote statistics"""
    draft: int = Field(..., description="Number of draft quotes")
    pending: int = Field(..., description="Number of pending quotes")
    approved: int = Field(..., description="Number of approved quotes")
    rejected: int = Field(..., description="Number of rejected quotes")
    expired: int = Field(..., description="Number of expired quotes")
    total_value: Optional[Decimal] = Field(
        None, description="Total value of all quotes")


class RevenueDataPoint(BaseModel):
    """Revenue data point for time series"""
    date: str = Field(..., description="Date in ISO format")
    revenue: Decimal = Field(..., description="Revenue for this period")


class QuoteTrendDataPoint(BaseModel):
    """Quote trend data point for time series"""
    date: str = Field(..., description="Date in ISO format")
    count: int = Field(...,
                       description="Number of quotes created in this period")
    draft: int = Field(0, description="Number of draft quotes")
    pending: int = Field(0, description="Number of pending quotes")
    approved: int = Field(0, description="Number of approved quotes")
    rejected: int = Field(0, description="Number of rejected quotes")
    expired: int = Field(0, description="Number of expired quotes")


class UserGrowthDataPoint(BaseModel):
    """User growth data point for time series"""
    date: str = Field(..., description="Date in ISO format")
    total_users: int = Field(..., description="Cumulative total users")
    new_users: int = Field(..., description="New users in this period")


class DashboardStatsResponse(BaseModel):
    """Complete dashboard statistics response"""
    overview: OverviewStats
    quotes: QuoteStats
    revenue_trend: List[RevenueDataPoint]
    quote_trend: List[QuoteTrendDataPoint]
    user_growth: List[UserGrowthDataPoint]
    recent_quotes: List[OwnerQuoteSummaryResponse]
    recent_users: List[UserResponse]
