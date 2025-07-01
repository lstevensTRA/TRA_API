import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.routes import auth, health, income_comparison, transcript_routes, analysis_routes, case_management_routes, tax_investigation_routes_new, closing_letters_routes, batch_routes, client_profile, irs_standards_routes, disposable_income_routes, test_routes, pattern_learning_routes, enhanced_analysis_routes

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
        {"name": "Pattern Learning", "description": "ML-enhanced pattern learning and user feedback endpoints."}
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
app.include_router(client_profile.router, prefix="/client_profile", tags=["Client Profile"])
app.include_router(irs_standards_routes.router, prefix="/irs-standards", tags=["IRS Standards"])
app.include_router(disposable_income_routes.router, prefix="/disposable-income", tags=["Disposable Income"])
app.include_router(test_routes.router, prefix="/test", tags=["Test"])
app.include_router(pattern_learning_routes.router, prefix="/pattern-learning", tags=["Pattern Learning"])
app.include_router(enhanced_analysis_routes.router, prefix="/analysis", tags=["Analysis"])

@app.get("/")
async def root():
    return {"message": "TRA API Backend is running", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

logger.info("🚀 FastAPI server initialized with logging enabled")
