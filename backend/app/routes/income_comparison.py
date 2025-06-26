import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs
from app.utils.client_info import extract_client_info_from_logiqs
from datetime import datetime

# Create logger for this module
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/income-comparison/{case_id}", tags=["Analysis"], summary="Client Profile vs Transcript Income Comparison", description="Compare client profile income to WI/AT transcript income for the most recent year.")
def income_comparison(case_id: str):
    """
    Returns a JSON structure comparing client profile income to WI/AT transcript income for the most recent year, including all required fields and calculations.
    """
    logger.info(f"🔍 Received income comparison request for case_id: {case_id}")

    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")

    cookies = get_cookies()

    try:
        # --- 1. Get client profile data from Logiqs ---
        logger.info(f"📋 Extracting client profile data from Logiqs")
        client_info = extract_client_info_from_logiqs(case_id, cookies)
        if not client_info or not client_info.get("success"):
            raise HTTPException(status_code=404, detail="Could not extract client profile info from Logiqs.")

        # Calculate client annual income from monthly data
        client_annual_income = None
        if client_info.get("client_agi"):
            client_annual_income = client_info["client_agi"]
        else:
            # Try to calculate from monthly income if available
            # This would need to be enhanced based on your Logiqs data structure
            pass

        # --- 2. Get WI summary data ---
        logger.info(f"📋 Fetching WI transcript data")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        wi_data = None
        wi_years = []
        wi_total_income = None
        most_recent_year = None
        
        if wi_files:
            wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis=False)
            # Extract years and find most recent
            wi_years = [y for y in wi_data.keys() if y.isdigit()]
            if wi_years:
                wi_years_sorted = sorted(wi_years, reverse=True)
                most_recent_year = wi_years_sorted[0]
                
                # Get WI total income for most recent year
                if most_recent_year in wi_data:
                    year_data = wi_data[most_recent_year]
                    if isinstance(year_data, list) and year_data:
                        # Look for summary data
                        for form in year_data:
                            if isinstance(form, dict) and "Total Income" in form:
                                wi_total_income = form["Total Income"]
                                break
                        # If not found, try to sum up
                        if wi_total_income is None:
                            wi_total_income = sum(form.get("Total Income", 0) for form in year_data if isinstance(form, dict))

        # --- 3. Get AT data ---
        logger.info(f"📋 Fetching AT transcript data")
        at_files = fetch_at_file_grid(case_id, cookies)
        at_data = []
        at_agi = None
        
        if at_files:
            at_data = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis=False)
            # Find AT AGI for the most recent year
            if at_data and most_recent_year:
                for record in at_data:
                    if str(record.get("tax_year")) == str(most_recent_year):
                        at_agi = record.get("adjusted_gross_income")
                        break

        # --- 4. Determine which transcript income to use ---
        transcript_income_used = None
        transcript_source = None
        
        if wi_total_income is not None:
            transcript_income_used = wi_total_income
            transcript_source = "Transcript Total Income (from WI)"
        elif at_agi is not None:
            transcript_income_used = at_agi
            transcript_source = "Transcript AGI (from AT)"
        else:
            transcript_income_used = None
            transcript_source = None

        # --- 5. Calculate percentage difference ---
        percentage_difference = None
        if client_annual_income is not None and transcript_income_used:
            try:
                percentage_difference = ((client_annual_income - transcript_income_used) / transcript_income_used) * 100
            except (ZeroDivisionError, TypeError):
                percentage_difference = None

        # --- 6. Build WI summary list for output ---
        wi_summary = []
        if wi_data:
            for year in sorted(wi_years, reverse=True):
                year_data = wi_data[year]
                if isinstance(year_data, list):
                    for form in year_data:
                        if isinstance(form, dict) and "Total Income" in form:
                            # Create summary entry
                            summary_entry = {
                                "Tax Year": year,
                                "Number of Forms": len(year_data),
                                "SE Income": form.get("SE Income", 0),
                                "SE Withholding": form.get("SE Withholding", 0),
                                "Non-SE Income": form.get("Non-SE Income", 0),
                                "Non-SE Withholding": form.get("Non-SE Withholding", 0),
                                "Other Income": form.get("Other Income", 0),
                                "Other Withholding": form.get("Other Withholding", 0),
                                "Total Income": form.get("Total Income", 0),
                                "Total Withholding": form.get("Total Withholding", 0)
                            }
                            wi_summary.append(summary_entry)
                            break

        # --- 7. Build client_data structure ---
        # For now, return a simplified structure - this can be enhanced based on your needs
        client_data = {
            "client_info": {
                "case_id": int(case_id),
                "full_name": "Client Name",  # Would need to extract from Logiqs
                "first_name": "First",
                "middle_name": "",
                "last_name": "Last",
                "ssn": "XXX-XX-XXXX",
                "ein": "",
                "marital_status": client_info.get("current_filing_status", "Unknown"),
                "business_name": "",
                "business_type": "",
                "business_address": ""
            },
            "contact_info": {
                "primary_phone": "N/A",
                "home_phone": "N/A", 
                "work_phone": "N/A",
                "email": "N/A",
                "address": {
                    "street": "N/A",
                    "apt": "",
                    "city": "N/A",
                    "state": "N/A",
                    "zip": "N/A",
                    "full_address": "N/A"
                },
                "sms_permitted": True,
                "best_time_to_call": ""
            },
            "tax_info": {
                "total_liability": client_info.get("total_tax_debt", 0),
                "years_owed": [],
                "unfiled_years": [],
                "status_id": 0,
                "status_name": "Unknown",
                "tax_type": "PERSONAL"
            },
            "financial_profile": {
                "income": {
                    "taxpayer_net": 0,
                    "taxpayer_gross": 0,
                    "spouse_net": 0,
                    "spouse_gross": 0,
                    "monthly_gross": client_annual_income / 12 if client_annual_income else 0,
                    "monthly_net": client_annual_income / 12 if client_annual_income else 0,
                    "other_sources": {
                        "business": 0,
                        "pension": 0,
                        "rental": 0,
                        "interest": 0,
                        "alimony": 0,
                        "child_support": 0,
                        "distributions": 0
                    }
                },
                "expenses": {
                    "monthly_expenses": {
                        "housekeeping": 0,
                        "apparel": 0,
                        "personal_care": 0,
                        "food_misc": 0,
                        "transportation": 0,
                        "prescription": 0,
                        "copay": 0,
                        "taxes": 0,
                        "other_1": 0,
                        "other_1_desc": "",
                        "other_2": 0,
                        "other_2_desc": "",
                        "other_3": 0,
                        "other_3_desc": ""
                    },
                    "total_allowable": 0
                },
                "assets": {
                    "cash_on_hand": 0,
                    "total_net_realizable": 0,
                    "retirement": 0,
                    "real_estate": {"quick_sale": 0},
                    "vehicles": {
                        "vehicle_1_qs": 0,
                        "vehicle_2_qs": 0,
                        "vehicle_3_qs": 0,
                        "vehicle_4_qs": 0
                    },
                    "investments": 0,
                    "life_insurance": 0,
                    "personal_effects": 0,
                    "other_assets": 0,
                    "business_assets": {
                        "cash": 0,
                        "bank_accounts": 0,
                        "receivables": 0,
                        "properties": 0,
                        "tools": 0,
                        "other": 0
                    }
                },
                "business": {
                    "income": {
                        "gross_receipts": 0,
                        "gross_rental": 0,
                        "interest": 0,
                        "dividends": 0,
                        "cash": 0,
                        "total": 0
                    },
                    "expenses": {
                        "materials": 0,
                        "inventory": 0,
                        "wages": 0,
                        "rent": 0,
                        "supplies": 0,
                        "vehicle_gas": 0,
                        "vehicle_repairs": 0,
                        "insurance": 0,
                        "taxes": 0,
                        "utilities": 0,
                        "total": 0
                    }
                },
                "family": {
                    "household_size": 1,
                    "members_under_65": 1,
                    "members_over_65": 0,
                    "dependents": "",
                    "vehicle_count": 0
                }
            },
            "case_management": {
                "sale_date": "N/A",
                "created_date": "N/A",
                "modified_date": "N/A",
                "days_in_status": 0,
                "source_name": "N/A",
                "team": {
                    "set_officer": "N/A",
                    "case_advocate": "N/A",
                    "tax_pro": "N/A",
                    "tax_preparer": "N/A",
                    "ti_agent": None,
                    "offer_analyst": None,
                    "team_name": "N/A"
                }
            },
            "raw_data": client_info
        }

        # --- 8. Build final result ---
        result = {
            "comparison_info": {
                "most_recent_year": most_recent_year,
                "client_annual_income": client_annual_income,
                "wi_total_income": wi_total_income,
                "at_agi": at_agi,
                "transcript_income_used": transcript_income_used,
                "transcript_source": transcript_source,
                "percentage_difference": percentage_difference
            },
            "client_data": client_data,
            "wi_summary": wi_summary,
            "at_data": at_data
        }

        logger.info(f"✅ Successfully completed income comparison for case_id: {case_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing income comparison for case_id {case_id}: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 