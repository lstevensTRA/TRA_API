import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import Optional, Dict, Any, List
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, parse_wi_pdfs, download_wi_pdf, fetch_ti_file_grid
from app.services.at_service import fetch_at_file_grid, parse_at_pdfs, download_at_pdf
from app.utils.tps_parser import TPSParser
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.wi_patterns import form_patterns
from app.utils.at_codes import at_codes
import re
from datetime import datetime
import os
import io
import httpx
import json
import time
from app.models.response_models import WITranscriptResponse, ATTranscriptResponse

# Create logger for this module
logger = logging.getLogger(__name__)

# Logiqs API URLs
LOGIQS_GRID_URL = "https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
LOGIQS_DOWNLOAD_URL = "https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"

router = APIRouter()

# Placeholder for transcript routes
@router.get("/transcript-test/{case_id}", tags=["Transcripts"])
def test_transcript_endpoint(case_id: str):
    """
    Test endpoint for transcript routes.
    """
    return {"message": "Transcript routes module loaded", "case_id": case_id}

@router.get("/raw/wi/{case_id}", tags=["Transcripts"])
def get_raw_wi_data(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis")
):
    """
    Get raw parsed WI data without summary calculations.
    Returns the same data as /wi/{case_id} but without the summary section.
    """
    logger.info(f"🔍 Received raw WI data request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch and parse WI files
        wi_files = fetch_wi_file_grid(case_id, cookies)
        if not wi_files:
            raise HTTPException(status_code=404, detail="404: No WI files found for this case.")
        
        # Parse WI PDFs
        wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status)
        
        # Remove summary if present (keep only raw data)
        if 'summary' in wi_data:
            del wi_data['summary']
        
        logger.info(f"✅ Successfully returned raw WI data for case_id: {case_id}")
        return wi_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting raw WI data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/raw/at/{case_id}", tags=["Transcripts"])
def get_raw_at_data(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis")
):
    """
    Get raw parsed AT data without summary calculations.
    Returns the same data as /at/{case_id} but without any summary sections.
    """
    logger.info(f"🔍 Received raw AT data request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch and parse AT files
        at_files = fetch_at_file_grid(case_id, cookies)
        if not at_files:
            raise HTTPException(status_code=404, detail="404: No AT files found for this case.")
        
        # Parse AT PDFs
        at_result = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis, filing_status)
        
        # Handle different return formats
        if include_tps_analysis and isinstance(at_result, dict):
            # Return only the raw AT data, not the analysis wrapper
            return at_result['at_data']
        else:
            return at_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting raw AT data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Individual File Download Endpoints ---

