# 🚀 Quick Reference: Endpoint Standards

## 📋 **Essential Imports**
```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from ..models.response_models import SuccessResponse, ErrorResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..utils.cookies import get_cookies
```

## 🎯 **Standard Endpoint Structure**
```python
@router.get("/your-endpoint/{case_id}", response_model=SuccessResponse)
@require_auth
async def your_endpoint(case_id: str):
    """Your endpoint description."""
    try:
        # 1. Validate input
        if not validate_case_id(case_id):
            log_error("your_endpoint", ValueError("Invalid case ID"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        # 2. Log call
        log_endpoint_call("your_endpoint", case_id)
        
        # 3. Your logic here
        result = {"case_id": case_id, "data": "your_data"}
        
        # 4. Log success
        log_success("your_endpoint", case_id)
        
        # 5. Return response
        return SuccessResponse(message="Success", data=result)
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("your_endpoint", e, case_id)
        raise HTTPException(status_code=500, detail=str(e))
```

## 🔧 **Common Patterns**

### **Input Validation**
```python
if not validate_case_id(case_id):
    log_error("endpoint_name", ValueError("Invalid case ID"), case_id)
    raise HTTPException(status_code=400, detail="Invalid case ID format")
```

### **Authentication Setup**
```python
cookies_data = get_cookies()
cookie_header = _extract_cookie_header(cookies_data)
user_agent = _get_user_agent(cookies_data)
```

### **External API Call**
```python
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers, timeout=30)
    if response.status_code != 200:
        log_error("endpoint_name", ValueError(f"API error: {response.status_code}"), case_id)
        raise HTTPException(status_code=response.status_code, detail="External API error")
```

### **Success Response**
```python
return SuccessResponse(
    message="Operation successful",
    status="success",
    data=your_data
)
```

### **Error Response**
```python
raise HTTPException(status_code=400, detail="Error message")
```

## 📊 **HTTP Status Codes**
- `200` - Success
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (no auth)
- `404` - Not Found
- `500` - Internal Server Error

## 🎯 **Pre-Launch Checklist**
- [ ] `@require_auth` decorator (if needed)
- [ ] `validate_case_id()` for case IDs
- [ ] `log_endpoint_call()` at start
- [ ] `log_success()` before return
- [ ] `log_error()` in exception handlers
- [ ] `SuccessResponse` or custom model
- [ ] Comprehensive docstring
- [ ] Proper tags
- [ ] Error handling for all cases

## 🚨 **Common Mistakes**
- ❌ Raw dict returns instead of `SuccessResponse`
- ❌ No input validation
- ❌ Missing logging
- ❌ Inconsistent error handling
- ❌ No authentication decorator

## 📚 **Full Documentation**
- **Template**: `ENDPOINT_TEMPLATE.md`
- **Examples**: `ENDPOINT_EXAMPLES.md`
- **QA Report**: `QA_QC_REPORT.md`

---

**Remember**: Copy the standard structure and customize for your needs! 