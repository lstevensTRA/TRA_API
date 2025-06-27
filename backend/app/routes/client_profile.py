from fastapi import APIRouter, HTTPException
from app.models.response_models import ClientProfileResponse
import httpx
import logging
from ..utils.cookies import cookies_exist, get_cookies

router = APIRouter()

LOGIQS_API_KEY = "4917fa0ce4694529a9b97ead1a60c932"
LOGIQS_API_URL = "https://tps.logiqs.com/publicapi/2020-02-22/cases/caseinfo"
LOGIQS_COUNTIES_URL = "https://tps.logiqs.com/API/CaseInterview/GetCounties"

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

async def _get_county_info(state: str, city: str) -> dict:
    """Get county information based on state and city"""
    try:
        # Check if we have authentication cookies
        if not cookies_exist():
            logging.warning("No authentication cookies found, skipping county lookup")
            return {"county_id": None, "county_name": None}
        
        cookies_data = get_cookies()
        cookie_header = _extract_cookie_header(cookies_data)
        user_agent = _get_user_agent(cookies_data)
        
        if not cookie_header:
            logging.warning("No valid cookies found, skipping county lookup")
            return {"county_id": None, "county_name": None}
        
        # Get counties for the state
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": user_agent,
            "Cookie": cookie_header
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                LOGIQS_COUNTIES_URL,
                params={"state": state.upper()},
                headers=headers,
                timeout=30,
                follow_redirects=False
            )
            
            if response.status_code != 200:
                logging.warning(f"Failed to get counties for state {state}: {response.status_code}")
                return {"county_id": None, "county_name": None}
            
            data = response.json()
            if data.get("Error", True):
                logging.warning(f"Logiqs API returned error for counties: {data}")
                return {"county_id": None, "county_name": None}
            
            counties = data.get("Result", [])
            
            # Try to find a matching county (this is a simple lookup - could be enhanced)
            # For now, we'll return the first county as a default
            if counties:
                county = counties[0]  # Default to first county
                return {
                    "county_id": county.get("CountyId"),
                    "county_name": county.get("CountyName")
                }
            
            return {"county_id": None, "county_name": None}
            
    except Exception as e:
        logging.warning(f"Error getting county info: {str(e)}")
        return {"county_id": None, "county_name": None}

@router.get("/{case_id}", response_model=ClientProfileResponse)
async def get_client_profile(case_id: str):
    """
    Get client profile for a case ID.
    This endpoint requires authentication via cookies.
    """
    # Check authentication
    if not cookies_exist():
        logging.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies_data = get_cookies()
    cookie_header = _extract_cookie_header(cookies_data)
    user_agent = _get_user_agent(cookies_data)
    
    if not cookie_header:
        logging.error("❌ No valid cookies found for authentication")
        raise HTTPException(status_code=401, detail="No valid cookies found for authentication.")
    
    return await get_client_profile_internal(case_id, cookie_header, user_agent)

