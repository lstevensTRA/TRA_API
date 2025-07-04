from fastapi import APIRouter, HTTPException, Query
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs
from app.utils.cookies import cookies_exist, get_cookies
from app.utils.tps_parser import TPSParser
from app.utils.wi_patterns import form_patterns
import logging
from collections import OrderedDict

# Create the debug router
debug_router = APIRouter(prefix="/analysis/wi/debug")

def build_troubleshoot(wi_data):
    troubleshoot = {}
    for year, forms in wi_data["years_data"].items():
        lines = []
        # Per-form lines
        for form in forms:
            form_type = form.get("Form", "")
            pattern = form_patterns.get(form_type, {})
            category = pattern.get("category", "Other")
            bucket = (
                "se_income" if category == "SE"
                else "non_se_income" if category == "Non-SE"
                else "other_income"
            )
            # Only nonzero fields used in calc
            fields_used = {k: v for k, v in form.get("Fields", {}).items() if isinstance(v, (int, float)) and v != 0}
            lines.append({
                "Form": form_type,
                "UniqueID": form.get("UniqueID", ""),
                "Entity": form.get("EntityName", ""),
                "Category": category,
                "FieldsUsed": fields_used,
                "IncomeContrib": form.get("Income", 0.0),
                "WithholdingContrib": form.get("Withholding", 0.0),
                "Bucket": bucket,
            })
        # Bucket totals
        bucket_totals = {"se_income": 0.0, "non_se_income": 0.0, "other_income": 0.0}
        for line in lines:
            bucket_totals[line["Bucket"]] += line["IncomeContrib"]
        # JSON totals from summary
        json_totals = {
            "se_income": wi_data["summary"]["by_year"][year]["se_income"],
            "non_se_income": wi_data["summary"]["by_year"][year]["non_se_income"],
            "other_income": wi_data["summary"]["by_year"][year]["other_income"],
        }
        match = all(abs(bucket_totals[k] - json_totals[k]) < 1e-6 for k in bucket_totals)
        lines.append({
            "BucketTotals": bucket_totals,
            "JSONTotals": json_totals,
            "Match": match,
        })
        troubleshoot[year] = lines
    return troubleshoot

@debug_router.get("/{case_id}", tags=["Analysis"], summary="WI Debug Analysis")
def wi_debug_analysis(
    case_id: str,
    include_tps_analysis: bool = Query(False, description="Include TP/S analysis in response"),
    filing_status: str = Query(None, description="Client filing status for TP/S analysis (e.g., 'Married Filing Jointly')")
):
    logger = logging.getLogger("app.routes.analysis_wi_debug")
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    cookies = get_cookies()
    wi_files = fetch_wi_file_grid(case_id, cookies)
    if not wi_files:
        raise HTTPException(status_code=404, detail="404: No WI files found for this case.")
    wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status, return_scoped_structure=False)
    troubleshoot = build_troubleshoot(wi_data)
    
    # Build the new per-year structure
    year_map = OrderedDict()
    years = sorted(wi_data["summary"]["years_analyzed"], reverse=True)
    
    for year in years:
        # Find the BucketTotals row
        tb_row = next(r for r in troubleshoot[year] if "BucketTotals" in r)
        
        year_map[year] = {
            "summary": {
                **tb_row["BucketTotals"],
                "match": tb_row["Match"],
                "number_of_forms": len(wi_data["years_data"][year])
            },
            "forms": wi_data["years_data"][year],
            "troubleshoot": [r for r in troubleshoot[year] if "Form" in r]
        }
    
    return {
        **year_map,
        "overall_totals": wi_data["summary"]["overall_totals"]
    } 