# Endpoint Standardization Examples

## 🔄 **Before vs After Examples**

### **Example 1: Simple Endpoint**

#### ❌ **Before (Non-Standardized)**
```python
from fastapi import APIRouter
import logging

router = APIRouter()

@router.get("/case/{case_id}/summary")
async def get_case_summary(case_id: str):
    logging.info(f"Getting summary for case {case_id}")
    
    try:
        # Business logic here
        summary = {"case_id": case_id, "status": "active"}
        return summary
    except Exception as e:
        logging.error(f"Error: {e}")
        return {"error": str(e)}
```

#### ✅ **After (Standardized)**
```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..models.response_models import SuccessResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..utils.cookies import get_cookies

router = APIRouter(tags=["Case Management"])

@router.get("/case/{case_id}/summary", response_model=SuccessResponse)
@require_auth
async def get_case_summary(case_id: str):
    """
    Get summary information for a case.
    
    Args:
        case_id: Case ID to get summary for
        
    Returns:
        SuccessResponse: Case summary information
        
    Raises:
        HTTPException: 400 if invalid case_id
        HTTPException: 404 if case not found
        HTTPException: 500 for internal errors
    """
    try:
        # Input validation
        if not validate_case_id(case_id):
            log_error("get_case_summary", ValueError("Invalid case ID format"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        # Log the call
        log_endpoint_call("get_case_summary", case_id)
        
        # Get authentication data
        cookies_data = get_cookies()
        
        # Business logic here
        summary = await get_case_summary_logic(case_id, cookies_data)
        
        # Log success
        log_success("get_case_summary", case_id, summary_keys=list(summary.keys()))
        
        # Return standardized response
        return SuccessResponse(
            message="Case summary retrieved successfully",
            status="success",
            data=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("get_case_summary", e, case_id)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def get_case_summary_logic(case_id: str, cookies_data: dict) -> Dict[str, Any]:
    """Internal function for case summary logic."""
    # Your implementation here
    return {"case_id": case_id, "status": "active", "processed_at": datetime.now().isoformat()}
```

### **Example 2: Complex Endpoint with External API**

#### ❌ **Before (Non-Standardized)**
```python
@router.post("/case/{case_id}/process")
async def process_case(case_id: str, data: dict):
    if not cookies_exist():
        return {"error": "No auth"}
    
    cookies = get_cookies()
    
    try:
        # Make external API call
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.example.com/process", json=data)
            
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "data": result}
        else:
            return {"error": f"API error: {response.status_code}"}
            
    except Exception as e:
        return {"error": str(e)}
```

#### ✅ **After (Standardized)**
```python
@router.post("/case/{case_id}/process", response_model=SuccessResponse)
@require_auth
async def process_case(case_id: str, data: dict):
    """
    Process case data through external API.
    
    Args:
        case_id: Case ID to process
        data: Data to process
        
    Returns:
        SuccessResponse: Processing results
        
    Raises:
        HTTPException: 400 if invalid case_id or data
        HTTPException: 500 for API or processing errors
    """
    try:
        # Input validation
        if not validate_case_id(case_id):
            log_error("process_case", ValueError("Invalid case ID format"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        if not data:
            log_error("process_case", ValueError("No data provided"), case_id)
            raise HTTPException(status_code=400, detail="No data provided")
        
        # Log the call
        log_endpoint_call("process_case", case_id, data_keys=list(data.keys()))
        
        # Get authentication data
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            log_error("process_case", ValueError("No valid cookies found"), case_id)
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        # Make external API call
        result = await process_case_logic(case_id, data, cookie_header, user_agent)
        
        # Log success
        log_success("process_case", case_id, result_status=result.get("status"))
        
        # Return standardized response
        return SuccessResponse(
            message="Case processed successfully",
            status="success",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("process_case", e, case_id)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def process_case_logic(case_id: str, data: dict, cookie_header: str, user_agent: str) -> Dict[str, Any]:
    """Internal function for case processing logic."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.example.com/process",
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            log_error("process_case_logic", ValueError(f"API error: {response.status_code}"), case_id)
            raise HTTPException(status_code=response.status_code, detail="External API error")
        
        return response.json()
```

## 🎯 **Step-by-Step Conversion Process**

### **Step 1: Update Imports**
```python
# Add these imports
from ..models.response_models import SuccessResponse, ErrorResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
```

### **Step 2: Add Authentication Decorator**
```python
# Add this decorator to protected endpoints
@require_auth
```

### **Step 3: Add Response Model**
```python
# Add response_model parameter
@router.get("/your-endpoint/{case_id}", response_model=SuccessResponse)
```

### **Step 4: Add Input Validation**
```python
# Add at the start of your function
if not validate_case_id(case_id):
    log_error("your_endpoint", ValueError("Invalid case ID format"), case_id)
    raise HTTPException(status_code=400, detail="Invalid case ID format")
```

### **Step 5: Add Logging**
```python
# Add at the start
log_endpoint_call("your_endpoint", case_id)

# Add before return
log_success("your_endpoint", case_id)

# Add in error handling
log_error("your_endpoint", e, case_id)
```

### **Step 6: Update Return Statement**
```python
# Replace raw dict returns with SuccessResponse
return SuccessResponse(
    message="Operation completed successfully",
    status="success",
    data=your_data
)
```

### **Step 7: Improve Error Handling**
```python
try:
    # Your logic here
    pass
except HTTPException:
    raise
except Exception as e:
    log_error("your_endpoint", e, case_id)
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
```

## 🔧 **Common Conversion Patterns**

### **Converting Raw Dict Returns**
```python
# Before
return {"status": "success", "data": result}

# After
return SuccessResponse(
    message="Operation successful",
    status="success",
    data=result
)
```

### **Converting Error Returns**
```python
# Before
return {"error": "Something went wrong"}

# After
raise HTTPException(status_code=500, detail="Something went wrong")
```

### **Converting Authentication Checks**
```python
# Before
if not cookies_exist():
    return {"error": "No auth"}

# After
# Use @require_auth decorator instead
@require_auth
async def your_endpoint():
    # No need to check cookies manually
```

### **Converting Logging**
```python
# Before
logging.info(f"Processing case {case_id}")
logging.error(f"Error: {e}")

# After
log_endpoint_call("your_endpoint", case_id)
log_error("your_endpoint", e, case_id)
```

## 📋 **Quick Conversion Checklist**

When converting an existing endpoint:

- [ ] Added required imports
- [ ] Added `@require_auth` decorator (if needed)
- [ ] Added `response_model=SuccessResponse`
- [ ] Added input validation with `validate_case_id()`
- [ ] Added `log_endpoint_call()` at start
- [ ] Added `log_success()` before return
- [ ] Added `log_error()` in exception handlers
- [ ] Changed raw dict returns to `SuccessResponse`
- [ ] Changed error returns to `HTTPException`
- [ ] Added comprehensive docstring
- [ ] Added proper tags
- [ ] Tested the converted endpoint

## 🎯 **Benefits of Standardization**

### **Before Standardization**
- ❌ Inconsistent error responses
- ❌ No input validation
- ❌ Poor logging
- ❌ Difficult debugging
- ❌ Inconsistent authentication
- ❌ Hard to maintain

### **After Standardization**
- ✅ Consistent error responses
- ✅ Proper input validation
- ✅ Comprehensive logging
- ✅ Easy debugging
- ✅ Centralized authentication
- ✅ Easy to maintain and extend

---

**Remember**: Start with one endpoint and gradually convert others. The benefits compound as you standardize more endpoints! 