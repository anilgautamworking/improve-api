"""
Error handling utilities for API responses

Provides standardized error responses that don't expose internal details
while logging full error information server-side.
"""

import logging
from flask import request, jsonify
from typing import Optional, Dict, Any
import traceback

logger = logging.getLogger(__name__)

# Error codes for different error types
class ErrorCode:
    """Error code constants"""
    # Authentication errors (1000-1999)
    AUTH_NO_TOKEN = "AUTH_001"
    AUTH_INVALID_TOKEN = "AUTH_002"
    AUTH_EXPIRED_TOKEN = "AUTH_003"
    AUTH_INVALID_CREDENTIALS = "AUTH_004"
    AUTH_EMAIL_EXISTS = "AUTH_005"
    
    # Validation errors (2000-2999)
    VALIDATION_MISSING_FIELD = "VAL_001"
    VALIDATION_INVALID_FORMAT = "VAL_002"
    VALIDATION_INVALID_VALUE = "VAL_003"
    
    # Resource errors (3000-3999)
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    
    # Database errors (4000-4999)
    DB_CONNECTION_ERROR = "DB_001"
    DB_QUERY_ERROR = "DB_002"
    DB_SCHEMA_MISSING = "DB_003"
    
    # Server errors (5000-5999)
    SERVER_INTERNAL_ERROR = "SRV_001"
    SERVER_TIMEOUT = "SRV_002"
    SERVER_UNAVAILABLE = "SRV_003"


# User-friendly error messages
ERROR_MESSAGES = {
    ErrorCode.AUTH_NO_TOKEN: "Authentication required. Please log in.",
    ErrorCode.AUTH_INVALID_TOKEN: "Invalid authentication token. Please log in again.",
    ErrorCode.AUTH_EXPIRED_TOKEN: "Your session has expired. Please log in again.",
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Invalid email or password.",
    ErrorCode.AUTH_EMAIL_EXISTS: "An account with this email already exists.",
    
    ErrorCode.VALIDATION_MISSING_FIELD: "Required field is missing.",
    ErrorCode.VALIDATION_INVALID_FORMAT: "Invalid data format.",
    ErrorCode.VALIDATION_INVALID_VALUE: "Invalid value provided.",
    
    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    ErrorCode.RESOURCE_ALREADY_EXISTS: "This resource already exists.",
    
    ErrorCode.DB_CONNECTION_ERROR: "Database connection error. Please try again later.",
    ErrorCode.DB_QUERY_ERROR: "Database error occurred. Please try again later.",
    ErrorCode.DB_SCHEMA_MISSING: "Database schema is not set up. Please contact support.",
    
    ErrorCode.SERVER_INTERNAL_ERROR: "An internal error occurred. Please try again later.",
    ErrorCode.SERVER_TIMEOUT: "Request timed out. Please try again.",
    ErrorCode.SERVER_UNAVAILABLE: "Service is temporarily unavailable. Please try again later.",
}


def get_error_message(error_code: str, default: Optional[str] = None) -> str:
    """
    Get user-friendly error message for error code
    
    Args:
        error_code: Error code constant
        default: Default message if code not found
        
    Returns:
        User-friendly error message
    """
    return ERROR_MESSAGES.get(error_code, default or "An error occurred. Please try again.")


def log_error(
    error: Exception,
    error_code: str,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
):
    """
    Log error with full context for debugging
    
    Args:
        error: Exception object
        error_code: Error code constant
        context: Additional context dictionary
        user_id: Optional user ID for tracking
    """
    request_info = {
        "method": request.method if request else None,
        "path": request.path if request else None,
        "endpoint": request.endpoint if request else None,
        "user_id": user_id,
        "error_code": error_code,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if context:
        request_info.update(context)
    
    # Log full traceback for server-side debugging
    logger.error(
        f"Error [{error_code}]: {str(error)}\n"
        f"Context: {request_info}\n"
        f"Traceback:\n{traceback.format_exc()}",
        extra=request_info
    )


def error_response(
    error_code: str,
    status_code: int = 500,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None,
    user_id: Optional[str] = None
) -> tuple:
    """
    Create standardized error response
    
    Args:
        error_code: Error code constant
        status_code: HTTP status code
        message: Optional custom message (overrides default)
        details: Optional additional details (not exposed to client in production)
        error: Optional exception object for logging
        user_id: Optional user ID for tracking
        
    Returns:
        Tuple of (JSON response, status_code)
    """
    # Log error if provided
    if error:
        log_error(error, error_code, details, user_id)
    
    # Get user-friendly message
    user_message = message or get_error_message(error_code)
    
    # Build response
    response = {
        "error": user_message,
        "error_code": error_code,
    }
    
    # Add details only in debug mode (for development)
    import os
    if os.getenv("FLASK_DEBUG", "False").lower() == "true" and details:
        response["details"] = details
    
    return jsonify(response), status_code


def handle_exception(error: Exception, error_code: str = ErrorCode.SERVER_INTERNAL_ERROR, 
                     status_code: int = 500, user_id: Optional[str] = None) -> tuple:
    """
    Handle exception and return standardized error response
    
    Args:
        error: Exception object
        error_code: Error code constant
        status_code: HTTP status code
        user_id: Optional user ID for tracking
        
    Returns:
        Tuple of (JSON response, status_code)
    """
    return error_response(
        error_code=error_code,
        status_code=status_code,
        error=error,
        user_id=user_id
    )


def validation_error(field: str, message: Optional[str] = None) -> tuple:
    """
    Create validation error response
    
    Args:
        field: Field name that failed validation
        message: Optional custom message
        
    Returns:
        Tuple of (JSON response, status_code)
    """
    return error_response(
        error_code=ErrorCode.VALIDATION_MISSING_FIELD,
        status_code=400,
        message=message or f"Validation failed for field: {field}",
        details={"field": field}
    )


def not_found_error(resource: str = "Resource") -> tuple:
    """
    Create not found error response
    
    Args:
        resource: Resource name
        
    Returns:
        Tuple of (JSON response, status_code)
    """
    return error_response(
        error_code=ErrorCode.RESOURCE_NOT_FOUND,
        status_code=404,
        message=f"{resource} not found"
    )

