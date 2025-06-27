# Endpoint Development Template & Standards

## 🎯 **Quick Reference Checklist**

When creating a new endpoint, ensure you follow these standards:

### ✅ **Required Imports**
```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
from ..models.response_models import SuccessResponse, ErrorResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..utils.cookies import get_cookies
```

### ✅ **Authentication**
- Use `@require_auth` decorator for protected endpoints
- Handle authentication errors consistently

### ✅ **Logging**
- Use `log_endpoint_call()` at the start
- Use `log_success()` for successful operations
- Use `log_error()` for error handling

### ✅ **Input Validation**
- Validate case IDs with `validate_case_id()`
- Sanitize inputs with `sanitize_input()`
- Return 400 errors for invalid inputs

### ✅ **Response Models**
- Always specify `response_model` for every endpoint
- Use Pydantic models from `response_models.py`
- Include proper validation and documentation

### ✅ **Error Handling**
- Use `HTTPException` with appropriate status codes
- Provide meaningful error messages
- Log all errors with context

### ✅ **Documentation**
- Add `summary` and `description` to all endpoints
- Use proper tags for API organization
- Include example responses in models

### ✅ **Frontend Synchronization** ⭐ **NEW**
- **MANDATORY**: Add new endpoint to frontend UI in `backend/frontend-testing-tool/src/App.js`
- Update `endpointConfig` object with new endpoint details
- Test endpoint through frontend UI before committing
- Follow this format:
```javascript
{ path: '/your-endpoint/{case_id}', method: 'GET', name: 'Your Endpoint Name' }
```

### ✅ **Testing**
- Test endpoint with real case IDs
- Verify response format matches model
- Check error handling scenarios

## 📝 **Standard Endpoint Template**

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
from ..models.response_models import SuccessResponse, ErrorResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..utils.cookies import get_cookies

router = APIRouter(tags=["Your Tag"])

# NOTE: Always specify response_model for every endpoint
@router.get("/your-endpoint/{case_id}", response_model=SuccessResponse)
@require_auth
async def your_endpoint(case_id: str, optional_param: Optional[str] = None):
    """
    Brief description of what this endpoint does.
    
    Args:
        case_id: Case ID to process
        optional_param: Optional parameter description
        
    Returns:
        SuccessResponse: Description of the response
        
    Raises:
        HTTPException: 400 if invalid case_id
        HTTPException: 404 if case not found
        HTTPException: 500 for internal errors
    """
    try:
        # 1. Input validation
        if not validate_case_id(case_id):
            log_error("your_endpoint", ValueError("Invalid case ID format"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        # 2. Log the call
        log_endpoint_call("your_endpoint", case_id, optional_param=optional_param)
        
        # 3. Get authentication data
        cookies_data = get_cookies()
        # ... extract cookie header and user agent
        
        # 4. Your business logic here
        result = await your_business_logic(case_id, cookies_data)
        
        # 5. Log success
        log_success("your_endpoint", case_id, result_count=len(result))
        
        # 6. Return standardized response
        return SuccessResponse(
            message="Operation completed successfully",
            status="success",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("your_endpoint", e, case_id)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def your_business_logic(case_id: str, cookies_data: dict) -> Dict[str, Any]:
    """Internal function for business logic."""
    # Your implementation here
    pass
```

## 🔧 **Common Patterns**

### **Case ID Validation**
```python
if not validate_case_id(case_id):
    log_error("endpoint_name", ValueError("Invalid case ID format"), case_id)
    raise HTTPException(status_code=400, detail="Invalid case ID format")
```

### **Authentication Setup**
```python
cookies_data = get_cookies()
cookie_header = _extract_cookie_header(cookies_data)
user_agent = _get_user_agent(cookies_data)

if not cookie_header:
    log_error("endpoint_name", ValueError("No valid cookies found"), case_id)
    raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
```

### **External API Calls**
```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        url, 
        params=params, 
        headers=headers,
        timeout=30,
        follow_redirects=False
    )
    
    if response.status_code != 200:
        log_error("endpoint_name", ValueError(f"API error: {response.status_code}"), case_id)
        raise HTTPException(status_code=response.status_code, detail="External API error")
```

### **Data Processing**
```python
try:
    processed_data = process_data(raw_data)
except Exception as e:
    log_error("endpoint_name", e, case_id, step="data_processing")
    raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}")
```

## 📊 **Response Model Examples**

### **Simple Success Response**
```python
return SuccessResponse(
    message="Data retrieved successfully",
    status="success",
    data={"case_id": case_id, "result": data}
)
```

### **Complex Response with Custom Model**
```python
# Define in response_models.py
class YourResponseModel(BaseModel):
    case_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]

# Use in endpoint
@router.get("/your-complex-endpoint/{case_id}", response_model=YourResponseModel)
def your_complex_endpoint(...):
    ...
    return YourResponseModel(
        case_id=case_id,
        data=processed_data,
        metadata={"processed_at": datetime.now().isoformat()}
    )