@router.get("/download/wi/{case_id}/{case_document_id}", tags=["Transcripts"])
def download_wi_file(case_id: str, case_document_id: str):
    """
    Download a specific WI PDF file by its CaseDocumentID.
    Returns the PDF file as a binary response.
    """
    logger.info(f"📥 Downloading WI file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Download the PDF
        pdf_bytes = download_wi_pdf(case_document_id, case_id, cookies)
        
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file not found or empty")
        
        logger.info(f"✅ Successfully downloaded WI file. Size: {len(pdf_bytes)} bytes")
        
        # Return PDF as binary response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=WI_{case_id}_{case_document_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error downloading WI file for case_id {case_id}, case_document_id {case_document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/download/at/{case_id}/{case_document_id}", tags=["Transcripts"])
def download_at_file(case_id: str, case_document_id: str):
    """
    Download a specific AT PDF file by its CaseDocumentID.
    Returns the PDF file as a binary response.
    """
    logger.info(f"📥 Downloading AT file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Download the PDF
        pdf_bytes = download_at_pdf(case_document_id, case_id, cookies)
        
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file not found or empty")
        
        logger.info(f"✅ Successfully downloaded AT file. Size: {len(pdf_bytes)} bytes")
        
        # Return PDF as binary response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=AT_{case_id}_{case_document_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error downloading AT file for case_id {case_id}, case_document_id {case_document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Individual File Parsing Endpoints ---

def parse_single_wi_file(case_id: str, case_document_id: str, filename: str, cookies: dict):
    """
    Parse a single WI PDF file and return structured data.
    """
    logger.info(f"🔍 Parsing single WI file: {filename}")
    
    try:
        # Download the PDF
        pdf_bytes = download_wi_pdf(case_document_id, case_id, cookies)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file not found or empty")
        
        # Extract text from PDF
        text_content = extract_text_from_pdf(pdf_bytes)
        if not text_content:
            raise HTTPException(status_code=500, detail="Could not extract text from PDF.")
        
        # Parse the text using TPSParser
        parser = TPSParser()
        parsed_data = parser.parse_wi_text(text_content, filename)
        
        # Add metadata
        parsed_data["metadata"] = {
            "case_id": case_id,
            "case_document_id": case_document_id,
            "filename": filename,
            "parsed_at": datetime.now().isoformat(),
            "file_size_bytes": len(pdf_bytes)
        }
        
        logger.info(f"✅ Successfully parsed WI file: {filename}")
        return parsed_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing WI file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def parse_single_at_file(case_id: str, case_document_id: str, filename: str, cookies: dict):
    """
    Parse a single AT PDF file and return structured data.
    """
    logger.info(f"🔍 Parsing single AT file: {filename}")
    
    try:
        # Download the PDF
        pdf_bytes = download_at_pdf(case_document_id, case_id, cookies)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file not found or empty")
        
        # Extract text from PDF
        text_content = extract_text_from_pdf(pdf_bytes)
        if not text_content:
            raise HTTPException(status_code=500, detail="Could not extract text from PDF.")
        
        # Parse the text using TPSParser
        parser = TPSParser()
        parsed_data = parser.parse_at_text(text_content, filename)
        
        # Add metadata
        parsed_data["metadata"] = {
            "case_id": case_id,
            "case_document_id": case_document_id,
            "filename": filename,
            "parsed_at": datetime.now().isoformat(),
            "file_size_bytes": len(pdf_bytes)
        }
        
        logger.info(f"✅ Successfully parsed AT file: {filename}")
        return parsed_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing AT file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/parse/wi/{case_id}/{case_document_id}", tags=["Transcripts"])
def parse_wi_file(case_id: str, case_document_id: str):
    """
    Parse a specific WI PDF file by its CaseDocumentID.
    Returns structured data extracted from the PDF.
    """
    logger.info(f"🔍 Parsing WI file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get file info from grid
        wi_files = fetch_wi_file_grid(case_id, cookies)
        if not wi_files:
            raise HTTPException(status_code=404, detail="No WI files found for this case.")
        
        # Find the specific file
        target_file = None
        for file_info in wi_files:
            if file_info.get("CaseDocumentID") == case_document_id:
                target_file = file_info
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found with the specified CaseDocumentID.")
        
        # Parse the file
        result = parse_single_wi_file(case_id, case_document_id, target_file["FileName"], cookies)
        
        logger.info(f"✅ Successfully parsed WI file for case_id: {case_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing WI file for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/parse/at/{case_id}/{case_document_id}", tags=["Transcripts"])
def parse_at_file(case_id: str, case_document_id: str):
    """
    Parse a specific AT PDF file by its CaseDocumentID.
    Returns structured data extracted from the PDF.
    """
    logger.info(f"🔍 Parsing AT file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get file info from grid
        at_files = fetch_at_file_grid(case_id, cookies)
        if not at_files:
            raise HTTPException(status_code=404, detail="No AT files found for this case.")
        
        # Find the specific file
        target_file = None
        for file_info in at_files:
            if file_info.get("CaseDocumentID") == case_document_id:
                target_file = file_info
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="File not found with the specified CaseDocumentID.")
        
        # Parse the file
        result = parse_single_at_file(case_id, case_document_id, target_file["FileName"], cookies)
        
        logger.info(f"✅ Successfully parsed AT file for case_id: {case_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing AT file for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Multi-File Transcript Endpoints ---

@router.get("/wi/{case_id}", tags=["Transcripts"], 
           summary="Get WI Transcript Files",
           description="Get list of WI transcript files available for a case.",
           response_model=WITranscriptResponse)
def get_wi_transcript_files(case_id: str):
    """
    Get list of WI transcript files available for a case.
    """
    logger.info(f"🔍 Received WI transcript files request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch WI file grid
        logger.info(f"📋 Fetching WI file grid for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        if not wi_files:
            logger.warning(f"⚠️ No WI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="No WI files found for this case.")
        
        # Process files
        processed_files = []
        for i, wi_file in enumerate(wi_files):
            filename = wi_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            
            processed_files.append({
                "index": i + 1,
                "filename": filename,
                "case_document_id": str(wi_file.get('CaseDocumentID', '')),
                "owner": owner
            })
            
            logger.info(f"   📄 {i+1}. {filename} (Owner: {owner})")
        
        logger.info(f"✅ Successfully retrieved {len(processed_files)} WI transcript files for case_id: {case_id}")
        
        return WITranscriptResponse(
            case_id=case_id,
            transcript_type="WI",
            total_files=len(processed_files),
            files=processed_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting WI transcript files for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/at/{case_id}", tags=["Transcripts"], 
           summary="Get AT Transcript Files",
           description="Get list of AT transcript files available for a case.",
           response_model=ATTranscriptResponse)
def get_at_transcript_files(case_id: str):
    """
    Get list of AT transcript files available for a case.
    """
    logger.info(f"🔍 Received AT transcript files request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch AT file grid
        logger.info(f"📋 Fetching AT file grid for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        if not at_files:
            logger.warning(f"⚠️ No AT files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="No AT files found for this case.")
        
        # Process files
        processed_files = []
        for i, at_file in enumerate(at_files):
            filename = at_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            
            processed_files.append({
                "index": i + 1,
                "filename": filename,
                "case_document_id": str(at_file.get('CaseDocumentID', '')),
                "owner": owner
            })
            
            logger.info(f"   📄 {i+1}. {filename} (Owner: {owner})")
        
        logger.info(f"✅ Successfully retrieved {len(processed_files)} AT transcript files for case_id: {case_id}")
        
        return ATTranscriptResponse(
            case_id=case_id,
            transcript_type="AT",
            total_files=len(processed_files),
            files=processed_files
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting AT transcript files for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/transcripts/{case_id}", tags=["Transcripts"])
def get_all_transcripts(case_id: str):
    """
    Get all WI and AT transcripts for a case.
    Returns both WI and AT transcript data.
    """
    logger.info(f"🔍 Received all transcripts request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get WI transcripts
        wi_result = None
        try:
            wi_result = get_wi_transcript_files(case_id)
        except HTTPException as e:
            if e.status_code == 404:
                logger.info(f"ℹ️ No WI transcripts found for case_id: {case_id}")
            else:
                raise
        
        # Get AT transcripts
        at_result = None
        try:
            at_result = get_at_transcript_files(case_id)
        except HTTPException as e:
            if e.status_code == 404:
                logger.info(f"ℹ️ No AT transcripts found for case_id: {case_id}")
            else:
                raise
        
        # Build response
        result = {
            "case_id": case_id,
            "wi_transcripts": wi_result,
            "at_transcripts": at_result
        }
        
        logger.info(f"✅ Successfully retrieved all transcripts for case_id: {case_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting all transcripts for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 