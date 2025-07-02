import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routes import auth, health, income_comparison, transcript_routes, analysis_routes, case_management_routes, tax_investigation_routes_new, closing_letters_routes, batch_routes, client_profile, irs_standards_routes, disposable_income_routes, test_routes, pattern_learning_routes, enhanced_analysis_routes, case_data_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TRA API Backend",
    description="Tax Resolution Associates API Backend",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and session management endpoints."},
        {"name": "Transcripts", "description": "Endpoints for transcript discovery, download, parsing, and raw data (WI/AT)."},
        {"name": "Analysis", "description": "Comprehensive tax analysis, pricing, and client attribute endpoints."},
        {"name": "Billing", "description": "(Coming soon) Invoice, payment, and billing endpoints."},
        {"name": "SMS Logs", "description": "(Coming soon) SMS log and notification endpoints."},
        {"name": "Info", "description": "API metadata and discovery endpoints."},
        {"name": "Health", "description": "Health check endpoints."},
        {"name": "Case Management", "description": "Endpoints for case management."},
        {"name": "Tax Investigation", "description": "Endpoints for tax investigation."},
        {"name": "Closing Letters", "description": "Endpoints for closing letters."},
        {"name": "Batch Processing", "description": "Endpoints for batch processing."},
        {"name": "Client Profile", "description": "Endpoints for client profile management."},
        {"name": "IRS Standards", "description": "Endpoints for IRS Standards and county data."},
        {"name": "Disposable Income", "description": "Endpoints for disposable income calculations."},
        {"name": "Pattern Learning", "description": "ML-enhanced pattern learning and user feedback endpoints."},

        {"name": "Case Data", "description": "Endpoints for case data management."}
    ]
)

# CORS setup (allow all for dev; restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with clean prefixes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(income_comparison.router, prefix="/income-comparison", tags=["Income Comparison"])
app.include_router(transcript_routes.router, prefix="/transcripts", tags=["Transcripts"])
app.include_router(analysis_routes.router, prefix="/analysis", tags=["Analysis"])
app.include_router(case_management_routes.router, prefix="/case-management", tags=["Case Management"])
app.include_router(tax_investigation_routes_new.router, prefix="/tax-investigation", tags=["Tax Investigation"])
app.include_router(closing_letters_routes.router, prefix="/closing-letters", tags=["Closing Letters"])
app.include_router(batch_routes.router, prefix="/batch", tags=["Batch Processing"])
app.include_router(client_profile.router, prefix="/client-profile", tags=["Client Profile"])
app.include_router(irs_standards_routes.router, prefix="/irs-standards", tags=["IRS Standards"])
app.include_router(disposable_income_routes.router, prefix="/disposable-income", tags=["Disposable Income"])
app.include_router(test_routes.router, prefix="/test", tags=["Test"])
app.include_router(pattern_learning_routes.router, prefix="/pattern-learning", tags=["Pattern Learning"])
app.include_router(enhanced_analysis_routes.router, prefix="/analysis", tags=["Analysis"])

app.include_router(case_data_routes.router, prefix="/case-data", tags=["Case Data"])

@app.get("/")
async def root():
    return {"message": "TRA API Backend is running", "version": "1.0.0"}

@app.post("/predict_wi", tags=["Analysis"])
async def predict_wi(request: Request):
    """
    Predict WI form fields for Label Studio ML backend integration or for a list of case IDs.
    If given {"case_ids": [...]}, will fetch raw text and structured data for each case and run prediction/comparison.
    If given the old Label Studio payload, will behave as before.
    """
    data = await request.json()
    # New: If user sends {"case_ids": [...]}, do all the work for them
    if isinstance(data, dict) and "case_ids" in data:
        case_ids = data["case_ids"]
        # Import batch endpoints
        from app.routes.analysis_routes import batch_wi_structured
        from app.services.wi_service import fetch_wi_file_grid, download_wi_pdf
        from app.utils.pdf_utils import extract_text_from_pdf
        from app.utils.cookies import get_cookies
        
        # Fetch raw text and structured data
        raw_texts = {}
        cookies = get_cookies()
        
        for case_id in case_ids:
            try:
                wi_files = fetch_wi_file_grid(case_id, cookies)
                if not wi_files:
                    raw_texts[case_id] = ""
                    continue
                
                all_text = []
                for wi_file in wi_files:
                    try:
                        case_doc_id = wi_file.get("CaseDocumentID")
                        if not case_doc_id:
                            continue
                        
                        pdf_bytes = download_wi_pdf(case_doc_id, case_id, cookies)
                        if not pdf_bytes:
                            continue
                        
                        text = extract_text_from_pdf(pdf_bytes)
                        if text:
                            all_text.append(text)
                    except Exception as e:
                        logger.error(f"Error processing WI file for case {case_id}: {str(e)}")
                        continue
                
                raw_texts[case_id] = "\n".join(all_text)
            except Exception as e:
                logger.error(f"Error getting raw text for case {case_id}: {str(e)}")
                raw_texts[case_id] = ""
        
        structured = batch_wi_structured(case_ids)
        results = {}
        for case_id in case_ids:
            raw_text = raw_texts.get(case_id, "")
            structured_data = structured.get(case_id, {})
            # Use your extraction logic (reuse old code)
            if not raw_text:
                results[case_id] = {"error": "No raw text found for this case."}
                continue
            try:
                # Simple field extraction without training data
                extraction_results = []
                # Basic regex extraction for common fields
                import re
                for field_name, pattern in [
                    ("Wages", r'Wages[\s,]*tips[\s,]*and[\s,]*other[\s,]*compensation[:\s]*\$?([\d,.]+)'),
                    ("Federal Withholding", r'Federal[\s,]*income[\s,]*tax[\s,]*withheld[:\s]*\$?([\d,.]+)'),
                    ("Non-Employee Compensation", r'Non[- ]?Employee[- ]?Compensation[:\s]*\$?([\d,.]+)')
                ]:
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        extraction_results.append({
                            "field": field_name,
                            "value": match.group(1),
                            "confidence": 0.8
                        })
                
                results[case_id] = {
                    "extraction_results": extraction_results,
                    "structured": structured_data
                }
            except Exception as e:
                results[case_id] = {"error": str(e)}
        return results
    # Old behavior: Label Studio ML backend
    task = data[0] if isinstance(data, list) else data
    text = task.get('data', {}).get('raw_text', '')
    if not text:
        raise HTTPException(status_code=400, detail="No raw_text provided in task data.")
    
    # Simple field extraction without training data
    import re
    ls_results = []
    for field_name, pattern in [
        ("Wages", r'Wages[\s,]*tips[\s,]*and[\s,]*other[\s,]*compensation[:\s]*\$?([\d,.]+)'),
        ("Federal Withholding", r'Federal[\s,]*income[\s,]*tax[\s,]*withheld[:\s]*\$?([\d,.]+)'),
        ("Non-Employee Compensation", r'Non[- ]?Employee[- ]?Compensation[:\s]*\$?([\d,.]+)')
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1)
            start = text.find(value_str)
            if start != -1:
                end = start + len(value_str)
                ls_results.append({
                    "from_name": "field",
                    "to_name": "raw_text",
                    "type": "labels",
                    "value": {
                        "start": start,
                        "end": end,
                        "labels": [field_name]
                    }
                })
    
    return [{"result": ls_results}]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

logger.info("🚀 FastAPI server initialized with logging enabled")