```

### **Error Response**
```python
# This is handled automatically by FastAPI when you raise HTTPException
# But you can also return custom error responses:
return ErrorResponse(
    detail="Specific error message",
    error_code="SPECIFIC_ERROR",
    status_code=400
)
```

## 🚨 **Common Mistakes to Avoid**

### ❌ **Don't Do This**
```python
# No input validation
@router.get("/bad/{case_id}")
async def bad_endpoint(case_id: str):
    # No logging
    # No error handling
    return {"data": "bad"}

# Inconsistent error handling
@router.get("/inconsistent/{case_id}")
async def inconsistent_endpoint(case_id: str):
    try:
        # ... logic
        return {"success": True}  # Raw dict instead of model
    except Exception as e:
        return {"error": str(e)}  # Inconsistent error format
```

### ✅ **Do This Instead**
```python
# Proper validation and logging
@router.get("/good/{case_id}", response_model=SuccessResponse)
@require_auth
async def good_endpoint(case_id: str):
    if not validate_case_id(case_id):
        log_error("good_endpoint", ValueError("Invalid case ID"), case_id)
        raise HTTPException(status_code=400, detail="Invalid case ID format")
    
    log_endpoint_call("good_endpoint", case_id)
    
    try:
        # ... logic
        log_success("good_endpoint", case_id)
        return SuccessResponse(message="Success", data={"result": "good"})
    except Exception as e:
        log_error("good_endpoint", e, case_id)
        raise HTTPException(status_code=500, detail=str(e))
```

## 🔍 **Testing Your New Endpoint**

### **Test Cases to Include**
1. **Valid case ID** - Should return success
2. **Invalid case ID** - Should return 400 error
3. **No authentication** - Should return 401 error
4. **Case not found** - Should return 404 error
5. **Internal error** - Should return 500 error

### **Example Test**
```python
def test_your_endpoint():
    # Test with valid case ID
    response = client.get("/your-endpoint/12345")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Test with invalid case ID
    response = client.get("/your-endpoint/invalid!")
    assert response.status_code == 400
    
    # Test without authentication
    # (Clear cookies first)
    response = client.get("/your-endpoint/12345")
    assert response.status_code == 401
```

## 📋 **Pre-Launch Checklist**

Before deploying a new endpoint, verify:

- [ ] Uses `@require_auth` decorator (if needed)
- [ ] Validates inputs with `validate_case_id()` or similar
- [ ] Uses `log_endpoint_call()`, `log_success()`, `log_error()`
- [ ] Returns `SuccessResponse` or custom Pydantic model
- [ ] Handles all expected error cases
- [ ] Has comprehensive docstring
- [ ] Includes proper tags for OpenAPI docs
- [ ] Tested with various input scenarios
- [ ] Follows naming conventions
- [ ] No hardcoded values or secrets

## 🎯 **Quick Copy-Paste Template**

```python
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
from ..models.response_models import SuccessResponse
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..utils.cookies import get_cookies

router = APIRouter(tags=["Your Tag"])

@router.get("/your-endpoint/{case_id}", response_model=SuccessResponse)
@require_auth
async def your_endpoint(case_id: str):
    """Your endpoint description."""
    try:
        if not validate_case_id(case_id):
            log_error("your_endpoint", ValueError("Invalid case ID"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        log_endpoint_call("your_endpoint", case_id)
        
        # Your logic here
        result = {"case_id": case_id, "data": "your_data"}
        
        log_success("your_endpoint", case_id)
        return SuccessResponse(message="Success", data=result)
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("your_endpoint", e, case_id)
        raise HTTPException(status_code=500, detail=str(e))
```

## 📋 **Pre-Commit Checklist**

Before committing any new endpoint, ensure:

- [ ] Endpoint follows all template standards above
- [ ] Response model is properly defined and used
- [ ] Error handling is comprehensive
- [ ] Logging is implemented
- [ ] Documentation is complete
- [ ] **FRONTEND**: Endpoint added to `backend/frontend-testing-tool/src/App.js`
- [ ] **FRONTEND**: Endpoint tested through frontend UI
- [ ] **FRONTEND**: Endpoint appears in correct category in UI
- [ ] All tests pass
- [ ] Code is formatted and linted

## 🔄 **Frontend Synchronization Process**

1. **Create Backend Endpoint** → Follow template above
2. **Add to Frontend** → Update `endpointConfig` in `App.js`
3. **Test Integration** → Use frontend UI to test endpoint
4. **Commit Both** → Backend and frontend changes together
5. **Verify** → Check that endpoint appears in frontend UI

**Example Frontend Addition:**
```javascript
// In backend/frontend-testing-tool/src/App.js
caseManagement: {
  name: 'Case Management',
  endpoints: [
    // ... existing endpoints ...
    { path: '/case-management/sms-logs/{case_id}', method: 'GET', name: 'Get SMS Logs' }
  ]
}
```

---

**Remember**: Consistency is key! Every endpoint should follow the same patterns for maintainability and reliability. 