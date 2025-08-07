from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

class SuccessResponse(BaseModel):
    """Standard success response model"""
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

class PaginationResponse(BaseModel):
    """Pagination metadata model"""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

class PaginatedResponse(BaseModel):
    """Generic paginated response model"""
    items: List[Dict[str, Any]] = Field(..., description="List of items")
    pagination: PaginationResponse = Field(..., description="Pagination metadata")

class ValidationErrorDetail(BaseModel):
    """Validation error detail model"""
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: Optional[Any] = Field(None, description="The invalid value")

class ValidationErrorResponse(BaseModel):
    """Validation error response model"""
    error: str = Field(default="validation_error", description="Error type")
    message: str = Field(default="Validation failed", description="Error message")
    details: List[ValidationErrorDetail] = Field(..., description="Validation error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
