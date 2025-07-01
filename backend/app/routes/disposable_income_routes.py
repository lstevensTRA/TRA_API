from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
import logging
import httpx
from ..models.response_models import DisposableIncomeResponse, ErrorResponse, SuccessResponse
from ..utils.cookies import cookies_exist, get_cookies
from ..utils.common import require_auth, log_endpoint_call, log_success, log_error, validate_case_id
from ..routes.client_profile import get_client_profile_internal
from ..routes.irs_standards_routes import _get_irs_standards_internal, _extract_cookie_header, _get_user_agent
from datetime import datetime

router = APIRouter(tags=["Disposable Income"])

@router.get("/test", response_model=SuccessResponse)
async def test_disposable_income():
    """Test endpoint to verify the disposable income router is working."""
    return {"message": "Disposable income router is working!"}

# Logiqs API configuration
LOGIQS_BASE_URL = "https://tps.logiqs.com/API/CaseInterview"
LOGIQS_API_KEY = "4917fa0ce4694529a9b97ead1a60c932"
LOGIQS_API_URL = "https://tps.logiqs.com/publicapi/2020-02-22/cases/caseinfo"

@router.get("/case/{case_id}", response_model=DisposableIncomeResponse)
@require_auth
async def calculate_disposable_income(case_id: str):
    """
    Calculate monthly disposable income for a client case.
    
    This endpoint:
    1. Gets the client profile (income, real expenses, household info)
    2. Calculates IRS Standards for the client's location and household
    3. Determines total allowable expenses (higher of real vs IRS Standards)
    4. Calculates disposable income (monthly income - total allowable expenses)
    
    Args:
        case_id: Case ID to calculate disposable income for
    
    Returns:
        Detailed disposable income calculation with breakdown
    """
    try:
        # Validate case ID
        if not validate_case_id(case_id):
            log_error("calculate_disposable_income", ValueError("Invalid case ID format"), case_id)
            raise HTTPException(status_code=400, detail="Invalid case ID format")
        
        log_endpoint_call("calculate_disposable_income", case_id)
        
        # Get authentication data
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            log_error("calculate_disposable_income", ValueError("No valid cookies found"), case_id)
            raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
        
        # Step 1: Get client profile data
        logging.info(f"📊 Step 1: Getting client profile for case {case_id}")
        client_profile = await get_client_profile_internal(case_id, cookie_header, user_agent)
        
        if not client_profile:
            log_error("calculate_disposable_income", ValueError("Client profile not found"), case_id)
            raise HTTPException(status_code=404, detail="Client profile not found")
        
        # Extract key financial data using attribute access
        monthly_income = getattr(client_profile.financial_profile, "monthly_net", 0) or 0
        real_expenses_obj = getattr(client_profile.financial_profile, "expenses", None)
        # Convert Pydantic model to dictionary
        real_expenses = real_expenses_obj.dict() if real_expenses_obj else {}
        
        # Debug: print the type of real_expenses
        logging.info(f"📊 real_expenses type: {type(real_expenses)}")
        logging.info(f"📊 real_expenses content: {real_expenses}")
        
        household_info = getattr(client_profile, "personal", None)
        address_info = getattr(client_profile, "address", None)
        
        members_under_65 = getattr(household_info, "members_under_65", 0) if household_info else 0
        members_over_65 = getattr(household_info, "members_over_65", 0) if household_info else 0
        household_size = getattr(household_info, "household_size", None) if household_info else None
        county_id = getattr(household_info, "county_id", None) if household_info else None
        county_name = getattr(household_info, "county_name", None) if household_info else None
        state = getattr(address_info, "state", None) if address_info else None
        city = getattr(address_info, "city", None) if address_info else None
        
        logging.info(f"📊 Client financial data - Monthly income: ${monthly_income}, Household: {members_under_65} under 65, {members_over_65} over 65")
        
        # Step 2: Get IRS Standards
        logging.info(f"📊 Step 2: Getting IRS Standards for case {case_id}")
        irs_standards = await _get_irs_standards_for_case_internal(case_id, cookie_header, user_agent)
        
        if not irs_standards:
            log_error("calculate_disposable_income", ValueError("Failed to get IRS Standards"), case_id)
            raise HTTPException(status_code=500, detail="Failed to get IRS Standards")
        
        # Step 3: Calculate total allowable expenses
        logging.info(f"📊 Step 3: Calculating total allowable expenses")
        try:
            total_allowable = calculate_total_allowable_expenses(real_expenses, irs_standards)
        except Exception as e:
            log_error("calculate_disposable_income", e, case_id, step="calculate_total_allowable_expenses")
            raise HTTPException(status_code=500, detail=f"Error calculating expenses: {str(e)}")
        
        # Step 4: Calculate disposable income
        logging.info(f"📊 Step 4: Calculating disposable income")
        disposable_income = monthly_income - total_allowable
        
        # Step 5: Prepare detailed breakdown
        breakdown = create_expense_breakdown(real_expenses, irs_standards, total_allowable)
        
        # Safely extract IRS standards used
        irs_standards_used = {}
        if hasattr(irs_standards, 'Result'):
            irs_standards_used = getattr(irs_standards, 'Result', {})
        elif isinstance(irs_standards, dict):
            irs_standards_used = irs_standards.get('Result', {})
        else:
            irs_standards_used = {}
        
        result = {
            "case_id": case_id,
            "calculation_date": datetime.now().isoformat(),
            "monthly_income": monthly_income,
            "total_allowable_expenses": total_allowable,
            "monthly_disposable_income": disposable_income,
            "expense_breakdown": breakdown,
            "client_profile": {
                "household_size": household_size,
                "members_under_65": members_under_65,
                "members_over_65": members_over_65,
                "state": state,
                "city": city,
                "county_id": county_id,
                "county_name": county_name
            },
            "irs_standards_used": irs_standards_used,
            "real_expenses": real_expenses
        }
        
        log_success("calculate_disposable_income", case_id, disposable_income=f"${disposable_income:.2f}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        log_error("calculate_disposable_income", e, case_id)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def _get_irs_standards_for_case_internal(case_id: str, cookie_header: str, user_agent: str) -> Optional[Dict[str, Any]]:
    """Get IRS Standards for a case using internal logic"""
    try:
        # Get client profile to extract household info
        client_profile = await get_client_profile_internal(case_id, cookie_header, user_agent)
        if not client_profile:
            return None
        
        household_info = getattr(client_profile, "personal", None)
        members_under_65 = getattr(household_info, "members_under_65", 1) if household_info else 1
        members_over_65 = getattr(household_info, "members_over_65", 0) if household_info else 0
        county_id = getattr(household_info, "county_id", None) if household_info else None
        
        if not county_id:
            logging.warning(f"No county ID found for case {case_id}, using default")
            county_id = 203
        
        # Get IRS Standards
        return await _get_irs_standards_internal(members_under_65, members_over_65, county_id, cookie_header, user_agent)
        
    except Exception as e:
        logging.error(f"Error getting IRS Standards for case {case_id}: {str(e)}")
        return None

def calculate_total_allowable_expenses(real_expenses, irs_standards) -> float:
    # Defensive conversion - ensure we're working with dictionaries
    if hasattr(real_expenses, 'dict'):
        real_expenses = real_expenses.dict()
    elif not isinstance(real_expenses, dict):
        real_expenses = {}
    
    if hasattr(irs_standards, 'dict'):
        irs_standards = irs_standards.dict()
    elif not isinstance(irs_standards, dict):
        irs_standards = {}
    
    # Safely extract IRS data
    irs_data = {}
    if hasattr(irs_standards, 'Result') and isinstance(irs_standards.Result, dict):
        irs_data = irs_standards.Result
    elif hasattr(irs_standards, 'data') and isinstance(irs_standards.data, dict):
        irs_data = irs_standards.data
    elif isinstance(irs_standards, dict):
        irs_data = irs_standards.get("data", {})
    
    # Map IRS Standards categories to expense categories
    expense_categories = {
        "housing": ("housing", "Housing"),
        "housing_utilities": ("housing_utilities", "Housing"),  # IRS doesn't separate utilities
        "auto_operating": ("auto_operating", "OperatingCostCar"),
        "food": ("food", "Food"),
        "personal_care": ("personal_care", "PersonalCare"),
        "apparel": ("apparel", "Apparel"),
        "other1": ("other1", "Misc"),
        "other2": ("other2", "Misc")
    }
    
    total_allowable = 0.0
    
    for real_key, irs_key in expense_categories.items():
        # Safe access to real expenses
        real_amount = 0
        if isinstance(real_expenses, dict):
            real_amount = float(real_expenses.get(real_key, 0) or 0)
        
        # Safe access to IRS data
        irs_amount = 0
        if isinstance(irs_data, dict):
            irs_amount = float(irs_data.get(irs_key, 0) or 0)
        
        allowable_amount = max(real_amount, irs_amount)
        total_allowable += allowable_amount
        logging.info(f"📊 {real_key}: Real=${real_amount:.2f}, IRS=${irs_amount:.2f}, Allowable=${allowable_amount:.2f}")
    
    # Add other IRS Standards categories that might not be in real expenses
    additional_irs_categories = {
        "Housekeeping": "housekeeping",
        "PublicTrans": "public_transportation",
        "HealthOutOfPocket": "health_out_of_pocket"
    }
    
    for irs_key, category_name in additional_irs_categories.items():
        irs_amount = 0
        if isinstance(irs_data, dict):
            irs_amount = float(irs_data.get(irs_key, 0) or 0)
        if irs_amount > 0:
            total_allowable += irs_amount
            logging.info(f"📊 {category_name}: IRS=${irs_amount:.2f}")
    
    return total_allowable

def create_expense_breakdown(real_expenses, irs_standards, total_allowable: float) -> dict:
    # Defensive conversion - ensure we're working with dictionaries
    if hasattr(real_expenses, 'dict'):
        real_expenses = real_expenses.dict()
    elif not isinstance(real_expenses, dict):
        real_expenses = {}
    
    if hasattr(irs_standards, 'dict'):
        irs_standards = irs_standards.dict()
    elif not isinstance(irs_standards, dict):
        irs_standards = {}
    
    # Safely extract IRS data
    irs_data = {}
    if hasattr(irs_standards, 'Result') and isinstance(irs_standards.Result, dict):
        irs_data = irs_standards.Result
    elif hasattr(irs_standards, 'data') and isinstance(irs_standards.data, dict):
        irs_data = irs_standards.data
    elif isinstance(irs_standards, dict):
        irs_data = irs_standards.get("data", {})
    
    # Calculate totals safely
    total_real_expenses = 0
    if isinstance(real_expenses, dict):
        total_real_expenses = sum(float(real_expenses.get(k, 0) or 0) for k in ["housing", "housing_utilities", "auto_operating", "food", "personal_care", "apparel", "other1", "other2"])
    
    total_irs_standards = 0
    if isinstance(irs_data, dict):
        total_irs_standards = sum(float(irs_data.get(k, 0) or 0) for k in ["Housing", "OperatingCostCar", "Food", "PersonalCare", "Apparel", "Misc", "Housekeeping", "PublicTrans", "HealthOutOfPocket"])
    
    breakdown = {
        "category_comparisons": {},
        "total_real_expenses": total_real_expenses,
        "total_irs_standards": total_irs_standards,
        "total_allowable": total_allowable
    }
    
    # Create category-by-category comparison
    categories = {
        "housing": ("Housing", "housing"),
        "auto_operating": ("OperatingCostCar", "auto_operating"),
        "food": ("Food", "food"),
        "personal_care": ("PersonalCare", "personal_care"),
        "apparel": ("Apparel", "apparel"),
        "misc": ("Misc", "other1")
    }
    
    for category, (irs_key, real_key) in categories.items():
        # Safe access to real expenses
        real_amount = 0
        if isinstance(real_expenses, dict):
            real_amount = float(real_expenses.get(real_key, 0) or 0)
        
        # Safe access to IRS data
        irs_amount = 0
        if isinstance(irs_data, dict):
            irs_amount = float(irs_data.get(irs_key, 0) or 0)
        
        allowable_amount = max(real_amount, irs_amount)
        breakdown["category_comparisons"][category] = {
            "real_expense": real_amount,
            "irs_standard": irs_amount,
            "allowable_amount": allowable_amount,
            "source_used": "real" if real_amount >= irs_amount else "irs"
        }
    
    return breakdown 