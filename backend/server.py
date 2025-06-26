import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import health, auth, data, income_comparison, transcript_routes

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
    title="Case Management API Backend",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Authentication and session management endpoints."},
        {"name": "Transcripts", "description": "Endpoints for transcript discovery, download, parsing, and raw data (WI/AT)."},
        {"name": "Analysis", "description": "Comprehensive tax analysis, pricing, and client attribute endpoints."},
        {"name": "Billing", "description": "(Coming soon) Invoice, payment, and billing endpoints."},
        {"name": "SMS Logs", "description": "(Coming soon) SMS log and notification endpoints."},
        {"name": "Info", "description": "API metadata and discovery endpoints."},
        {"name": "Health", "description": "Health check endpoints."}
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

# Include routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(data.router)
app.include_router(income_comparison.router)
app.include_router(transcript_routes.router)

logger.info("🚀 FastAPI server initialized with logging enabled")