async def get_client_profile_internal(case_id: str, cookie_header: str, user_agent: str):
    """
    Internal function to get client profile data.
    This can be called by other routes that already have authentication.
    """
    params = {
        "apikey": LOGIQS_API_KEY,
        "CaseID": case_id
    }
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(LOGIQS_API_URL, params=params, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Case not found")
        data = resp.json()
    
    logging.info(f"RAW LOGIQS RESPONSE for case_id {case_id}: {data}")

    raw = data.get("data", {})
    misc = raw.get("MiscXML", {})

    # Income details
    income_fields = [
        "ClientDetailNetIncom", "ClientDetailFrequentlyPaid", "Income_Pension", "Income_PensionSpouse",
        "Income_Pension_WithoutSocialSecurity", "Income_PensionSpouse_WithoutSocialSecurity", "Income_Interest",
        "Income_Business", "Income_RentalGross", "Income_RentalExpenses", "Income_Rental", "Income_Distributions",
        "Income_ChildSupport", "Income_Alimony", "Income_Other", "Income_Personal_Net", "ClientDetailGrossIncom"
    ]
    income_details = {k: misc.get(k) for k in income_fields if k in misc}

    # Asset details
    asset_fields = [
        "EE_Asset_BankAccounts", "EE_Asset_Investments", "EE_Asset_LInvestments", "EE_Asset_LifeInsurance",
        "EE_Asset_LLifeInsurance", "EE_Asset_Retirement", "EE_Asset_LRetirement", "EE_Asset_RealEstate",
        "EE_Asset_LRealEstate", "EE_Asset_Vehicle1", "EE_Asset_LVehicle1", "EE_Asset_Vehicle2", "EE_Asset_LVehicle2",
        "EE_Asset_Vehicle3", "EE_Asset_LVehicle3", "EE_Asset_Vehicle4", "EE_Asset_LVehicle4", "EE_Asset_Effects",
        "EE_Asset_LEffects", "EE_Asset_Other", "EE_Asset_LOther", "EE_Asset_chkVehicle_1", "EE_Asset_chkVehicle_2",
        "EE_Asset_chkVehicle_3", "EE_Asset_chkVehicle_4"
    ]
    asset_details = {k: misc.get(k) for k in asset_fields if k in misc}

    # Assets section
    assets = {
        "real_estate": misc.get("EE_Asset_QSRealEstate"),
        "investments": misc.get("EE_Asset_QSInvestments"),
        "life_insurance": misc.get("EE_Asset_QSLifeInsurance"),
        "personal_property": misc.get("EE_Asset_QSEffects"),
        "retirement": misc.get("EE_Asset_QSRetirement"),
        "vehicles": {
            "vehicle1": misc.get("EE_Asset_QSVehicle1"),
            "vehicle2": misc.get("EE_Asset_QSVehicle2"),
            "vehicle3": misc.get("EE_Asset_QSVehicle3"),
            "vehicle4": misc.get("EE_Asset_QSVehicle4"),
            "count": _to_int(misc.get("VehicleCount")),
        },
        "business_receivables": misc.get("EE_Asset_BizQSReceivables"),
        "business_properties": misc.get("EE_Asset_BizQSProperties"),
        "business_tools": misc.get("EE_Asset_BizQSTools"),
        "business_other": misc.get("EE_Asset_BizQSOther"),
        "other": misc.get("EE_Asset_QSOther"),
    }

    # Expanded expenses section
    monthly_net = _to_float(misc.get("Income_Net"))
    expenses = {
        "housing": _to_float(misc.get("Expense_HouseKeeping")),
        "housing_utilities": _to_float(misc.get("Expense_HousingUtilities")),
        "auto_operating": _to_float(misc.get("Expense_AutoOperating")),
        "food": _to_float(misc.get("Expense_FoodMisc")),
        "personal_care": _to_float(misc.get("Expense_PersonalCare")),
        "apparel": _to_float(misc.get("Expense_Apparel")),
        "other1": _to_float(misc.get("Expense_Other1")),
        "other1_label": misc.get("Expense_Other1S"),
        "other2": _to_float(misc.get("Expense_Other2")),
        "other2_label": misc.get("Expense_Other2S"),
        "total": _to_float(misc.get("ExpenseTotalAllowable")),
    }

    # Get county information
    state = raw.get("State")
    city = raw.get("City")
    county_info = await _get_county_info(state, city) if state else {"county_id": None, "county_name": None}

    # Personal
    personal = {
        "marital_status": raw.get("MartialStatus"),
        "household_size": _to_int(misc.get("ClientDetailHousehold")),
        "members_under_65": _to_int(misc.get("FamilyMembersUnder65")),
        "members_over_65": _to_int(misc.get("FamilyMembersOver65")),
        "county_id": county_info.get("county_id"),
        "county_name": county_info.get("county_name"),
    }
    # Contact
    contact = {
        "primary_phone": raw.get("CellPhone"),
        "home_phone": raw.get("HomePhone"),
        "work_phone": raw.get("WorkPhone"),
        "email": raw.get("Email"),
        "sms_permitted": raw.get("SMSPermitted"),
        "best_time_to_call": raw.get("BestTimeToCall"),
    }
    # Address
    address = {
        "street": raw.get("Address"),
        "city": raw.get("City"),
        "state": raw.get("State"),
        "zip": raw.get("Zip"),
    }
    # Financial Profile
    financial_profile = {
        "taxpayer_income": _to_float(misc.get("IncomeGrossM")),
        "spouse_income": _to_float(misc.get("IncomeSpouseM")),
        "monthly_net": monthly_net,
        "yearly_income": monthly_net * 12 if monthly_net is not None else None,
        "expenses": expenses
    }
    # Tax Info
    tax_info = {
        "total_liability": _to_float(raw.get("TaxLiability")),
        "years_owed": [y.strip() for y in (raw.get("OweTaxestoFederal") or "").split(",") if y.strip()],
    }
    # Case Management
    case_management = {
        "case_id": str(raw.get("CaseID")) if raw.get("CaseID") is not None else None,
        "status": raw.get("StatusName"),
        "sale_date": raw.get("SaleDate"),
        "created_date": raw.get("CreatedDate"),
        "modified_date": raw.get("ModifiedDate"),
        "days_in_status": _to_int(raw.get("DaysInStatus")),
        "team": {
            "set_officer": raw.get("SetOfficer"),
            "case_advocate": raw.get("CaseAdvocate"),
            "tax_pro": raw.get("TaxPro"),
            "tax_preparer": raw.get("TaxPreparer"),
            "ti_agent": raw.get("TIAgent"),
            "offer_analyst": raw.get("OfferAnalyst"),
            "team_name": raw.get("TeamName"),
        },
        "source_name": raw.get("SourceName"),
    }

    return ClientProfileResponse(
        personal=personal,
        contact=contact,
        address=address,
        financial_profile=financial_profile,
        tax_info=tax_info,
        case_management=case_management,
        assets=assets,
        income_details=income_details,
        asset_details=asset_details
    )

def _to_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def _to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None 