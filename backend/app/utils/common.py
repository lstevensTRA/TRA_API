"""
Common utilities for TRA API Backend
Provides standardized authentication, error handling, and logging functions.
"""

import logging
from functools import wraps
from fastapi import HTTPException
from typing import Optional, Callable, Any
from datetime import datetime
from .cookies import cookies_exist

# Create logger for this module
logger = logging.getLogger(__name__)

class ErrorResponse:
    """Standardized error response model"""
    
    @staticmethod
    def create(detail: str, error_code: Optional[str] = None, status_code: int = 500) -> dict:
        """Create a standardized error response"""
        return {
            "detail": detail,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code
        }

def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for endpoints.
    Checks for valid cookies before allowing access.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not cookies_exist():
            logger.error("❌ Authentication required - no cookies found")
            raise HTTPException(
                status_code=401, 
                detail="Authentication required. Please log in first."
            )
        return await func(*args, **kwargs)
    return wrapper

def log_endpoint_call(endpoint: str, case_id: Optional[str] = None, **kwargs):
    """
    Standardized logging for endpoint calls.
    
    Args:
        endpoint: Name of the endpoint being called
        case_id: Case ID if applicable
        **kwargs: Additional context information
    """
    context = f"case_id: {case_id}" if case_id else "no case_id"
    additional_info = ", ".join([f"{k}: {v}" for k, v in kwargs.items()])
    
    if additional_info:
        logger.info(f"🔍 {endpoint} called - {context}, {additional_info}")
    else:
        logger.info(f"🔍 {endpoint} called - {context}")

def log_success(endpoint: str, case_id: Optional[str] = None, **kwargs):
    """
    Standardized logging for successful endpoint calls.
    
    Args:
        endpoint: Name of the endpoint
        case_id: Case ID if applicable
        **kwargs: Additional success information
    """
    context = f"case_id: {case_id}" if case_id else "no case_id"
    additional_info = ", ".join([f"{k}: {v}" for k, v in kwargs.items()])
    
    if additional_info:
        logger.info(f"✅ {endpoint} completed successfully - {context}, {additional_info}")
    else:
        logger.info(f"✅ {endpoint} completed successfully - {context}")

def log_error(endpoint: str, error: Exception, case_id: Optional[str] = None, **kwargs):
    """
    Standardized logging for endpoint errors.
    
    Args:
        endpoint: Name of the endpoint
        error: The exception that occurred
        case_id: Case ID if applicable
        **kwargs: Additional error context
    """
    context = f"case_id: {case_id}" if case_id else "no case_id"
    additional_info = ", ".join([f"{k}: {v}" for k, v in kwargs.items()])
    
    if additional_info:
        logger.error(f"❌ {endpoint} failed - {context}, {additional_info}, error: {str(error)}")
    else:
        logger.error(f"❌ {endpoint} failed - {context}, error: {str(error)}")

def validate_case_id(case_id: str) -> bool:
    """
    Validate case ID format.
    
    Args:
        case_id: Case ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not case_id:
        return False
    
    # Basic validation - case ID should be alphanumeric and reasonable length
    if not case_id.replace('-', '').replace('_', '').isalnum():
        return False
    
    if len(case_id) < 1 or len(case_id) > 50:
        return False
    
    return True

def sanitize_input(input_str: str) -> str:
    """
    Basic input sanitization.
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
    sanitized = input_str
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized.strip()

def format_currency(amount: float) -> str:
    """
    Format currency amounts consistently.
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted currency string
    """
    if amount is None:
        return "$0.00"
    
    try:
        return f"${amount:,.2f}"
    except (ValueError, TypeError):
        return "$0.00"

def format_percentage(value: float) -> str:
    """
    Format percentage values consistently.
    
    Args:
        value: Percentage value (0-100)
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "0.00%"
    
    try:
        return f"{value:.2f}%"
    except (ValueError, TypeError):
        return "0.00%"

def _extract_cookie_header(cookies: dict) -> str:
    """Extract cookie header string from cookies dict"""
    if not cookies:
        return None
    
    if isinstance(cookies, dict) and 'cookies' in cookies:
        return "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
    elif isinstance(cookies, str):
        return cookies
    
    return None

def _get_user_agent(cookies: dict) -> str:
    """Extract user agent from cookies dict"""
    if cookies and isinstance(cookies, dict) and 'user_agent' in cookies:
        return cookies['user_agent']
    return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' 