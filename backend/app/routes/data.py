import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
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
import csv

# Create logger for this module
logger = logging.getLogger(__name__)

# Logiqs API URLs
LOGIQS_GRID_URL = "https://tps.logiqs.com/API/Document/gridBind?caseid={case_id}&type=grid"
LOGIQS_DOWNLOAD_URL = "https://tps.logiqs.com/API/Document/DownloadFile?CaseDocumentID={case_doc_id}&caseId={case_id}"

router = APIRouter()

# Response Models with Examples for FastAPI Docs
class ResolutionSummary(BaseModel):
    resolution_type: Optional[str] = Field(None, example="IA", description="Type of resolution (IA, PPIA, CNC, OIC, FA, etc.)")
    resolution_amount: Optional[float] = Field(None, example=450.0, description="Monthly payment amount")
    payment_terms: Optional[str] = Field(None, example="Due on 28th of each month", description="Payment schedule")
    user_fee: Optional[float] = Field(None, example=178.0, description="User fee amount")
    start_date: Optional[str] = Field(None, example="7/28/2025", description="Agreement start date")
    tax_years: List[str] = Field(default_factory=list, example=["2019", "2020", "2021", "2022", "2023"], description="Tax years covered")
    lien_status: Optional[str] = Field(None, example="No liens filed", description="Lien status")
    account_balance: Optional[float] = Field(None, example=35369.0, description="Total account balance")
    payment_method: Optional[str] = Field(None, example="Manual", description="Payment method")
    services_completed: List[str] = Field(default_factory=list, example=[], description="Services completed")
    additional_terms: List[str] = Field(default_factory=list, example=["1. To avoid default of your Installment Agreement, all future tax returns must be filed on", "2. To prevent future balances, make sure to increase your IRS tax withholdings"], description="Additional terms and conditions")

class CaseResult(BaseModel):
    case_id: int = Field(example=732334, description="Case ID")
    has_closing_letters: bool = Field(example=True, description="Whether case has closing letters")
    error: Optional[str] = Field(None, example=None, description="Error message if processing failed")
    resolution_summary: Optional[ResolutionSummary] = Field(None, example=ResolutionSummary(), description="Parsed resolution details")
    total_files: Optional[int] = Field(None, example=1, description="Number of closing letter files")

class BatchSummary(BaseModel):
    total_cases: int = Field(example=3, description="Total number of cases processed")
    successful_cases: int = Field(example=3, description="Number of successfully processed cases")
    cases_with_closing_letters: int = Field(example=2, description="Number of cases with closing letters")
    success_rate: float = Field(example=100.0, description="Success rate percentage")
    closing_letter_rate: float = Field(example=66.67, description="Percentage of cases with closing letters")
    resolution_type_distribution: Dict[str, int] = Field(example={"IA": 1}, description="Distribution of resolution types")
    average_account_balance: Optional[float] = Field(None, example=30945.97, description="Average account balance")

class CompletedCasesResponse(BaseModel):
    total_completed_cases: int
    case_ids: List[int]

class BatchAnalysisResponse(BaseModel):
    total_completed_cases: int
    processed_cases: int
    start_index: int
    end_index: int
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]

class CSVExportResponse(BaseModel):
    total_completed_cases: int
    processed_cases: int
    start_index: int
    end_index: int
    total_batches: int
    batch_size: int
    csv_data: str
    summary: Dict[str, Any]

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
        logger.error(f"❌ Error downloading WI file: {str(e)}")
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
        logger.error(f"❌ Error downloading AT file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Individual File Parse Endpoints ---

def parse_single_wi_file(case_id: str, case_document_id: str, filename: str, cookies: dict):
    """
    Parse a single WI PDF file and return the extracted data.
    """
    logger.info(f"🔍 Parsing single WI file: {filename}")
    
    try:
        # Download PDF
        pdf_bytes = download_wi_pdf(case_document_id, case_id, cookies)
        if not pdf_bytes:
            raise Exception("No PDF content received")
        
        # Extract text
        text = extract_text_from_pdf(pdf_bytes)
        if not text:
            raise Exception("No text extracted from PDF")
        
        # Extract tax year from filename
        year_match = re.search(r'WI\s+(\d{2})', filename)
        if year_match:
            year_suffix = year_match.group(1)
            if int(year_suffix) <= 50:
                tax_year = f"20{year_suffix}"
            else:
                tax_year = f"19{year_suffix}"
        else:
            year_match = re.search(r"(20\d{2})", filename)
            tax_year = year_match.group(1) if year_match else "Unknown"
        
        # Extract owner from filename
        owner = TPSParser.extract_owner_from_filename(filename)
        
        # Parse forms
        forms_found = []
        for form_name, pattern_info in form_patterns.items():
            matches = list(re.finditer(pattern_info['pattern'], text, re.MULTILINE | re.IGNORECASE))
            
            for match in matches:
                start = match.start()
                end = len(text)
                for next_match in matches[matches.index(match) + 1:]:
                    if next_match.start() > start:
                        end = next_match.start()
                        break
                
                form_text = text[start:end]
                
                # Extract fields
                fields_data = {}
                for field_name, regex in pattern_info['fields'].items():
                    if regex:
                        field_match = re.search(regex, form_text, re.IGNORECASE)
                        if field_match:
                            try:
                                value_str = field_match.group(1).replace(',', '')
                                if field_name in ['Direct Sales Indicator', 'FATCA Filing Requirement', 'Second Notice Indicator']:
                                    fields_data[field_name] = value_str
                                else:
                                    value = float(value_str)
                                    fields_data[field_name] = value
                            except (ValueError, AttributeError):
                                fields_data[field_name] = 0
                
                # Extract identifiers
                unique_id = None
                label = None
                
                if 'identifiers' in pattern_info:
                    identifiers = pattern_info['identifiers']
                    if 'EIN' in identifiers:
                        ein_match = re.search(identifiers['EIN'], form_text, re.IGNORECASE)
                        if ein_match:
                            unique_id = ein_match.group(1)
                    elif 'FIN' in identifiers:
                        fin_match = re.search(identifiers['FIN'], form_text, re.IGNORECASE)
                        if fin_match:
                            unique_id = fin_match.group(1)
                    
                    if 'Employer' in identifiers:
                        label = 'E'
                    elif 'Payer' in identifiers:
                        label = 'P'
                
                # Fallback for UniqueID
                if not unique_id:
                    if form_name == 'W-2':
                        ein_match = re.search(r'Employer Identification Number \(EIN\):\s*([\d\-]+)', form_text, re.IGNORECASE)
                        unique_id = ein_match.group(1) if ein_match else 'UNKNOWN'
                    elif form_name.startswith('1099'):
                        fin_match = re.search(r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)", form_text, re.IGNORECASE)
                        unique_id = fin_match.group(1) if fin_match else 'UNKNOWN'
                
                # Fallback for Label
                if not label:
                    if form_name == 'W-2':
                        label = 'E'
                    elif form_name.startswith('1099'):
                        label = 'P'
                
                # Calculate income and withholding
                calc = pattern_info.get('calculation', {})
                income = None
                withholding = None
                
                try:
                    if 'Income' in calc and callable(calc['Income']):
                        income = calc['Income'](fields_data)
                    if 'Withholding' in calc and callable(calc['Withholding']):
                        withholding = calc['Withholding'](fields_data)
                except Exception:
                    income = 0
                    withholding = 0
                
                if withholding is None:
                    withholding = 0
                
                # Build form dict
                form_dict = {
                    'Form': form_name,
                    'UniqueID': unique_id,
                    'Label': label,
                    'Income': income,
                    'Withholding': withholding,
                    'Category': pattern_info.get('category'),
                    'Fields': fields_data,
                    'Owner': owner,
                    'SourceFile': filename
                }
                
                forms_found.append(form_dict)
        
        return {
            'case_id': case_id,
            'case_document_id': case_document_id,
            'filename': filename,
            'tax_year': tax_year,
            'owner': owner,
            'forms_found': len(forms_found),
            'forms': forms_found
        }
        
    except Exception as e:
        logger.error(f"❌ Error parsing WI file {filename}: {str(e)}")
        raise

def parse_single_at_file(case_id: str, case_document_id: str, filename: str, cookies: dict):
    """
    Parse a single AT PDF file and return the extracted data.
    """
    logger.info(f"🔍 Parsing single AT file: {filename}")
    
    try:
        # Download PDF
        pdf_bytes = download_at_pdf(case_document_id, case_id, cookies)
        if not pdf_bytes:
            raise Exception("No PDF content received")
        
        # Extract text
        text = extract_text_from_pdf(pdf_bytes)
        if not text:
            raise Exception("No text extracted from PDF")
        
        # Extract owner from filename
        owner = TPSParser.extract_owner_from_filename(filename)
        
        # Use the existing AT parsing logic
        from app.services.at_service import extract_at_data
        
        data = extract_at_data(text)
        data['owner'] = owner
        data['source_file'] = filename
        data['case_document_id'] = case_document_id
        
        return {
            'case_id': case_id,
            'case_document_id': case_document_id,
            'filename': filename,
            'owner': owner,
            'parsed_data': data
        }
        
    except Exception as e:
        logger.error(f"❌ Error parsing AT file {filename}: {str(e)}")
        raise

@router.get("/parse/wi/{case_id}/{case_document_id}", tags=["Transcripts"])
def parse_wi_file(case_id: str, case_document_id: str):
    """
    Parse a specific WI PDF file by its CaseDocumentID.
    Returns the parsed form data from that single file.
    """
    logger.info(f"🔍 Parsing WI file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # First, get the filename from the file grid
        wi_files = fetch_wi_file_grid(case_id, cookies)
        target_file = None
        
        for wi_file in wi_files:
            if wi_file.get('CaseDocumentID') == case_document_id:
                target_file = wi_file
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="WI file not found with specified CaseDocumentID")
        
        filename = target_file.get('FileName', 'Unknown')
        
        # Parse the single file
        result = parse_single_wi_file(case_id, case_document_id, filename, cookies)
        
        logger.info(f"✅ Successfully parsed WI file. Found {result['forms_found']} forms")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing WI file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/parse/at/{case_id}/{case_document_id}", tags=["Transcripts"])
def parse_at_file(case_id: str, case_document_id: str):
    """
    Parse a specific AT PDF file by its CaseDocumentID.
    Returns the parsed data from that single file.
    """
    logger.info(f"🔍 Parsing AT file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # First, get the filename from the file grid
        at_files = fetch_at_file_grid(case_id, cookies)
        target_file = None
        
        for at_file in at_files:
            if at_file.get('CaseDocumentID') == case_document_id:
                target_file = at_file
                break
        
        if not target_file:
            raise HTTPException(status_code=404, detail="AT file not found with specified CaseDocumentID")
        
        filename = target_file.get('FileName', 'Unknown')
        
        # Parse the single file
        result = parse_single_at_file(case_id, case_document_id, filename, cookies)
        
        logger.info(f"✅ Successfully parsed AT file")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing AT file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Transcript Discovery Endpoints ---

@router.get("/transcripts/wi/{case_id}", tags=["Transcripts"])
def get_wi_transcripts(case_id: str):
    """
    Get list of WI transcript files available for a case.
    Returns metadata about available WI files without parsing them.
    """
    logger.info(f"🔍 Received WI transcripts request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch WI file grid
        logger.info(f"📋 Fetching WI file grid for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        if not wi_files:
            logger.warning(f"⚠️ No WI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No WI files found for this case.")
        
        logger.info(f"✅ Found {len(wi_files)} WI files for case_id: {case_id}")
        
        # Enhance response with additional metadata
        response = {
            "case_id": case_id,
            "transcript_type": "WI",
            "total_files": len(wi_files),
            "files": []
        }
        
        for i, wi_file in enumerate(wi_files):
            filename = wi_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            file_info = {
                "index": i + 1,
                "filename": filename,
                "case_document_id": wi_file.get('CaseDocumentID', 'Unknown'),
                "owner": owner
            }
            response["files"].append(file_info)
            logger.info(f"   📄 {i+1}. {file_info['filename']} (ID: {file_info['case_document_id']}, Owner: {owner})")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching WI transcripts for case_id {case_id}: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/transcripts/at/{case_id}", tags=["Transcripts"])
def get_at_transcripts(case_id: str):
    """
    Get list of AT transcript files available for a case.
    Returns metadata about available AT files without parsing them.
    """
    logger.info(f"🔍 Received AT transcripts request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch AT file grid
        logger.info(f"📋 Fetching AT file grid for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        if not at_files:
            logger.warning(f"⚠️ No AT files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No AT files found for this case.")
        
        logger.info(f"✅ Found {len(at_files)} AT files for case_id: {case_id}")
        
        # Enhance response with additional metadata
        response = {
            "case_id": case_id,
            "transcript_type": "AT",
            "total_files": len(at_files),
            "files": []
        }
        
        for i, at_file in enumerate(at_files):
            filename = at_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            file_info = {
                "index": i + 1,
                "filename": filename,
                "case_document_id": at_file.get('CaseDocumentID', 'Unknown'),
                "owner": owner
            }
            response["files"].append(file_info)
            logger.info(f"   📄 {i+1}. {file_info['filename']} (ID: {file_info['case_document_id']}, Owner: {owner})")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching AT transcripts for case_id {case_id}: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/transcripts/{case_id}", tags=["Transcripts"])
def get_all_transcripts(case_id: str):
    """
    Get list of all transcript files (WI + AT) available for a case.
    Returns metadata about all available transcript files without parsing them.
    """
    logger.info(f"🔍 Received all transcripts request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch both WI and AT file grids
        logger.info(f"📋 Fetching WI file grid for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        logger.info(f"📋 Fetching AT file grid for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        # Combine results
        all_files = []
        
        # Add WI files
        for i, wi_file in enumerate(wi_files):
            filename = wi_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            file_info = {
                "index": i + 1,
                "filename": filename,
                "case_document_id": wi_file.get('CaseDocumentID', 'Unknown'),
                "transcript_type": "WI",
                "owner": owner
            }
            all_files.append(file_info)
        
        # Add AT files
        for i, at_file in enumerate(at_files):
            filename = at_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            file_info = {
                "index": len(all_files) + i + 1,
                "filename": filename,
                "case_document_id": at_file.get('CaseDocumentID', 'Unknown'),
                "transcript_type": "AT",
                "owner": owner
            }
            all_files.append(file_info)
        
        if not all_files:
            logger.warning(f"⚠️ No transcript files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No transcript files found for this case.")
        
        logger.info(f"✅ Found {len(all_files)} total transcript files for case_id: {case_id}")
        logger.info(f"   📄 WI files: {len(wi_files)}")
        logger.info(f"   📄 AT files: {len(at_files)}")
        
        # Create response
        response = {
            "case_id": case_id,
            "total_files": len(all_files),
            "wi_files": len(wi_files),
            "at_files": len(at_files),
            "files": all_files
        }
        
        for file_info in all_files:
            logger.info(f"   📄 {file_info['index']}. {file_info['filename']} ({file_info['transcript_type']}) (ID: {file_info['case_document_id']}, Owner: {file_info['owner']})")
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching all transcripts for case_id {case_id}: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Existing Processing Endpoints ---

@router.get("/wi/{case_id}", tags=["Analysis"], summary="Wage & Income Multi-Year Analysis", description="Get parsed and aggregated Wage & Income (WI) transcript data for all available years in the case.")
def get_wi_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis (e.g., 'Married Filing Jointly')")
):
    """
    Get parsed and aggregated Wage & Income (WI) transcript data for all available years in the case.
    Returns a summary of all WI forms and income by year, with optional TP/S analysis.
    """
    logger.info(f"🔍 Received WI data request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch WI file grid
        logger.info(f"📋 Fetching WI file grid for case_id: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        if not wi_files:
            logger.warning(f"⚠️ No WI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No WI files found for this case.")
        
        logger.info(f"✅ Found {len(wi_files)} WI files for case_id: {case_id}")
        for i, wi_file in enumerate(wi_files):
            filename = wi_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            logger.info(f"   📄 {i+1}. {filename} (ID: {wi_file.get('CaseDocumentID', 'Unknown')}, Owner: {owner})")
        
        # Parse WI PDFs with optional TP/S analysis
        logger.info(f"🔍 Starting PDF parsing for {len(wi_files)} WI files")
        wi_summary = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status)
        
        logger.info(f"✅ Successfully parsed WI data for case_id: {case_id}")
        if 'summary' in wi_summary:
            logger.info(f"📊 Summary: {len(wi_summary) - 1} tax years with data")  # -1 for summary key
            for tax_year, forms in wi_summary.items():
                if tax_year != 'summary' and tax_year != 'tps_analysis':
                    logger.info(f"   📅 {tax_year}: {len(forms)} forms")
        else:
            logger.info(f"📊 Summary: {len(wi_summary)} tax years with data")
            for tax_year, forms in wi_summary.items():
                logger.info(f"   📅 {tax_year}: {len(forms)} forms")
        
        return wi_summary
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing WI data for case_id {case_id}: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/at/{case_id}", tags=["Analysis"], summary="Account Transcript Multi-Year Analysis", description="Get parsed and aggregated Account Transcript (AT) data for all available years in the case.")
def get_at_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis (e.g., 'Married Filing Jointly')")
):
    """
    Get parsed and aggregated Account Transcript (AT) data for all available years in the case.
    Returns a summary of all AT data by year, with optional TP/S analysis.
    """
    logger.info(f"🔍 Received AT data request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    logger.info("✅ Cookies found, proceeding with authentication")
    cookies = get_cookies()
    logger.info(f"🍪 Loaded {len(cookies.get('cookies', [])) if isinstance(cookies, dict) and 'cookies' in cookies else 'unknown'} cookies")
    
    try:
        # Fetch AT file grid
        logger.info(f"📋 Fetching AT file grid for case_id: {case_id}")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        if not at_files:
            logger.warning(f"⚠️ No AT files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No AT files found for this case.")
        
        logger.info(f"✅ Found {len(at_files)} AT files for case_id: {case_id}")
        for i, at_file in enumerate(at_files):
            filename = at_file.get('FileName', 'Unknown')
            owner = TPSParser.extract_owner_from_filename(filename)
            logger.info(f"   📄 {i+1}. {filename} (ID: {at_file.get('CaseDocumentID', 'Unknown')}, Owner: {owner})")
        
        # Parse AT PDFs with optional TP/S analysis
        logger.info(f"🔍 Starting PDF parsing for {len(at_files)} AT files")
        at_result = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis, filing_status)
        
        # Handle different return formats based on TP/S analysis
        if include_tps_analysis and isinstance(at_result, dict):
            at_data = at_result['at_data']
            logger.info(f"✅ Successfully parsed AT data for case_id: {case_id} with TP/S analysis")
            logger.info(f"📊 Summary: {len(at_data)} AT records")
            for at_record in at_data:
                logger.info(f"   📅 {at_record['tax_year']}: {len(at_record['transactions'])} transactions")
            return at_result
        else:
            at_data = at_result
            logger.info(f"✅ Successfully parsed AT data for case_id: {case_id}")
            logger.info(f"📊 Summary: {len(at_data)} AT records")
            for at_record in at_data:
                logger.info(f"   📅 {at_record['tax_year']}: {len(at_record['transactions'])} transactions")
            return at_data
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error processing AT data for case_id {case_id}: {str(e)}")
        logger.error(f"🔍 Error type: {type(e).__name__}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Comprehensive Tax Analysis Endpoint ---

@router.get("/analysis/{case_id}", tags=["Analysis"])
def get_comprehensive_analysis(
    case_id: str,
    include_tps_analysis: Optional[bool] = Query(False, description="Include TP/S analysis in response"),
    filing_status: Optional[str] = Query(None, description="Client filing status for TP/S analysis")
):
    """
    Get comprehensive tax analysis combining WI and AT data.
    Returns advanced analytics including income trends, filing patterns, and recommendations.
    """
    logger.info(f"🔍 Received comprehensive analysis request for case_id: {case_id}")
    logger.info(f"🔍 TP/S analysis requested: {include_tps_analysis}")
    if filing_status:
        logger.info(f"🔍 Filing status provided: {filing_status}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch and parse both WI and AT data
        logger.info(f"📋 Fetching WI data for comprehensive analysis")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        if not wi_files:
            logger.warning(f"⚠️ No WI files found for case_id: {case_id}")
            wi_data = {}
        else:
            wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis, filing_status)
        
        logger.info(f"📋 Fetching AT data for comprehensive analysis")
        at_files = fetch_at_file_grid(case_id, cookies)
        if not at_files:
            logger.warning(f"⚠️ No AT files found for case_id: {case_id}")
            at_data = []
        else:
            at_result = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis, filing_status)
            at_data = at_result['at_data'] if include_tps_analysis and isinstance(at_result, dict) else at_result
        
        # Perform comprehensive analysis
        analysis = perform_comprehensive_analysis(wi_data, at_data, case_id, include_tps_analysis, filing_status)
        
        logger.info(f"✅ Successfully completed comprehensive analysis for case_id: {case_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing comprehensive analysis for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def perform_comprehensive_analysis(wi_data: dict, at_data: list, case_id: str, include_tps_analysis: bool, filing_status: str = None) -> dict:
    """
    Perform comprehensive tax analysis combining WI and AT data.
    """
    logger.info(f"🔍 Performing comprehensive analysis for case_id: {case_id}")
    
    analysis = {
        "case_id": case_id,
        "analysis_date": datetime.now().isoformat(),
        "filing_status": filing_status,
        "data_availability": {},
        "income_analysis": {},
        "filing_patterns": {},
        "financial_health": {},
        "recommendations": [],
        "tax_years": {},
        "summary": {}
    }
    
    # Data Availability Analysis
    analysis["data_availability"] = analyze_data_availability(wi_data, at_data)
    
    # Income Analysis
    analysis["income_analysis"] = analyze_income_trends(wi_data, at_data)
    
    # Filing Patterns
    analysis["filing_patterns"] = analyze_filing_patterns(wi_data, at_data)
    
    # Financial Health
    analysis["financial_health"] = analyze_financial_health(wi_data, at_data)
    
    # Tax Year Breakdown
    analysis["tax_years"] = create_tax_year_breakdown(wi_data, at_data)
    
    # Generate Recommendations
    analysis["recommendations"] = generate_recommendations(wi_data, at_data, analysis)
    
    # Summary Statistics
    analysis["summary"] = create_summary_statistics(wi_data, at_data, analysis)
    
    # Add TP/S analysis if requested
    if include_tps_analysis:
        analysis["tps_analysis"] = perform_tps_analysis(wi_data, at_data, filing_status)
    
    return analysis

def analyze_data_availability(wi_data: dict, at_data: list) -> dict:
    """Analyze what data is available and identify gaps."""
    logger.info("🔍 Analyzing data availability")
    
    # Get available tax years - filter out non-year keys
    wi_years = set()
    if isinstance(wi_data, dict):
        for key in wi_data.keys():
            if key not in ['summary', 'tps_analysis'] and key.isdigit():
                wi_years.add(key)
    
    at_years = {record['tax_year'] for record in at_data} if at_data else set()
    
    all_years = sorted(wi_years.union(at_years), reverse=True)
    
    availability = {
        "total_tax_years": len(all_years),
        "wi_years": sorted(list(wi_years), reverse=True),
        "at_years": sorted(list(at_years), reverse=True),
        "years_with_both": sorted(list(wi_years.intersection(at_years)), reverse=True),
        "years_with_wi_only": sorted(list(wi_years - at_years), reverse=True),
        "years_with_at_only": sorted(list(at_years - wi_years), reverse=True),
        "data_gaps": []
    }
    
    # Identify gaps
    if len(wi_years) > 0 and len(at_years) > 0:
        min_year = min(min(wi_years), min(at_years))
        max_year = max(max(wi_years), max(at_years))
        
        for year in range(int(min_year), int(max_year) + 1):
            year_str = str(year)
            if year_str not in wi_years and year_str not in at_years:
                availability["data_gaps"].append(year_str)
    
    return availability

def analyze_income_trends(wi_data: dict, at_data: list) -> dict:
    """Analyze income trends over time."""
    logger.info("🔍 Analyzing income trends")
    
    trends = {
        "total_income_by_year": {},
        "income_sources": {},
        "income_growth": {},
        "volatility": {},
        "peak_income_year": None,
        "lowest_income_year": None
    }
    
    # Analyze WI income
    if isinstance(wi_data, dict):
        for tax_year, forms in wi_data.items():
            if tax_year == 'summary' or tax_year == 'tps_analysis':
                continue
                
            total_income = 0
            income_sources = {}
            
            for form in forms:
                if isinstance(form, dict) and 'Income' in form and form['Income']:
                    income = form['Income']
                    total_income += income
                    
                    form_type = form.get('Form', 'Unknown')
                    if form_type not in income_sources:
                        income_sources[form_type] = 0
                    income_sources[form_type] += income
            
            trends["total_income_by_year"][tax_year] = total_income
            trends["income_sources"][tax_year] = income_sources
    
    # Analyze AT income
    for record in at_data:
        tax_year = record['tax_year']
        agi = record.get('adjusted_gross_income', 0)
        
        if tax_year not in trends["total_income_by_year"]:
            trends["total_income_by_year"][tax_year] = 0
        trends["total_income_by_year"][tax_year] += agi
    
    # Calculate trends
    years = sorted(trends["total_income_by_year"].keys(), reverse=True)
    if len(years) >= 2:
        for i in range(len(years) - 1):
            current_year = years[i]
            previous_year = years[i + 1]
            current_income = trends["total_income_by_year"][current_year]
            previous_income = trends["total_income_by_year"][previous_year]
            
            if previous_income > 0:
                growth_rate = ((current_income - previous_income) / previous_income) * 100
                trends["income_growth"][current_year] = growth_rate
    
    # Find peak and lowest years
    if trends["total_income_by_year"]:
        max_income = max(trends["total_income_by_year"].values())
        min_income = min(trends["total_income_by_year"].values())
        
        for year, income in trends["total_income_by_year"].items():
            if income == max_income:
                trends["peak_income_year"] = year
            if income == min_income:
                trends["lowest_income_year"] = year
    
    return trends

def analyze_filing_patterns(wi_data: dict, at_data: list) -> dict:
    """Analyze filing patterns and compliance."""
    logger.info("🔍 Analyzing filing patterns")
    
    patterns = {
        "filing_timeliness": {},
        "extension_usage": {},
        "amended_returns": {},
        "compliance_issues": [],
        "filing_status_changes": []
    }
    
    # Analyze AT data for filing patterns
    for record in at_data:
        tax_year = record['tax_year']
        transactions = record.get('transactions', [])
        
        # Check for extensions
        extensions = [t for t in transactions if t.get('code') == '460']
        if extensions:
            patterns["extension_usage"][tax_year] = len(extensions)
        
        # Check for amended returns
        amended = [t for t in transactions if t.get('code') in ['150', '160'] and 'amended' in t.get('meaning', '').lower()]
        if amended:
            patterns["amended_returns"][tax_year] = len(amended)
        
        # Check filing timeliness
        filing_date = None
        for t in transactions:
            if t.get('code') == '150':  # Tax return filed
                filing_date = t.get('date')
                break
        
        if filing_date:
            try:
                from datetime import datetime
                file_date = datetime.strptime(filing_date, '%Y-%m-%d')
                due_date = datetime(int(tax_year) + 1, 4, 15)  # April 15th of next year
                
                days_late = (file_date - due_date).days
                patterns["filing_timeliness"][tax_year] = {
                    "filing_date": filing_date,
                    "days_late": days_late,
                    "on_time": days_late <= 0
                }
                
                if days_late > 0:
                    patterns["compliance_issues"].append({
                        "year": tax_year,
                        "issue": "Late filing",
                        "days_late": days_late
                    })
            except:
                pass
    
    return patterns

def analyze_financial_health(wi_data: dict, at_data: list) -> dict:
    """Analyze overall financial health indicators."""
    logger.info("🔍 Analyzing financial health")
    
    health = {
        "debt_levels": {},
        "payment_history": {},
        "income_stability": {},
        "risk_factors": [],
        "positive_indicators": []
    }
    
    # Analyze AT data for debt and payment history
    for record in at_data:
        tax_year = record['tax_year']
        account_balance = record.get('account_balance', 0)
        total_balance = record.get('total_balance', 0)
        
        health["debt_levels"][tax_year] = {
            "account_balance": account_balance,
            "total_balance": total_balance,
            "has_debt": account_balance > 0 or total_balance > 0
        }
        
        # Check for positive indicators
        if account_balance == 0 and total_balance == 0:
            health["positive_indicators"].append(f"Tax year {tax_year}: No outstanding balance")
    
    # Analyze income stability from WI data
    if isinstance(wi_data, dict):
        incomes = []
        for tax_year, forms in wi_data.items():
            if tax_year == 'summary' or tax_year == 'tps_analysis':
                continue
                
            total_income = sum(form.get('Income', 0) for form in forms if isinstance(form, dict))
            incomes.append(total_income)
        
        if len(incomes) >= 2:
            # Calculate income stability
            import statistics
            if len(incomes) > 1:
                mean_income = statistics.mean(incomes)
                std_dev = statistics.stdev(incomes) if len(incomes) > 1 else 0
                cv = (std_dev / mean_income) * 100 if mean_income > 0 else 0
                
                health["income_stability"] = {
                    "coefficient_of_variation": cv,
                    "stable": cv < 20,  # Less than 20% variation is considered stable
                    "mean_income": mean_income,
                    "std_deviation": std_dev
                }
    
    return health

def create_tax_year_breakdown(wi_data: dict, at_data: list) -> dict:
    """Create detailed breakdown by tax year."""
    logger.info("🔍 Creating tax year breakdown")
    
    breakdown = {}
    
    # Combine WI and AT data by tax year
    all_years = set()
    
    if isinstance(wi_data, dict):
        all_years.update(wi_data.keys())
    
    for record in at_data:
        all_years.add(record['tax_year'])
    
    for tax_year in sorted(all_years, reverse=True):
        if tax_year == 'summary' or tax_year == 'tps_analysis':
            continue
            
        year_data = {
            "tax_year": tax_year,
            "wi_data": wi_data.get(tax_year, []) if isinstance(wi_data, dict) else [],
            "at_data": next((r for r in at_data if r['tax_year'] == tax_year), None),
            "summary": {}
        }
        
        # Calculate year summary
        wi_forms = year_data["wi_data"]
        at_record = year_data["at_data"]
        
        # WI Summary
        total_income = sum(form.get('Income', 0) for form in wi_forms if isinstance(form, dict))
        total_withholding = sum(form.get('Withholding', 0) for form in wi_forms if isinstance(form, dict))
        form_count = len(wi_forms)
        
        year_data["summary"]["wi"] = {
            "total_income": total_income,
            "total_withholding": total_withholding,
            "form_count": form_count,
            "income_sources": list(set(form.get('Form', 'Unknown') for form in wi_forms if isinstance(form, dict)))
        }
        
        # AT Summary
        if at_record:
            year_data["summary"]["at"] = {
                "adjusted_gross_income": at_record.get('adjusted_gross_income', 0),
                "taxable_income": at_record.get('taxable_income', 0),
                "tax_per_return": at_record.get('tax_per_return', 0),
                "account_balance": at_record.get('account_balance', 0),
                "filing_status": at_record.get('filing_status', 'Unknown'),
                "transaction_count": len(at_record.get('transactions', []))
            }
        
        breakdown[tax_year] = year_data
    
    return breakdown

def generate_recommendations(wi_data: dict, at_data: list, analysis: dict) -> list:
    """Generate actionable recommendations based on analysis."""
    logger.info("🔍 Generating recommendations")
    
    recommendations = []
    
    # Data gaps
    data_gaps = analysis["data_availability"].get("data_gaps", [])
    if data_gaps:
        recommendations.append({
            "category": "Data Collection",
            "priority": "High",
            "recommendation": f"Obtain missing transcript data for years: {', '.join(data_gaps)}",
            "reason": "Missing data prevents complete analysis"
        })
    
    # Filing compliance
    compliance_issues = analysis["filing_patterns"].get("compliance_issues", [])
    for issue in compliance_issues:
        recommendations.append({
            "category": "Compliance",
            "priority": "High",
            "recommendation": f"Address late filing for {issue['year']} ({issue['days_late']} days late)",
            "reason": "Late filings can result in penalties and interest"
        })
    
    # Debt management
    debt_years = [year for year, data in analysis["financial_health"].get("debt_levels", {}).items() 
                 if data.get("has_debt", False)]
    if debt_years:
        recommendations.append({
            "category": "Financial Planning",
            "priority": "Medium",
            "recommendation": f"Review outstanding tax balances for years: {', '.join(debt_years)}",
            "reason": "Outstanding balances accrue interest and penalties"
        })
    
    # Income stability
    income_stability = analysis["financial_health"].get("income_stability", {})
    if income_stability.get("coefficient_of_variation", 0) > 30:
        recommendations.append({
            "category": "Income Planning",
            "priority": "Medium",
            "recommendation": "Consider income diversification strategies",
            "reason": "High income volatility may impact tax planning"
        })
    
    # Extension usage
    extension_years = list(analysis["filing_patterns"].get("extension_usage", {}).keys())
    if len(extension_years) > 2:
        recommendations.append({
            "category": "Tax Planning",
            "priority": "Medium",
            "recommendation": "Consider earlier tax preparation to avoid frequent extensions",
            "reason": "Regular extensions may indicate planning opportunities"
        })
    
    return recommendations

def create_summary_statistics(wi_data: dict, at_data: list, analysis: dict) -> dict:
    """Create summary statistics for the comprehensive analysis."""
    logger.info("🔍 Creating summary statistics")
    
    summary = {
        "total_tax_years_analyzed": analysis["data_availability"]["total_tax_years"],
        "total_income_reported": sum(analysis["income_analysis"].get("total_income_by_year", {}).values()),
        "average_annual_income": 0,
        "total_forms_processed": 0,
        "compliance_score": 0,
        "data_completeness": 0
    }
    
    # Calculate averages
    income_by_year = analysis["income_analysis"].get("total_income_by_year", {})
    if income_by_year:
        summary["average_annual_income"] = summary["total_income_reported"] / len(income_by_year)
    
    # Count total forms
    if isinstance(wi_data, dict):
        for tax_year, forms in wi_data.items():
            if tax_year != 'summary' and tax_year != 'tps_analysis':
                summary["total_forms_processed"] += len(forms)
    
    # Calculate compliance score
    timeliness = analysis["filing_patterns"].get("filing_timeliness", {})
    on_time_filings = sum(1 for data in timeliness.values() if data.get("on_time", False))
    total_filings = len(timeliness)
    if total_filings > 0:
        summary["compliance_score"] = (on_time_filings / total_filings) * 100
    
    # Calculate data completeness
    years_with_both = len(analysis["data_availability"].get("years_with_both", []))
    total_years = summary["total_tax_years_analyzed"]
    if total_years > 0:
        summary["data_completeness"] = (years_with_both / total_years) * 100
    
    return summary

def perform_tps_analysis(wi_data: dict, at_data: list, filing_status: str) -> dict:
    """Perform TP/S specific analysis."""
    logger.info("🔍 Performing TP/S analysis")
    
    tps_analysis = {
        "owner_breakdown": {},
        "filing_status_analysis": {},
        "missing_spouse_data": [],
        "amendment_recommendations": []
    }
    
    # Analyze WI data by owner
    if isinstance(wi_data, dict):
        for tax_year, forms in wi_data.items():
            if tax_year == 'summary' or tax_year == 'tps_analysis':
                continue
                
            owners = {}
            for form in forms:
                if isinstance(form, dict):
                    owner = form.get('Owner', 'TP')
                    if owner not in owners:
                        owners[owner] = {
                            'income': 0,
                            'withholding': 0,
                            'forms': []
                        }
                    
                    owners[owner]['income'] += form.get('Income', 0)
                    owners[owner]['withholding'] += form.get('Withholding', 0)
                    owners[owner]['forms'].append(form.get('Form', 'Unknown'))
            
            tps_analysis["owner_breakdown"][tax_year] = owners
    
    # Analyze AT data by owner
    at_owners = {}
    for record in at_data:
        owner = record.get('owner', 'TP')
        tax_year = record['tax_year']
        
        if owner not in at_owners:
            at_owners[owner] = {}
        
        if tax_year not in at_owners[owner]:
            at_owners[owner][tax_year] = {
                'agi': 0,
                'taxable_income': 0,
                'tax_per_return': 0
            }
        
        at_owners[owner][tax_year]['agi'] += record.get('adjusted_gross_income', 0)
        at_owners[owner][tax_year]['taxable_income'] += record.get('taxable_income', 0)
        at_owners[owner][tax_year]['tax_per_return'] += record.get('tax_per_return', 0)
    
    tps_analysis["at_owner_breakdown"] = at_owners
    
    return tps_analysis

# --- File Analysis & Client Detection Endpoints ---

@router.get("/client-analysis/{case_id}", tags=["Analysis"])
def get_client_analysis(case_id: str):
    """
    Analyze file names to detect TP/S ownership patterns and extract client information.
    Returns automated detection of filing status and TP/S breakdown.
    """
    logger.info(f"🔍 Received client analysis request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch file grids for analysis
        logger.info(f"📋 Fetching WI files for client analysis")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        
        logger.info(f"📋 Fetching AT files for client analysis")
        at_files = fetch_at_file_grid(case_id, cookies)
        
        # Analyze file patterns
        analysis = analyze_client_files(wi_files, at_files, case_id)
        
        # Try to extract additional client info from Logiqs
        try:
            client_info = extract_client_info_from_logiqs(case_id, cookies)
            analysis["logiqs_client_info"] = client_info
        except Exception as e:
            logger.warning(f"⚠️ Could not extract Logiqs client info: {str(e)}")
            analysis["logiqs_client_info"] = None
        
        logger.info(f"✅ Successfully completed client analysis for case_id: {case_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing client analysis for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def analyze_client_files(wi_files: list, at_files: list, case_id: str) -> dict:
    """
    Analyze file names to detect TP/S ownership patterns and filing status.
    """
    logger.info(f"🔍 Analyzing client files for case_id: {case_id}")
    
    analysis = {
        "case_id": case_id,
        "analysis_date": datetime.now().isoformat(),
        "file_analysis": {
            "wi_files": [],
            "at_files": [],
            "ownership_patterns": {},
            "filing_status_detection": {},
            "recommendations": []
        },
        "detected_owners": set(),
        "suggested_filing_status": None,
        "tps_analysis_enabled": False
    }
    
    # Analyze WI files
    if wi_files:
        for file_info in wi_files:
            filename = file_info.get('FileName', '')
            file_analysis = analyze_filename_patterns(filename, 'WI')
            analysis["file_analysis"]["wi_files"].append({
                "filename": filename,
                "analysis": file_analysis
            })
            
            if file_analysis.get('detected_owner'):
                analysis["detected_owners"].add(file_analysis['detected_owner'])
    
    # Analyze AT files
    if at_files:
        for file_info in at_files:
            filename = file_info.get('FileName', '')
            file_analysis = analyze_filename_patterns(filename, 'AT')
            analysis["file_analysis"]["at_files"].append({
                "filename": filename,
                "analysis": file_analysis
            })
            
            if file_analysis.get('detected_owner'):
                analysis["detected_owners"].add(file_analysis['detected_owner'])
    
    # Convert set to list for JSON serialization
    analysis["detected_owners"] = list(analysis["detected_owners"])
    
    # Analyze ownership patterns
    analysis["file_analysis"]["ownership_patterns"] = analyze_ownership_patterns(
        analysis["file_analysis"]["wi_files"], 
        analysis["file_analysis"]["at_files"]
    )
    
    # Detect filing status
    analysis["file_analysis"]["filing_status_detection"] = detect_filing_status_from_files(
        analysis["file_analysis"]["wi_files"], 
        analysis["file_analysis"]["at_files"]
    )
    
    # Set suggested filing status
    analysis["suggested_filing_status"] = analysis["file_analysis"]["filing_status_detection"].get("suggested_status")
    
    # Determine if TP/S analysis should be enabled
    analysis["tps_analysis_enabled"] = len(analysis["detected_owners"]) > 1 or analysis["suggested_filing_status"] in [
        "Married Filing Jointly", "Married Filing Separately"
    ]
    
    # Generate recommendations
    analysis["file_analysis"]["recommendations"] = generate_file_analysis_recommendations(analysis)
    
    return analysis

def analyze_filename_patterns(filename: str, file_type: str) -> dict:
    """
    Analyze individual filename for TP/S patterns and other indicators.
    """
    analysis = {
        "filename": filename,
        "file_type": file_type,
        "detected_owner": None,
        "confidence": 0,
        "patterns_found": [],
        "filing_status_hints": []
    }
    
    filename_upper = filename.upper()
    
    # TP/S Detection Patterns - Enhanced
    tp_patterns = [
        r'\bTP\b', r'\bTAXPAYER\b', r'\bPRIMARY\b', r'\bMAIN\b',
        r'_TP_', r'_TAXPAYER_', r'_PRIMARY_', r'_MAIN_',
        r'\bFIRST\b', r'\b1ST\b', r'\bONE\b'
    ]
    
    spouse_patterns = [
        r'\bSP\b', r'\bSPOUSE\b', r'\bSECONDARY\b', r'\bJOINT\b',
        r'_SP_', r'_SPOUSE_', r'_SECONDARY_', r'_JOINT_',
        r'\bSECOND\b', r'\b2ND\b', r'\bTWO\b', r'\bE\b(?=\s|$)',  # E for extension/spouse
        r'\bEXT\b', r'\bEXTENSION\b'
    ]
    
    # Check for TP patterns
    for pattern in tp_patterns:
        if re.search(pattern, filename_upper):
            analysis["detected_owner"] = "TP"
            analysis["confidence"] += 0.3
            analysis["patterns_found"].append(f"TP pattern: {pattern}")
            break
    
    # Check for Spouse patterns
    for pattern in spouse_patterns:
        if re.search(pattern, filename_upper):
            analysis["detected_owner"] = "S"
            analysis["confidence"] += 0.3
            analysis["patterns_found"].append(f"Spouse pattern: {pattern}")
            break
    
    # Special case: "E" at the end might indicate spouse/extension
    if re.search(r'\bE\b(?=\s|\.|$)', filename_upper) and not analysis["detected_owner"]:
        analysis["detected_owner"] = "S"
        analysis["confidence"] += 0.2
        analysis["patterns_found"].append("E suffix pattern (likely spouse/extension)")
    
    # Check for summary files (might indicate combined data)
    if re.search(r'\bSUM\b', filename_upper):
        analysis["patterns_found"].append("Summary file detected")
        analysis["confidence"] += 0.1
    
    # Filing Status Detection Patterns - Enhanced
    joint_patterns = [
        r'\bJOINT\b', r'\bMFJ\b', r'\bMARRIED\b.*\bJOINT\b',
        r'_JOINT_', r'_MFJ_', r'_MARRIED_',
        r'\bCOMBINED\b', r'\bBOTH\b'
    ]
    
    separate_patterns = [
        r'\bSEP\b', r'\bMFS\b', r'\bSEPARATE\b', r'\bINDIVIDUAL\b',
        r'_SEP_', r'_MFS_', r'_SEPARATE_', r'_INDIVIDUAL_',
        r'\bSINGLE\b', r'\bSGL\b'
    ]
    
    single_patterns = [
        r'\bSINGLE\b', r'\bSGL\b', r'\bINDIVIDUAL\b',
        r'_SINGLE_', r'_SGL_', r'_INDIVIDUAL_'
    ]
    
    # Check filing status patterns
    for pattern in joint_patterns:
        if re.search(pattern, filename_upper):
            analysis["filing_status_hints"].append("Married Filing Jointly")
            analysis["confidence"] += 0.2
            break
    
    for pattern in separate_patterns:
        if re.search(pattern, filename_upper):
            analysis["filing_status_hints"].append("Married Filing Separately")
            analysis["confidence"] += 0.2
            break
    
    for pattern in single_patterns:
        if re.search(pattern, filename_upper):
            analysis["filing_status_hints"].append("Single")
            analysis["confidence"] += 0.2
            break
    
    # Tax year detection
    year_match = re.search(r'\b(20[12]\d)\b', filename)
    if year_match:
        analysis["tax_year"] = year_match.group(1)
        analysis["confidence"] += 0.1
    
    # Cap confidence at 1.0
    analysis["confidence"] = min(analysis["confidence"], 1.0)
    
    return analysis

def analyze_ownership_patterns(wi_files: list, at_files: list) -> dict:
    """
    Analyze overall ownership patterns across all files.
    """
    patterns = {
        "total_files": len(wi_files) + len(at_files),
        "wi_files": len(wi_files),
        "at_files": len(at_files),
        "owner_distribution": {},
        "confidence_scores": {},
        "mixed_ownership": False,
        "single_owner": False
    }
    
    # Count owners
    all_owners = []
    for file_analysis in wi_files + at_files:
        owner = file_analysis["analysis"].get("detected_owner")
        if owner:
            all_owners.append(owner)
    
    # Calculate distribution
    from collections import Counter
    owner_counts = Counter(all_owners)
    patterns["owner_distribution"] = dict(owner_counts)
    
    # Determine patterns
    unique_owners = set(all_owners)
    patterns["mixed_ownership"] = len(unique_owners) > 1
    patterns["single_owner"] = len(unique_owners) == 1
    
    # Calculate confidence scores
    total_files = len(all_owners)
    for owner, count in owner_counts.items():
        patterns["confidence_scores"][owner] = count / total_files if total_files > 0 else 0
    
    return patterns

def detect_filing_status_from_files(wi_files: list, at_files: list) -> dict:
    """
    Detect filing status based on file patterns and ownership.
    """
    detection = {
        "suggested_status": None,
        "confidence": 0,
        "evidence": [],
        "alternative_statuses": []
    }
    
    # Collect all filing status hints
    all_hints = []
    for file_analysis in wi_files + at_files:
        hints = file_analysis["analysis"].get("filing_status_hints", [])
        all_hints.extend(hints)
    
    # Count hints
    from collections import Counter
    hint_counts = Counter(all_hints)
    
    if hint_counts:
        # Get most common hint
        most_common = hint_counts.most_common(1)[0]
        detection["suggested_status"] = most_common[0]
        detection["confidence"] = most_common[1] / len(all_hints) if all_hints else 0
        detection["evidence"] = [f"{status}: {count} files" for status, count in hint_counts.items()]
    
    # Analyze ownership patterns for additional clues
    all_owners = []
    for file_analysis in wi_files + at_files:
        owner = file_analysis["analysis"].get("detected_owner")
        if owner:
            all_owners.append(owner)
    
    unique_owners = set(all_owners)
    
    # If we have both TP and S, likely married
    if "TP" in unique_owners and "S" in unique_owners:
        if not detection["suggested_status"]:
            detection["suggested_status"] = "Married Filing Jointly"
            detection["confidence"] = 0.7
        detection["evidence"].append("Both TP and S files detected")
    
    # If only S owner, likely married filing separately
    elif len(unique_owners) == 1 and "S" in unique_owners:
        if not detection["suggested_status"]:
            detection["suggested_status"] = "Married Filing Separately"
            detection["confidence"] = 0.6
        detection["evidence"].append("Only spouse files detected - likely married filing separately")
    
    # If only one owner (not S), could be single or separate
    elif len(unique_owners) == 1 and "S" not in unique_owners:
        if not detection["suggested_status"]:
            detection["suggested_status"] = "Single"
            detection["confidence"] = 0.6
        detection["evidence"].append(f"Single owner detected: {list(unique_owners)[0]}")
    
    return detection

def generate_file_analysis_recommendations(analysis: dict) -> list:
    """
    Generate recommendations based on file analysis.
    """
    recommendations = []
    
    # Check for mixed ownership
    if analysis["file_analysis"]["ownership_patterns"]["mixed_ownership"]:
        recommendations.append({
            "type": "TP/S Analysis",
            "priority": "High",
            "recommendation": "Enable TP/S analysis in comprehensive analysis endpoint",
            "reason": "Multiple owners detected in file names"
        })
    
    # Check filing status confidence
    filing_detection = analysis["file_analysis"]["filing_status_detection"]
    if filing_detection["confidence"] < 0.5:
        recommendations.append({
            "type": "Filing Status",
            "priority": "Medium",
            "recommendation": "Manually verify filing status",
            "reason": f"Low confidence in detected status: {filing_detection['suggested_status']}"
        })
    
    # Check for missing spouse data
    owners = analysis["detected_owners"]
    if "TP" in owners and "S" not in owners and filing_detection["suggested_status"] in ["Married Filing Jointly", "Married Filing Separately"]:
        recommendations.append({
            "type": "Data Completeness",
            "priority": "Medium",
            "recommendation": "Check for missing spouse transcript files",
            "reason": "Married filing status detected but no spouse files found"
        })
    
    return recommendations

def extract_client_info_from_logiqs(case_id: str, cookies: dict) -> dict:
    """
    Extract client information from Logiqs case page.
    """
    logger.info(f"🔍 Extracting client info from Logiqs for case_id: {case_id}")
    
    try:
        import requests
        
        # Build case URL
        case_url = f"https://tps.logiqs.com/Cases/Case.aspx?CaseID={case_id}&ProductID=1"
        
        # Convert cookies dict to string
        cookies_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        headers = {
            'Cookie': cookies_string,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(case_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            html_content = response.text
            
            # Extract TaxAmount using multiple patterns
            tax_amount = None
            tax_patterns = [
                r'TaxAmount["\s]*:["\s]*([0-9.]+)',
                r'name=["\']taxamount["\'][^>]*value=["\']([0-9.]+)["\']',
                r'taxAmount["\s]*=["\s]*([0-9.]+)',
                r'\$([0-9,]+\.?[0-9]*)'
            ]
            
            for pattern in tax_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    try:
                        tax_amount = float(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue
            
            # Extract ClientDetailNetIncome
            client_agi = None
            net_income_match = re.search(r'ClientDetailNetIncom["\s]*:["\s]*"?\$?([0-9,.]+)', html_content, re.IGNORECASE)
            if net_income_match:
                try:
                    monthly_income = float(net_income_match.group(1).replace(',', ''))
                    client_agi = round(monthly_income * 12)
                except ValueError:
                    pass
            
            # Extract MaritalStatus
            marital_status_map = {
                "0": "Single",
                "1": "Married Filing Jointly", 
                "2": "Married Filing Separately",
                "3": "Head of Household",
                "4": "Qualifying Widow(er)"
            }
            
            current_filing_status = None
            marital_status_match = re.search(r'MartialStatus["\s]*:["\s]*([0-4])', html_content, re.IGNORECASE)
            if marital_status_match and marital_status_match.group(1) in marital_status_map:
                current_filing_status = marital_status_map[marital_status_match.group(1)]
            
            return {
                "total_tax_debt": tax_amount,
                "client_agi": client_agi,
                "current_filing_status": current_filing_status,
                "currency": "USD" if tax_amount else None,
                "extracted_at": datetime.now().isoformat(),
                "url": case_url,
                "success": True
            }
        else:
            logger.warning(f"⚠️ Logiqs request failed with status {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"❌ Error extracting Logiqs client info: {str(e)}")
        return {"success": False, "error": str(e)}

# --- Enhanced Comprehensive Analysis with Auto-Detection ---

@router.get("/analysis/{case_id}/auto", tags=["Analysis"])
def get_comprehensive_analysis_auto(case_id: str):
    """
    Get comprehensive tax analysis with automatic TP/S and filing status detection.
    """
    logger.info(f"🔍 Received auto comprehensive analysis request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # First, get client analysis
        logger.info(f"📋 Getting client analysis for auto-detection")
        client_analysis = get_client_analysis(case_id)
        
        # Extract detected values
        include_tps_analysis = client_analysis.get("tps_analysis_enabled", False)
        filing_status = client_analysis.get("suggested_filing_status")
        
        # Get Logiqs client info if available
        logiqs_info = client_analysis.get("logiqs_client_info", {})
        if logiqs_info and logiqs_info.get("success") and logiqs_info.get("current_filing_status"):
            filing_status = logiqs_info["current_filing_status"]
        
        logger.info(f"🔍 Auto-detected: TP/S={include_tps_analysis}, Filing Status={filing_status}")
        
        # Now get comprehensive analysis with detected values
        analysis = get_comprehensive_analysis(case_id, include_tps_analysis, filing_status)
        
        # Add client analysis to the response
        analysis["client_analysis"] = client_analysis
        
        logger.info(f"✅ Successfully completed auto comprehensive analysis for case_id: {case_id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error performing auto comprehensive analysis for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") 

# --- Pricing Model Schema Endpoint ---

@router.get("/pricing-model/{case_id}", tags=["Analysis"])
def get_pricing_model_schema(
    case_id: str,
    product_id: Optional[int] = Query(1, description="Product ID for Logiqs case"),
    include_analysis: Optional[bool] = Query(True, description="Include comprehensive analysis in response")
):
    """
    Get pricing model schema combining Logiqs client data with comprehensive analysis.
    Returns pricing recommendations, client insights, and financial analysis.
    """
    logger.info(f"💰 Received pricing model request for case_id: {case_id}, product_id: {product_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Extract client info from Logiqs
        logger.info(f"🔍 Extracting Logiqs client info for pricing model")
        logiqs_client_info = extract_client_info_from_logiqs(case_id, cookies)
        
        # Get comprehensive analysis if requested
        comprehensive_analysis = None
        if include_analysis:
            try:
                logger.info(f"📊 Getting comprehensive analysis for pricing model")
                comprehensive_analysis = get_comprehensive_analysis_auto(case_id)
            except Exception as e:
                logger.warning(f"⚠️ Could not get comprehensive analysis: {str(e)}")
                comprehensive_analysis = {"error": str(e)}
        
        # Build pricing model schema
        pricing_schema = build_pricing_model_schema(
            case_id, 
            product_id, 
            logiqs_client_info, 
            comprehensive_analysis
        )
        
        logger.info(f"✅ Successfully completed pricing model schema for case_id: {case_id}")
        return pricing_schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating pricing model schema for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def build_pricing_model_schema(
    case_id: str, 
    product_id: int, 
    logiqs_client_info: dict, 
    comprehensive_analysis: dict = None
) -> dict:
    """
    Build comprehensive pricing model schema with client insights and recommendations.
    """
    logger.info(f"🏗️ Building pricing model schema for case_id: {case_id}")
    
    # Base schema structure
    schema = {
        "success": True,
        "message": "Pricing model schema generated successfully",
        "data": {
            "case_id": case_id,
            "product_id": product_id,
            "generated_at": datetime.now().isoformat(),
            "logiqs_data": logiqs_client_info,
            "pricing_analysis": {},
            "client_insights": {},
            "recommendations": [],
            "risk_assessment": {},
            "service_tier": None,
            "estimated_fees": {}
        }
    }
    
    # Extract key financial data
    total_tax_debt = logiqs_client_info.get("total_tax_debt", 0)
    client_agi = logiqs_client_info.get("client_agi", 0)
    current_filing_status = logiqs_client_info.get("current_filing_status")
    
    # Build pricing analysis
    schema["data"]["pricing_analysis"] = analyze_pricing_factors(
        total_tax_debt, 
        client_agi, 
        current_filing_status,
        comprehensive_analysis
    )
    
    # Build client insights
    schema["data"]["client_insights"] = generate_client_insights(
        total_tax_debt,
        client_agi,
        current_filing_status,
        comprehensive_analysis
    )
    
    # Determine service tier
    schema["data"]["service_tier"] = determine_service_tier(
        total_tax_debt,
        client_agi,
        comprehensive_analysis
    )
    
    # Calculate estimated fees
    schema["data"]["estimated_fees"] = calculate_estimated_fees(
        schema["data"]["service_tier"],
        total_tax_debt,
        comprehensive_analysis
    )
    
    # Generate recommendations
    schema["data"]["recommendations"] = generate_pricing_recommendations(
        schema["data"]["pricing_analysis"],
        schema["data"]["client_insights"],
        comprehensive_analysis
    )
    
    # Risk assessment
    schema["data"]["risk_assessment"] = assess_client_risk(
        total_tax_debt,
        client_agi,
        comprehensive_analysis
    )
    
    # Add comprehensive analysis if available
    if comprehensive_analysis and "error" not in comprehensive_analysis:
        schema["data"]["comprehensive_analysis"] = comprehensive_analysis
    
    return schema

def analyze_pricing_factors(
    total_tax_debt: float, 
    client_agi: float, 
    filing_status: str,
    comprehensive_analysis: dict = None
) -> dict:
    """
    Analyze factors that influence pricing decisions.
    """
    analysis = {
        "debt_level": "Low",
        "income_level": "Low",
        "complexity_score": 0,
        "urgency_score": 0,
        "compliance_issues": [],
        "special_circumstances": []
    }
    
    # Debt level analysis
    if total_tax_debt:
        if total_tax_debt < 10000:
            analysis["debt_level"] = "Low"
        elif total_tax_debt < 50000:
            analysis["debt_level"] = "Medium"
        elif total_tax_debt < 100000:
            analysis["debt_level"] = "High"
        else:
            analysis["debt_level"] = "Very High"
    
    # Income level analysis
    if client_agi:
        if client_agi < 50000:
            analysis["income_level"] = "Low"
        elif client_agi < 100000:
            analysis["income_level"] = "Medium"
        elif client_agi < 200000:
            analysis["income_level"] = "High"
        else:
            analysis["income_level"] = "Very High"
    
    # Complexity scoring
    complexity_score = 0
    
    # Filing status complexity
    if filing_status in ["Married Filing Separately", "Head of Household"]:
        complexity_score += 2
    elif filing_status == "Married Filing Jointly":
        complexity_score += 1
    
    # Add complexity from comprehensive analysis
    if comprehensive_analysis:
        # Multiple tax years
        tax_years = comprehensive_analysis.get("data_availability", {}).get("total_tax_years", 0)
        if tax_years > 5:
            complexity_score += 2
        elif tax_years > 3:
            complexity_score += 1
        
        # Compliance issues
        compliance_issues = comprehensive_analysis.get("filing_patterns", {}).get("compliance_issues", [])
        if compliance_issues:
            analysis["compliance_issues"] = compliance_issues
            complexity_score += len(compliance_issues) * 2
        
        # TP/S analysis complexity
        if comprehensive_analysis.get("tps_analysis"):
            complexity_score += 3
        
        # Multiple income sources
        income_sources = comprehensive_analysis.get("income_analysis", {}).get("income_sources", {})
        total_sources = sum(len(sources) for sources in income_sources.values())
        if total_sources > 20:
            complexity_score += 2
        elif total_sources > 10:
            complexity_score += 1
    
    analysis["complexity_score"] = min(complexity_score, 10)  # Cap at 10
    
    # Urgency scoring
    urgency_score = 0
    
    if total_tax_debt and total_tax_debt > 50000:
        urgency_score += 3
    elif total_tax_debt and total_tax_debt > 25000:
        urgency_score += 2
    elif total_tax_debt and total_tax_debt > 10000:
        urgency_score += 1
    
    # Add urgency from compliance issues
    if analysis["compliance_issues"]:
        urgency_score += len(analysis["compliance_issues"])
    
    analysis["urgency_score"] = min(urgency_score, 10)  # Cap at 10
    
    return analysis

def generate_client_insights(
    total_tax_debt: float,
    client_agi: float,
    filing_status: str,
    comprehensive_analysis: dict = None
) -> dict:
    """
    Generate insights about the client's financial situation and needs.
    """
    insights = {
        "financial_profile": "Standard",
        "debt_to_income_ratio": None,
        "payment_capacity": "Unknown",
        "priority_concerns": [],
        "opportunities": [],
        "warning_signs": []
    }
    
    # Calculate debt-to-income ratio
    if total_tax_debt and client_agi and client_agi > 0:
        debt_ratio = (total_tax_debt / client_agi) * 100
        insights["debt_to_income_ratio"] = round(debt_ratio, 2)
        
        if debt_ratio > 50:
            insights["financial_profile"] = "High Risk"
            insights["warning_signs"].append("Very high debt-to-income ratio")
        elif debt_ratio > 25:
            insights["financial_profile"] = "Moderate Risk"
            insights["warning_signs"].append("High debt-to-income ratio")
        elif debt_ratio > 10:
            insights["financial_profile"] = "Standard"
        else:
            insights["financial_profile"] = "Low Risk"
            insights["opportunities"].append("Low debt burden - good payment capacity")
    
    # Payment capacity assessment
    if client_agi:
        if client_agi > 100000:
            insights["payment_capacity"] = "High"
        elif client_agi > 50000:
            insights["payment_capacity"] = "Medium"
        else:
            insights["payment_capacity"] = "Low"
    
    # Priority concerns
    if total_tax_debt and total_tax_debt > 50000:
        insights["priority_concerns"].append("High tax debt requiring immediate attention")
    
    if comprehensive_analysis:
        # Add insights from comprehensive analysis
        compliance_issues = comprehensive_analysis.get("filing_patterns", {}).get("compliance_issues", [])
        if compliance_issues:
            insights["priority_concerns"].append(f"{len(compliance_issues)} compliance issues detected")
        
        # Income stability
        income_stability = comprehensive_analysis.get("financial_health", {}).get("income_stability", {})
        if income_stability.get("stable") == False:
            insights["warning_signs"].append("Unstable income pattern")
        
        # Outstanding balances
        debt_levels = comprehensive_analysis.get("financial_health", {}).get("debt_levels", {})
        years_with_debt = [year for year, data in debt_levels.items() if data.get("has_debt")]
        if years_with_debt:
            insights["priority_concerns"].append(f"Outstanding balances in {len(years_with_debt)} tax years")
    
    return insights

def determine_service_tier(
    total_tax_debt: float,
    client_agi: float,
    comprehensive_analysis: dict = None
) -> str:
    """
    Determine appropriate service tier based on client factors.
    """
    # Base tier determination
    if total_tax_debt and total_tax_debt > 100000:
        base_tier = "Premium"
    elif total_tax_debt and total_tax_debt > 50000:
        base_tier = "Standard Plus"
    elif total_tax_debt and total_tax_debt > 25000:
        base_tier = "Standard"
    else:
        base_tier = "Basic"
    
    # Adjust based on complexity
    if comprehensive_analysis:
        complexity_score = comprehensive_analysis.get("pricing_analysis", {}).get("complexity_score", 0)
        
        if complexity_score >= 8:
            if base_tier == "Basic":
                base_tier = "Standard"
            elif base_tier == "Standard":
                base_tier = "Standard Plus"
            elif base_tier == "Standard Plus":
                base_tier = "Premium"
    
    return base_tier

def calculate_estimated_fees(
    service_tier: str,
    total_tax_debt: float,
    comprehensive_analysis: dict = None
) -> dict:
    """
    Calculate estimated fees based on service tier and complexity.
    """
    # Base fees by tier
    base_fees = {
        "Basic": 1500,
        "Standard": 2500,
        "Standard Plus": 3500,
        "Premium": 5000
    }
    
    base_fee = base_fees.get(service_tier, 2500)
    
    # Complexity adjustments
    complexity_multiplier = 1.0
    if comprehensive_analysis:
        complexity_score = comprehensive_analysis.get("pricing_analysis", {}).get("complexity_score", 0)
        
        if complexity_score >= 8:
            complexity_multiplier = 1.5
        elif complexity_score >= 6:
            complexity_multiplier = 1.3
        elif complexity_score >= 4:
            complexity_multiplier = 1.1
    
    # Debt-based adjustments
    debt_multiplier = 1.0
    if total_tax_debt:
        if total_tax_debt > 100000:
            debt_multiplier = 1.4
        elif total_tax_debt > 50000:
            debt_multiplier = 1.2
        elif total_tax_debt > 25000:
            debt_multiplier = 1.1
    
    estimated_fee = base_fee * complexity_multiplier * debt_multiplier
    
    return {
        "base_fee": base_fee,
        "complexity_multiplier": complexity_multiplier,
        "debt_multiplier": debt_multiplier,
        "estimated_total": round(estimated_fee),
        "payment_plans": {
            "monthly_3": round(estimated_fee / 3, 2),
            "monthly_6": round(estimated_fee / 6, 2),
            "monthly_12": round(estimated_fee / 12, 2)
        }
    }

def generate_pricing_recommendations(
    pricing_analysis: dict,
    client_insights: dict,
    comprehensive_analysis: dict = None
) -> list:
    """
    Generate pricing and service recommendations.
    """
    recommendations = []
    
    # Service tier recommendations
    if pricing_analysis.get("complexity_score", 0) >= 8:
        recommendations.append({
            "category": "Service Level",
            "priority": "High",
            "recommendation": "Consider Premium service tier due to high complexity",
            "reason": f"Complexity score: {pricing_analysis['complexity_score']}/10"
        })
    
    # Payment plan recommendations
    if client_insights.get("payment_capacity") == "Low":
        recommendations.append({
            "category": "Payment",
            "priority": "Medium",
            "recommendation": "Offer extended payment plans (6-12 months)",
            "reason": "Low payment capacity detected"
        })
    
    # Urgency recommendations
    if pricing_analysis.get("urgency_score", 0) >= 7:
        recommendations.append({
            "category": "Timeline",
            "priority": "High",
            "recommendation": "Expedite case processing due to high urgency",
            "reason": f"Urgency score: {pricing_analysis['urgency_score']}/10"
        })
    
    # Compliance recommendations
    if client_insights.get("priority_concerns"):
        for concern in client_insights["priority_concerns"]:
            recommendations.append({
                "category": "Compliance",
                "priority": "High",
                "recommendation": f"Address: {concern}",
                "reason": "Critical compliance issue"
            })
    
    return recommendations

def assess_client_risk(
    total_tax_debt: float,
    client_agi: float,
    comprehensive_analysis: dict = None
) -> dict:
    """
    Assess overall client risk profile.
    """
    risk_assessment = {
        "overall_risk": "Low",
        "risk_factors": [],
        "mitigation_strategies": [],
        "approval_recommendation": "Approve"
    }
    
    risk_score = 0
    
    # Debt-based risk
    if total_tax_debt:
        if total_tax_debt > 100000:
            risk_score += 4
            risk_assessment["risk_factors"].append("Very high tax debt")
        elif total_tax_debt > 50000:
            risk_score += 3
            risk_assessment["risk_factors"].append("High tax debt")
        elif total_tax_debt > 25000:
            risk_score += 2
            risk_assessment["risk_factors"].append("Moderate tax debt")
        elif total_tax_debt > 10000:
            risk_score += 1
            risk_assessment["risk_factors"].append("Low tax debt")
    
    # Income-based risk
    if client_agi:
        if client_agi < 30000:
            risk_score += 3
            risk_assessment["risk_factors"].append("Low income")
        elif client_agi < 50000:
            risk_score += 2
            risk_assessment["risk_factors"].append("Moderate income")
        elif client_agi > 200000:
            risk_score -= 1  # High income reduces risk
    
    # Compliance risk from comprehensive analysis
    if comprehensive_analysis:
        compliance_issues = comprehensive_analysis.get("filing_patterns", {}).get("compliance_issues", [])
        if compliance_issues:
            risk_score += len(compliance_issues)
            risk_assessment["risk_factors"].append(f"{len(compliance_issues)} compliance issues")
    
    # Determine overall risk
    if risk_score >= 8:
        risk_assessment["overall_risk"] = "Very High"
        risk_assessment["approval_recommendation"] = "Review Required"
    elif risk_score >= 6:
        risk_assessment["overall_risk"] = "High"
        risk_assessment["approval_recommendation"] = "Approve with Conditions"
    elif risk_score >= 4:
        risk_assessment["overall_risk"] = "Medium"
        risk_assessment["approval_recommendation"] = "Approve"
    elif risk_score >= 2:
        risk_assessment["overall_risk"] = "Low"
        risk_assessment["approval_recommendation"] = "Approve"
    else:
        risk_assessment["overall_risk"] = "Very Low"
        risk_assessment["approval_recommendation"] = "Approve"
    
    # Mitigation strategies
    if risk_score >= 6:
        risk_assessment["mitigation_strategies"].append("Require upfront payment")
        risk_assessment["mitigation_strategies"].append("Shorter payment terms")
        risk_assessment["mitigation_strategies"].append("Regular progress updates")
    
    return risk_assessment

# --- Case Attributes v1 Endpoint (for ML Training) ---

@router.get("/case-attributesv1/{case_id}", tags=["Analysis"])
def get_case_attributes_v1(
    case_id: str,
    product_id: Optional[int] = Query(1, description="Product ID for Logiqs case")
):
    """
    Extract core case attributes for ML model training.
    Returns key financial attributes like tax liability, AGI, debt-to-AGI ratio, etc.
    """
    logger.info(f"💰 Fetching case attributes v1 for case_id: {case_id}, product_id: {product_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Extract client info from Logiqs
        logger.info(f"🔍 Extracting Logiqs client info for case attributes")
        logiqs_client_info = extract_client_info_from_logiqs(case_id, cookies)
        
        # Get comprehensive analysis for additional attributes
        try:
            logger.info(f"📊 Getting comprehensive analysis for additional attributes")
            comprehensive_analysis = get_comprehensive_analysis_auto(case_id)
        except Exception as e:
            logger.warning(f"⚠️ Could not get comprehensive analysis: {str(e)}")
            comprehensive_analysis = None
        
        # Build case attributes
        case_attributes = build_case_attributes_v1(
            case_id, 
            product_id, 
            logiqs_client_info, 
            comprehensive_analysis
        )
        
        logger.info(f"✅ Successfully completed case attributes v1 for case_id: {case_id}")
        return case_attributes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating case attributes v1 for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def build_case_attributes_v1(
    case_id: str, 
    product_id: int, 
    logiqs_client_info: dict, 
    comprehensive_analysis: dict = None
) -> dict:
    """
    Build case attributes for ML model training.
    """
    logger.info(f"🏗️ Building case attributes v1 for case_id: {case_id}")
    
    # Extract base data from Logiqs
    total_tax_debt = logiqs_client_info.get("total_tax_debt", 0)
    client_agi = logiqs_client_info.get("client_agi", 0)
    current_filing_status = logiqs_client_info.get("current_filing_status")
    
    # Calculate debt-to-AGI ratio
    debt_to_agi_ratio = None
    if total_tax_debt and client_agi and client_agi > 0:
        debt_to_agi_ratio = round((total_tax_debt / client_agi) * 100, 2)
    
    # Base attributes structure
    attributes = {
        "success": True,
        "message": "Case attributes extracted successfully",
        "data": {
            "case_id": case_id,
            "product_id": product_id,
            "extracted_at": datetime.now().isoformat(),
            "url": logiqs_client_info.get("url"),
            
            # Core financial attributes
            "total_tax_debt": total_tax_debt,
            "client_agi": client_agi,
            "debt_to_agi_ratio": debt_to_agi_ratio,
            "current_filing_status": current_filing_status,
            "currency": "USD" if total_tax_debt else None,
            
            # Additional attributes from comprehensive analysis
            "additional_attributes": {}
        }
    }
    
    # Add attributes from comprehensive analysis if available
    if comprehensive_analysis and "error" not in comprehensive_analysis:
        additional_attrs = extract_additional_attributes(comprehensive_analysis)
        attributes["data"]["additional_attributes"] = additional_attrs
    
    return attributes

def extract_additional_attributes(comprehensive_analysis: dict) -> dict:
    """
    Extract additional attributes from comprehensive analysis for ML training.
    """
    additional_attrs = {}
    
    try:
        # Income analysis
        income_analysis = comprehensive_analysis.get("income_analysis", {})
        if income_analysis:
            additional_attrs.update({
                "total_income_reported": income_analysis.get("total_income_by_year", {}),
                "average_annual_income": income_analysis.get("average_annual_income"),
                "peak_income_year": income_analysis.get("peak_income_year"),
                "lowest_income_year": income_analysis.get("lowest_income_year"),
                "income_volatility": income_analysis.get("volatility", {})
            })
        
        # Filing patterns
        filing_patterns = comprehensive_analysis.get("filing_patterns", {})
        if filing_patterns:
            # Calculate compliance metrics
            compliance_issues = filing_patterns.get("compliance_issues", [])
            late_filings = [issue for issue in compliance_issues if issue.get("issue") == "Late filing"]
            
            additional_attrs.update({
                "total_compliance_issues": len(compliance_issues),
                "late_filing_count": len(late_filings),
                "average_days_late": sum(issue.get("days_late", 0) for issue in late_filings) / len(late_filings) if late_filings else 0,
                "extension_usage": filing_patterns.get("extension_usage", {}),
                "amended_returns": filing_patterns.get("amended_returns", {})
            })
        
        # Financial health
        financial_health = comprehensive_analysis.get("financial_health", {})
        if financial_health:
            debt_levels = financial_health.get("debt_levels", {})
            years_with_debt = [year for year, data in debt_levels.items() if data.get("has_debt")]
            
            additional_attrs.update({
                "years_with_outstanding_balance": len(years_with_debt),
                "total_years_analyzed": len(debt_levels),
                "income_stability_coefficient": financial_health.get("income_stability", {}).get("coefficient_of_variation"),
                "income_stable": financial_health.get("income_stability", {}).get("stable")
            })
        
        # Data availability
        data_availability = comprehensive_analysis.get("data_availability", {})
        if data_availability:
            additional_attrs.update({
                "total_tax_years": data_availability.get("total_tax_years"),
                "years_with_wi_data": len(data_availability.get("wi_years", [])),
                "years_with_at_data": len(data_availability.get("at_years", [])),
                "data_completeness_percentage": data_availability.get("data_completeness", 0)
            })
        
        # TP/S analysis
        tps_analysis = comprehensive_analysis.get("tps_analysis", {})
        if tps_analysis:
            owner_breakdown = tps_analysis.get("owner_breakdown", {})
            additional_attrs.update({
                "has_tp_data": "TP" in [owner for year_data in owner_breakdown.values() for owner in year_data.keys()],
                "has_spouse_data": "S" in [owner for year_data in owner_breakdown.values() for owner in year_data.keys()],
                "filing_status_changes": len(tps_analysis.get("filing_status_analysis", {}))
            })
        
        # Summary metrics
        summary = comprehensive_analysis.get("summary", {})
        if summary:
            additional_attrs.update({
                "total_forms_processed": summary.get("total_forms_processed"),
                "compliance_score": summary.get("compliance_score"),
                "data_completeness": summary.get("data_completeness")
            })
        
    except Exception as e:
        logger.warning(f"⚠️ Error extracting additional attributes: {str(e)}")
        additional_attrs["error"] = str(e)
    
    return additional_attrs

# --- API Info/Discovery Endpoint ---

@router.get("/info", tags=["Info"])
def get_api_info():
    """
    API metadata and grouped endpoint discovery for clients.
    """
    has_cookies = cookies_exist()
    cookies = get_cookies() if has_cookies else []
    
    return {
        "message": "Case Management API Backend",
        "version": "1.0.0",
        "environment": os.environ.get("NODE_ENV", "development"),
        "authentication": "Authenticated" if has_cookies else "Not authenticated",
        "cookieCount": len(cookies) if has_cookies else 0,
        "endpoints": {
            "auth": {
                "login": "POST /login",
                "status": "GET /auth/status",
                "logout": "POST /auth/logout"
            },
            "transcripts": {
                "wi_list": "GET /transcripts/wi/{case_id}",
                "at_list": "GET /transcripts/at/{case_id}",
                "wi_raw": "GET /raw/wi/{case_id}",
                "at_raw": "GET /raw/at/{case_id}",
                "wi_download": "GET /download/wi/{case_id}/{case_document_id}",
                "at_download": "GET /download/at/{case_id}/{case_document_id}",
                "wi_parse": "GET /parse/wi/{case_id}/{case_document_id}",
                "at_parse": "GET /parse/at/{case_id}/{case_document_id}"
            },
            "analysis": {
                "comprehensive": "GET /analysis/{case_id}",
                "auto": "GET /analysis/{case_id}/auto",
                "client_analysis": "GET /client-analysis/{case_id}",
                "pricing_model": "GET /pricing-model/{case_id}",
                "case_attributes_v1": "GET /case-attributesv1/{case_id}"
            },
            "health": {
                "health_check": "GET /"
            }
        },
        "usage": {
            "authenticate": "POST /login with username/password",
            "get_wi_transcripts": "GET /transcripts/wi/{case_id}",
            "get_at_transcripts": "GET /transcripts/at/{case_id}",
            "get_case_attributes": "GET /case-attributesv1/{case_id}"
        },
        "setup": "Use the frontend to authenticate with your Logiqs credentials"
    }

# --- Tax Investigation Endpoints (using correct TI file grid) ---

@router.get("/tax-investigation/files/{case_id}", tags=["Tax Investigation"])
def get_ti_files(case_id: str):
    """
    Get list of Tax Investigation (TI) files available for a case.
    Returns metadata about available TI files without parsing them.
    """
    logger.info(f"🔍 Received TI files request for case_id: {case_id}")
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    cookies = get_cookies()
    try:
        from app.services.wi_service import fetch_ti_file_grid
        ti_files = fetch_ti_file_grid(case_id, cookies)
        if not ti_files:
            raise HTTPException(status_code=404, detail="404: No TI files found for this case.")
        response = {
            "case_id": case_id,
            "transcript_type": "TI",
            "total_files": len(ti_files),
            "files": ti_files
        }
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching TI files for case_id {case_id}: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/tax-investigation/raw/{case_id}", tags=["Tax Investigation"])
def get_ti_raw_data(case_id: str):
    """
    Get raw extracted text from the most recent standalone TI file for the case.
    Returns the file metadata and the extracted text (no summary or parsing yet).
    """
    logger.info(f"🔍 Received raw TI data request for case_id: {case_id}")
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    cookies = get_cookies()
    try:
        from app.services.wi_service import fetch_ti_file_grid, download_wi_pdf
        from app.utils.pdf_utils import extract_text_from_pdf
        ti_files = fetch_ti_file_grid(case_id, cookies)
        logger.info(f"🔍 TI files found: {ti_files}")
        if not ti_files:
            logger.warning(f"⚠️ No TI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="404: No TI files found for this case.")
        # Use the most recent TI file (by filename sort)
        ti_files_sorted = sorted(ti_files, key=lambda x: x.get('FileName', ''), reverse=True)
        most_recent = ti_files_sorted[0]
        logger.info(f"🔍 Most recent TI file selected: {most_recent}")
        pdf_bytes = download_wi_pdf(most_recent['CaseDocumentID'], case_id, cookies)
        if not pdf_bytes:
            logger.warning(f"⚠️ Most recent TI file not found or empty for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="Most recent TI file not found or empty")
        text = extract_text_from_pdf(pdf_bytes)
        logger.info(f"🔍 Extracted text length: {len(text) if text else 0}")
        return {
            "case_id": case_id,
            "file": most_recent,
            "raw_text": text
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting raw TI data for case_id {case_id}: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def parse_ti_text_to_structured(ti_text: str, filename: str = "") -> Dict[str, Any]:
    """
    Parse the raw TI text into a comprehensive structured dictionary.
    Extracts detailed case metadata, tax years, resolution plans, compliance requirements, etc.
    Parses by TI version from filename for better accuracy.
    """
    logger.info(f"🔍 Starting comprehensive TI text parsing...")
    result = {}
    
    # Extract TI version from filename
    ti_version = None
    if filename:
        logger.info(f"🔍 Extracting version from filename: '{filename}'")
        
        # Try multiple patterns
        patterns = [
            r"TI\s+(\d+\.\d+)",
            r"TI\s*(\d+)\.(\d+)",
            r"TI\s*(\d+\.\d+)"
        ]
        
        for i, pattern in enumerate(patterns):
            logger.info(f"🔍 Trying pattern {i+1}: {pattern}")
            version_match = re.search(pattern, filename, re.IGNORECASE)
            if version_match:
                if len(version_match.groups()) == 2:
                    ti_version = f"{version_match.group(1)}.{version_match.group(2)}"
                else:
                    ti_version = version_match.group(1)
                logger.info(f"✅ Version extracted with pattern {i+1}: {ti_version}")
                break
            else:
                logger.info(f"❌ Pattern {i+1} failed")
        
        if not ti_version:
            logger.warning(f"⚠️ Could not extract version from filename: {filename}")
    
    logger.info(f"📋 Final TI Version: {ti_version} from filename: {filename}")
    
    # === CASE METADATA ===
    case_metadata = {}
    
    # Case ID - handle both formats
    case_match = re.search(r"Case\s*#\s*(\d+)", ti_text, re.IGNORECASE)
    if case_match:
        case_metadata["case_id"] = case_match.group(1)
    
    # File info (from the endpoint context)
    case_metadata["file_info"] = {
        "filename": filename,
        "case_document_id": 0,  # Will be set by endpoint
        "file_comment": "",
        "ti_version": ti_version
    }
    
    # Investigation dates - handle both formats
    investigation_dates = {}
    
    # Common date patterns for all versions
    ti_completed_match = re.search(r"Date\s+TI\s+Completed\s+(\d{1,2}\/\d{1,2}\/\d{4})", ti_text, re.IGNORECASE)
    if ti_completed_match:
        investigation_dates["ti_completed"] = ti_completed_match.group(1)
    
    resolution_completed_match = re.search(r"Date\s+RESO\s+Plan\s+Completed:\s*(\d{1,2}\/\d{1,2}\/\d{4})", ti_text, re.IGNORECASE)
    if resolution_completed_match:
        investigation_dates["resolution_plan_completed"] = resolution_completed_match.group(1)
    
    if investigation_dates:
        case_metadata["investigation_dates"] = investigation_dates
    
    # Personnel - handle both formats
    personnel = {}
    
    # Common personnel patterns for all versions
    investigator_match = re.search(r"Opening\s+Investigator\s+([A-Za-z\s]+?)(?=\s+Resolution|$)", ti_text, re.IGNORECASE)
    if investigator_match:
        personnel["opening_investigator"] = investigator_match.group(1).strip()
    
    resolution_completer_match = re.search(r"Resolution\s+Plan\s+Completed\s+by:\s*([A-Za-z\s]+?)(?=\s+|$)", ti_text, re.IGNORECASE)
    if resolution_completer_match:
        personnel["resolution_plan_completed_by"] = resolution_completer_match.group(1).strip()
    
    settlement_officer_match = re.search(r"Settlement\s+Officer:\s*([A-Za-z\s]+?)(?=\s+|$)", ti_text, re.IGNORECASE)
    if settlement_officer_match:
        personnel["settlement_officer"] = settlement_officer_match.group(1).strip()
    
    if personnel:
        case_metadata["personnel"] = personnel
    
    # TRA Code
    tra_code_match = re.search(r"TRA\s+Code:\s*([A-Z0-9]+)", ti_text, re.IGNORECASE)
    if tra_code_match:
        case_metadata["tra_code"] = tra_code_match.group(1)
    
    if case_metadata:
        result["case_metadata"] = case_metadata
    
    # === CLIENT INFORMATION ===
    client_name_match = re.search(r"Client\s+Name\s+([A-Za-z\s]+?)(?=\s+Current|$)", ti_text, re.IGNORECASE)
    if client_name_match:
        result["client_information"] = {
            "name": client_name_match.group(1).strip()
        }
    
    # === TAX LIABILITY SUMMARY ===
    tax_liability_summary = {}
    
    # Common liability patterns for all versions
    current_liability_match = re.search(r"Current\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
    if current_liability_match:
        tax_liability_summary["current_tax_liability"] = float(current_liability_match.group(1).replace(",", ""))
    
    # Version-specific liability parsing
    if ti_version and float(ti_version) <= 3.0:
        # Old format: "Current & Projected Tax Liability $6,446.64"
        projected_liability_match = re.search(r"Current\s+&\s+Projected\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if projected_liability_match:
            tax_liability_summary["current_and_projected_tax_liability"] = float(projected_liability_match.group(1).replace(",", ""))
        
        # Old format: "Total Current Balance $0.00"
        total_balance_match = re.search(r"Total\s+Current\s+Balance\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if total_balance_match:
            tax_liability_summary["total_individual_balance"] = float(total_balance_match.group(1).replace(",", ""))
        
        # Old format: "Projected Unfiled Balances: $6,446.64"
        unfiled_match = re.search(r"Projected\s+Unfiled\s+Balances:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if unfiled_match:
            tax_liability_summary["projected_unfiled_balances"] = float(unfiled_match.group(1).replace(",", ""))
    elif ti_version and float(ti_version) >= 6.0:
        # New format patterns
        projected_match = re.search(r"Current\s+and\s+Projected\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if projected_match:
            tax_liability_summary["current_and_projected_tax_liability"] = float(projected_match.group(1).replace(",", ""))
        
        total_balance_match = re.search(r"Total\s+Individual\s+Balance\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if total_balance_match:
            tax_liability_summary["total_individual_balance"] = float(total_balance_match.group(1).replace(",", ""))
        
        unfiled_match = re.search(r"Projected\s+Unfiled\s+Balances\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if unfiled_match:
            tax_liability_summary["projected_unfiled_balances"] = float(unfiled_match.group(1).replace(",", ""))
    else:
        # Unknown version - try common patterns
        projected_match = re.search(r"Current\s+(?:and|&)\s+Projected\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if projected_match:
            tax_liability_summary["current_and_projected_tax_liability"] = float(projected_match.group(1).replace(",", ""))
    
    # Resolution fees - both formats
    fees_match = re.search(r"Total\s+Resolution\s+Fees\s+\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
    if fees_match:
        tax_liability_summary["total_resolution_fees"] = float(fees_match.group(1).replace(",", ""))
    
    if tax_liability_summary:
        result["tax_liability_summary"] = tax_liability_summary
    
    # === INTEREST CALCULATIONS ===
    interest_calculations = {}
    
    daily_interest_match = re.search(r"Daily:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
    if daily_interest_match:
        interest_calculations["daily_interest"] = float(daily_interest_match.group(1).replace(",", ""))
    
    monthly_interest_match = re.search(r"Monthly:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
    if monthly_interest_match:
        interest_calculations["monthly_interest"] = float(monthly_interest_match.group(1).replace(",", ""))
    
    yearly_interest_match = re.search(r"Yearly:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
    if yearly_interest_match:
        interest_calculations["yearly_interest"] = float(yearly_interest_match.group(1).replace(",", ""))
    
    if interest_calculations:
        result["interest_calculations"] = interest_calculations
    
    # === TAX YEARS ===
    tax_years = []
    
    if ti_version and float(ti_version) <= 3.0:
        # Old format: table-style parsing
        # Look for patterns like: "2020 Unfiled $0.00W-2 1099-MISC 1099-R 1099-B"
        old_year_pattern = r"(\d{4})\s+(Filed|Unfiled)\s+([A-Za-z]*)\s*\$?([\d,]+\.?\d*|-[\d,]+\.?\d*)\s*([A-Z0-9\-\s]+?)(?=\d{4}|$)"
        old_year_matches = re.finditer(old_year_pattern, ti_text, re.IGNORECASE)
        
        for match in old_year_matches:
            year_data = {
                "year": int(match.group(1)),
                "return_status": match.group(2),
                "filing_status": match.group(3) if match.group(3) else None,
                "current_balance": match.group(4),
                "csed_date": None,
                "reason_status": None,
                "legal_action": None,
                "projected_balance": None,
                "wage_information": []
            }
            
            # Convert balance to float if it's a number
            if year_data["current_balance"] != "Refund":
                try:
                    year_data["current_balance"] = float(year_data["current_balance"].replace(",", ""))
                except ValueError:
                    pass
            
            # Extract wage information from the forms section
            forms_text = match.group(5)
            wage_forms = re.findall(r"\b(W-2[A-Z]*|1099-[A-Z]+(?:credit)?|SSA|401K|W-2G)\b", forms_text, re.IGNORECASE)
            year_data["wage_information"] = list(set(wage_forms))
            
            tax_years.append(year_data)
    elif ti_version and float(ti_version) >= 6.0:
        # New format parsing
        year_pattern = r"(\d{4})\s+(Filed|Unfiled|Amended)\s+([A-Z]{0,3})\s+\$?([\d,]+\.?\d*|Refund)\s*(\d{1,2}\/\d{1,2}\/\d{4})?\s*([^$\d]*?)(?=\$|W-2|1099|\s*$)"
        year_matches = re.finditer(year_pattern, ti_text, re.IGNORECASE)
        
        for match in year_matches:
            year_data = {
                "year": int(match.group(1)),
                "return_status": match.group(2),
                "filing_status": match.group(3) if match.group(3) else None,
                "current_balance": match.group(4),
                "csed_date": match.group(5),
                "reason_status": match.group(6).strip() if match.group(6) else None,
                "legal_action": None,
                "projected_balance": None,
                "wage_information": []
            }
            
            # Convert balance to float if it's a number
            if year_data["current_balance"] != "Refund":
                try:
                    year_data["current_balance"] = float(year_data["current_balance"].replace(",", ""))
                except ValueError:
                    pass
            
            # Extract wage information for this year
            year_start = match.end()
            year_end = len(ti_text)
            
            # Find next year or end of text
            next_year_match = re.search(rf"\d{{4}}\s+(Filed|Unfiled|Amended)", ti_text[year_start:])
            if next_year_match:
                year_end = year_start + next_year_match.start()
            
            year_text = ti_text[year_start:year_end]
            wage_forms = re.findall(r"\b(W-2[A-Z]*|1099-[A-Z]+(?:credit)?|SSA|401K|W-2G)\b", year_text, re.IGNORECASE)
            year_data["wage_information"] = list(set(wage_forms))
            
            tax_years.append(year_data)
    else:
        # Unknown version - add placeholder
        result["parsing_note"] = f"TI version {ti_version} parsing not implemented. Please add parsing details for this version."
        logger.warning(f"⚠️ Unknown TI version {ti_version} - parsing incomplete")
    
    # Sort by year descending
    tax_years.sort(key=lambda x: x["year"], reverse=True)
    
    if tax_years:
        result["tax_years"] = tax_years
    
    # === RESOLUTION PLAN ===
    resolution_plan = {"steps": [], "resolution_opportunities": [], "special_notes": []}
    
    if ti_version and float(ti_version) <= 3.0:
        # Old format: "List of Services" style
        # Look for patterns like: "Tax Prep W2 3 Penalty Abatement 1$2,500.00Tax Prep 1099 1 Currently Non Collectable 1"
        services_pattern = r"([A-Za-z\s]+)\s+(\d+)\s+([A-Za-z\s]+)\s+(\d+)"
        services_matches = re.finditer(services_pattern, ti_text, re.IGNORECASE)
        
        step_number = 1
        for match in services_matches:
            service1 = match.group(1).strip()
            quantity1 = match.group(2)
            service2 = match.group(3).strip()
            quantity2 = match.group(4)
            
            step_data = {
                "step": step_number,
                "code": service1.upper().replace(" ", ""),
                "description": service1,
                "timeframe": f"{quantity1} units",
                "required_completion_date": None,
                "details": f"{service1} ({quantity1} units), {service2} ({quantity2} units)"
            }
            resolution_plan["steps"].append(step_data)
            step_number += 1
        
        # Extract resolution opportunities from old format
        opportunities = re.findall(r"\b(Currently Non Collectable|CNC|Penalty Abatement|PA)\b", ti_text, re.IGNORECASE)
        resolution_plan["resolution_opportunities"] = list(set(opportunities))
        
        # Extract notes from old format
        notes_section = re.search(r"Notes:\s*(.*?)(?=\n\n|$)", ti_text, re.DOTALL | re.IGNORECASE)
        if notes_section:
            notes_text = notes_section.group(1).strip()
            # Split into bullet points or sentences
            notes = re.split(r'\.\s+', notes_text)
            resolution_plan["special_notes"] = [note.strip() for note in notes if len(note.strip()) > 10]
    elif ti_version and float(ti_version) >= 6.0:
        # New format parsing
        step_pattern = r"(\d+)\s+([A-Z\s\-]+?)\s+([A-Za-z\s\-]+?)\s+(\d+(?:\s*[-–]\s*\d+)?\s*months?|N\/A)"
        step_matches = re.finditer(step_pattern, ti_text, re.IGNORECASE)
        
        for match in step_matches:
            step_data = {
                "step": int(match.group(1)),
                "code": match.group(2).strip(),
                "description": match.group(3).strip(),
                "timeframe": match.group(4),
                "required_completion_date": None,
                "details": ""
            }
            
            # Try to extract details for this step
            step_start = match.end()
            step_end = len(ti_text)
            
            # Find next step or end of text
            next_step_match = re.search(rf"\d+\s+[A-Z\s\-]+?\s+[A-Za-z\s\-]+?\s+(\d+(?:\s*[-–]\s*\d+)?\s*months?|N\/A)", ti_text[step_start:])
            if next_step_match:
                step_end = step_start + next_step_match.start()
            
            step_text = ti_text[step_start:step_end]
            if step_text.strip():
                details = step_text.strip()
                details = re.sub(r'\s+', ' ', details)
                step_data["details"] = details[:500]
            
            resolution_plan["steps"].append(step_data)
        
        # Extract resolution opportunities
        opportunities = re.findall(r"\b(Offer In Compromise|OIC|CNC|PPIA|PENAB|Amended Returns)\b", ti_text, re.IGNORECASE)
        resolution_plan["resolution_opportunities"] = list(set(opportunities))
        
        # Extract special notes
        notes_pattern = r"•\s*([^•\n]+)|^\d+\.\s*([^\n]+)"
        notes_matches = re.finditer(notes_pattern, ti_text, re.MULTILINE)
        for match in notes_matches:
            note = match.group(1) or match.group(2)
            if note and len(note.strip()) > 10:
                resolution_plan["special_notes"].append(note.strip())
    else:
        # Unknown version - add placeholder
        resolution_plan["parsing_note"] = f"Resolution plan parsing for TI version {ti_version} not implemented."
    
    if resolution_plan["steps"] or resolution_plan["resolution_opportunities"] or resolution_plan["special_notes"]:
        result["resolution_plan"] = resolution_plan
    
    # === COMPLIANCE REQUIREMENTS ===
    compliance_requirements = {}
    
    # Unfiled returns
    unfiled_years = []
    for year_data in tax_years:
        if year_data["return_status"] == "Unfiled":
            unfiled_years.append(str(year_data["year"]))
    
    if unfiled_years:
        compliance_requirements["unfiled_returns"] = unfiled_years
    
    # Potential amendments
    amendment_years = []
    for year_data in tax_years:
        if year_data["return_status"] == "Amended":
            amendment_years.append(str(year_data["year"]))
    
    if amendment_years:
        compliance_requirements["potential_amendments"] = amendment_years
    
    # Withholding adjustments
    if re.search(r"withholding|W/H", ti_text, re.IGNORECASE):
        compliance_requirements["withholding_adjustments_needed"] = True
    
    # Financial documentation
    if re.search(r"financial|documentation|OIC", ti_text, re.IGNORECASE):
        compliance_requirements["financial_documentation_required"] = True
    
    if compliance_requirements:
        result["compliance_requirements"] = compliance_requirements
    
    # === RISKS AND WARNINGS ===
    risks_and_warnings = {}
    
    # Ongoing interest accrual
    if re.search(r"interest.*accru|daily.*interest", ti_text, re.IGNORECASE):
        risks_and_warnings["ongoing_interest_accrual"] = True
    
    # Potential penalties
    penalties = re.findall(r"(\d+(?:\.\d+)?%)\s*penalty", ti_text, re.IGNORECASE)
    if penalties:
        risks_and_warnings["potential_penalties"] = [f"{penalty} penalty" for penalty in penalties]
    
    # Resolution nullification risk
    nullification_match = re.search(r"resolution.*null.*void", ti_text, re.IGNORECASE)
    if nullification_match:
        risks_and_warnings["resolution_nullification_risk"] = "If IRS assesses additional taxes after resolution completion"
    
    if risks_and_warnings:
        result["risks_and_warnings"] = risks_and_warnings
    
    logger.info(f"✅ Comprehensive TI parsing completed. Found {len(result)} main sections")
    logger.info(f"   📅 Tax years: {len(tax_years)}")
    logger.info(f"   📋 Resolution steps: {len(resolution_plan.get('steps', []))}")
    logger.info(f"   ⚠️ Compliance issues: {len(compliance_requirements)}")
    logger.info(f"   🔍 TI Version: {ti_version}")
    
    return result

@router.get("/tax-investigation/parse/{case_id}", tags=["Tax Investigation"])
def parse_ti_file_structured(case_id: str):
    """
    Parse the most recent TI file for the given case_id and return a structured summary.
    """
    logger.info(f"🔍 Received TI structured parse request for case_id: {case_id}")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch TI file grid and get the most recent TI file
        logger.info(f"📋 Fetching TI file grid for case_id: {case_id}")
        ti_files = fetch_ti_file_grid(case_id, cookies)
        if not ti_files:
            logger.error(f"❌ No TI files found for case_id: {case_id}")
            raise HTTPException(status_code=404, detail="No TI files found for this case.")
        
        ti_file = ti_files[0]  # Most recent
        logger.info(f"📄 Processing TI file: {ti_file['FileName']} (ID: {ti_file['CaseDocumentID']})")
        
        # Download PDF
        logger.info(f"📥 Downloading TI PDF...")
        pdf_bytes = download_wi_pdf(ti_file["CaseDocumentID"], case_id, cookies)
        if not pdf_bytes:
            logger.error(f"❌ No PDF content received for TI file")
            raise HTTPException(status_code=404, detail="TI PDF file not found or empty")
        
        logger.info(f"📊 PDF downloaded successfully ({len(pdf_bytes)} bytes)")
        
        # Extract text
        logger.info(f"📝 Extracting text from TI PDF...")
        ti_text = extract_text_from_pdf(pdf_bytes)
        if not ti_text:
            logger.error(f"❌ No text extracted from TI PDF")
            raise HTTPException(status_code=500, detail="Could not extract text from TI PDF.")
        
        logger.info(f"📝 Extracted {len(ti_text)} characters from TI PDF")
        logger.info(f"📄 First 200 chars: {ti_text[:200]}...")
        
        # Parse to structured format
        logger.info(f"🔍 Parsing TI text to structured format...")
        structured = parse_ti_text_to_structured(ti_text)
        
        # Set file info in case metadata
        if "case_metadata" in structured:
            structured["case_metadata"]["file_info"] = {
                "filename": ti_file["FileName"],
                "case_document_id": ti_file["CaseDocumentID"],
                "file_comment": ti_file.get("FileComment", "")
            }
        else:
            # If no case_metadata was found, create it
            structured["case_metadata"] = {
                "case_id": case_id,
                "file_info": {
                    "filename": ti_file["FileName"],
                    "case_document_id": ti_file["CaseDocumentID"],
                    "file_comment": ti_file.get("FileComment", "")
                }
            }
        
        # Log what was found
        logger.info(f"✅ TI parsing completed successfully")
        if "tax_years" in structured:
            logger.info(f"   📅 Tax years found: {len(structured['tax_years'])}")
        if "tax_liability_summary" in structured:
            logger.info(f"   💰 Tax liability summary: {structured['tax_liability_summary']}")
        if "resolution_plan" in structured:
            logger.info(f"   📋 Resolution steps: {len(structured['resolution_plan'].get('steps', []))}")
        if "compliance_requirements" in structured:
            logger.info(f"   ⚠️ Compliance requirements: {structured['compliance_requirements']}")
        
        return structured
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing TI file for case_id {case_id}: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/tax-investigation/compare/{case_id}", tags=["Tax Investigation"])
def compare_ti_with_wi_at(case_id: str):
    """
    Compare TI parsed data with WI/AT data side-by-side.
    Shows discrepancies, income comparisons, and other relevant analysis.
    """
    logger.info(f"🔍 Received TI comparison request for case_id: {case_id}")
    
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get TI data
        logger.info(f"📋 Fetching TI data for comparison...")
        ti_files = fetch_ti_file_grid(case_id, cookies)
        if not ti_files:
            raise HTTPException(status_code=404, detail="No TI files found for this case.")
        
        ti_file = ti_files[0]
        pdf_bytes = download_wi_pdf(ti_file["CaseDocumentID"], case_id, cookies)
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="TI PDF file not found or empty")
        
        ti_text = extract_text_from_pdf(pdf_bytes)
        if not ti_text:
            raise HTTPException(status_code=500, detail="Could not extract text from TI PDF.")
        
        ti_data = parse_ti_text_to_structured(ti_text, ti_file["FileName"])
        
        # Set file info
        if "case_metadata" in ti_data:
            ti_data["case_metadata"]["file_info"] = {
                "filename": ti_file["FileName"],
                "case_document_id": ti_file["CaseDocumentID"],
                "file_comment": ti_file.get("FileComment", "")
            }
        
        # Get WI data
        logger.info(f"📋 Fetching WI data for comparison...")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        wi_data = None
        if wi_files:
            wi_data = parse_wi_pdfs(wi_files, cookies, case_id, include_tps_analysis=True)
        
        # Get AT data
        logger.info(f"📋 Fetching AT data for comparison...")
        at_files = fetch_at_file_grid(case_id, cookies)
        at_data = None
        if at_files:
            at_data = parse_at_pdfs(at_files, cookies, case_id, include_tps_analysis=True)
        
        # Build comparison
        comparison = {
            "case_id": case_id,
            "ti_data": ti_data,
            "wi_data": wi_data,
            "at_data": at_data,
            "comparisons": {}
        }
        
        # === TAX LIABILITY COMPARISON ===
        tax_liability_comparison = {}
        
        if "tax_liability_summary" in ti_data:
            ti_liability = ti_data["tax_liability_summary"].get("current_tax_liability")
            if ti_liability:
                tax_liability_comparison["ti_current_liability"] = ti_liability
                
                # Compare with AT data if available
                if at_data:
                    at_total_balance = 0
                    for at_record in at_data:
                        if isinstance(at_record, dict) and "transactions" in at_record:
                            for transaction in at_record["transactions"]:
                                if transaction.get("type") == "Balance Due":
                                    at_total_balance += abs(float(transaction.get("amount", 0)))
                    
                    if at_total_balance > 0:
                        tax_liability_comparison["at_total_balance"] = at_total_balance
                        tax_liability_comparison["difference"] = ti_liability - at_total_balance
                        tax_liability_comparison["percentage_difference"] = ((ti_liability - at_total_balance) / ti_liability) * 100 if ti_liability > 0 else 0
        
        if tax_liability_comparison:
            comparison["comparisons"]["tax_liability"] = tax_liability_comparison
        
        # === TAX YEARS COMPARISON ===
        tax_years_comparison = {}
        
        if "tax_years" in ti_data:
            ti_years = {year["year"]: year for year in ti_data["tax_years"]}
            tax_years_comparison["ti_years"] = list(ti_years.keys())
            
            # Compare with WI years
            if wi_data and "years" in wi_data:
                wi_years = list(wi_data["years"].keys())
                tax_years_comparison["wi_years"] = wi_years
                tax_years_comparison["common_years"] = list(set(ti_years.keys()) & set(wi_years))
                tax_years_comparison["ti_only_years"] = list(set(ti_years.keys()) - set(wi_years))
                tax_years_comparison["wi_only_years"] = list(set(wi_years) - set(ti_years.keys()))
            
            # Compare with AT years
            if at_data:
                at_years = []
                for at_record in at_data:
                    if isinstance(at_record, dict) and "tax_year" in at_record:
                        at_years.append(at_record["tax_year"])
                
                tax_years_comparison["at_years"] = at_years
                tax_years_comparison["ti_at_common_years"] = list(set(ti_years.keys()) & set(at_years))
        
        if tax_years_comparison:
            comparison["comparisons"]["tax_years"] = tax_years_comparison
        
        # === FILING STATUS COMPARISON ===
        filing_status_comparison = {}
        
        if "tax_years" in ti_data:
            ti_filing_statuses = {}
            for year_data in ti_data["tax_years"]:
                if year_data["filing_status"]:
                    ti_filing_statuses[year_data["year"]] = year_data["filing_status"]
            
            filing_status_comparison["ti_filing_statuses"] = ti_filing_statuses
            
            # Compare with WI filing statuses
            if wi_data and "years" in wi_data:
                wi_filing_statuses = {}
                for year, year_data in wi_data["years"].items():
                    if "filing_status" in year_data:
                        wi_filing_statuses[int(year)] = year_data["filing_status"]
                
                filing_status_comparison["wi_filing_statuses"] = wi_filing_statuses
                
                # Find discrepancies
                discrepancies = []
                for year in set(ti_filing_statuses.keys()) & set(wi_filing_statuses.keys()):
                    if ti_filing_statuses[year] != wi_filing_statuses[year]:
                        discrepancies.append({
                            "year": year,
                            "ti_status": ti_filing_statuses[year],
                            "wi_status": wi_filing_statuses[year]
                        })
                
                if discrepancies:
                    filing_status_comparison["filing_status_discrepancies"] = discrepancies
        
        if filing_status_comparison:
            comparison["comparisons"]["filing_status"] = filing_status_comparison
        
        # === INCOME COMPARISON ===
        income_comparison = {}
        
        if "tax_years" in ti_data and wi_data and "years" in wi_data:
            income_discrepancies = []
            
            for year_data in ti_data["tax_years"]:
                year = year_data["year"]
                if str(year) in wi_data["years"]:
                    wi_year_data = wi_data["years"][str(year)]
                    
                    # Get WI calculated income
                    wi_total_income = 0
                    if "summary" in wi_year_data:
                        wi_total_income = wi_year_data["summary"].get("total_income", 0)
                    
                    # Look for income mentioned in TI for this year
                    # This would need more sophisticated parsing based on your TI format
                    # For now, we'll note the comparison
                    if wi_total_income > 0:
                        income_discrepancies.append({
                            "year": year,
                            "wi_calculated_income": wi_total_income,
                            "ti_income_mentioned": "Not parsed yet",  # Would need TI income parsing
                            "forms_found": year_data.get("wage_information", [])
                        })
            
            if income_discrepancies:
                income_comparison["income_discrepancies"] = income_discrepancies
        
        if income_comparison:
            comparison["comparisons"]["income"] = income_comparison
        
        # === COMPLIANCE COMPARISON ===
        compliance_comparison = {}
        
        if "compliance_requirements" in ti_data:
            ti_compliance = ti_data["compliance_requirements"]
            compliance_comparison["ti_compliance"] = ti_compliance
            
            # Compare with WI/AT findings
            compliance_issues = []
            
            # Check for unfiled returns
            if "unfiled_returns" in ti_compliance:
                compliance_issues.append({
                    "type": "unfiled_returns",
                    "ti_years": ti_compliance["unfiled_returns"],
                    "wi_at_analysis": "Would need WI/AT analysis for missing returns"
                })
            
            # Check for amendments needed
            if "potential_amendments" in ti_compliance:
                compliance_issues.append({
                    "type": "potential_amendments",
                    "ti_years": ti_compliance["potential_amendments"],
                    "wi_at_analysis": "Would need WI/AT analysis for amendment opportunities"
                })
            
            if compliance_issues:
                compliance_comparison["compliance_issues"] = compliance_issues
        
        if compliance_comparison:
            comparison["comparisons"]["compliance"] = compliance_comparison
        
        # === SUMMARY STATISTICS ===
        summary_stats = {
            "ti_tax_years_count": len(ti_data.get("tax_years", [])),
            "wi_tax_years_count": len(wi_data.get("years", {})) if wi_data else 0,
            "at_tax_years_count": len(at_data) if at_data else 0,
            "ti_current_liability": ti_data.get("tax_liability_summary", {}).get("current_tax_liability"),
            "ti_daily_interest": ti_data.get("interest_calculations", {}).get("daily_interest"),
            "resolution_steps_count": len(ti_data.get("resolution_plan", {}).get("steps", [])),
            "resolution_opportunities": ti_data.get("resolution_plan", {}).get("resolution_opportunities", [])
        }
        
        comparison["summary_statistics"] = summary_stats
        
        logger.info(f"✅ TI comparison completed successfully")
        logger.info(f"   📊 Tax liability comparison: {bool(tax_liability_comparison)}")
        logger.info(f"   📅 Tax years comparison: {bool(tax_years_comparison)}")
        logger.info(f"   📋 Filing status comparison: {bool(filing_status_comparison)}")
        logger.info(f"   💰 Income comparison: {bool(income_comparison)}")
        logger.info(f"   ⚠️ Compliance comparison: {bool(compliance_comparison)}")
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing TI with WI/AT for case_id {case_id}: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- Case Closing Notes Endpoint ---

@router.get("/case-closing-notes/{case_id}", tags=["Case Management"])
def get_case_closing_notes(case_id: str):
    """
    Get case closing notes from activity data.
    Extracts resolution details from activities with "Closing Notes" subject.
    """
    logger.info(f"🔍 Received case closing notes request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch activity data from Logiqs API
        activity_data = fetch_case_activity(case_id, cookies)
        
        # Extract closing notes
        closing_notes = extract_closing_notes(activity_data)
        
        if not closing_notes:
            logger.info(f"ℹ️ No closing notes found for case_id: {case_id}")
            response = {
                "case_id": case_id,
                "has_closing_notes": False,
                "closing_notes": [],
                "resolution_summary": None
            }
            logger.info("Case Closing Notes Response: " + json.dumps(response, indent=2))
            return response
        
        # Parse resolution details
        resolution_summary = parse_resolution_details(closing_notes)
        
        response = {
            "case_id": case_id,
            "has_closing_notes": True,
            "closing_notes": closing_notes,
            "resolution_summary": resolution_summary
        }
        logger.info("Case Closing Notes Response: " + json.dumps(response, indent=2))
        logger.info(f"✅ Successfully extracted closing notes for case_id: {case_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting case closing notes for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def fetch_case_activity(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch case activity data from Logiqs API.
    """
    logger.info(f"📡 Fetching activity data for case_id: {case_id}")
    
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = f"https://tps.logiqs.com/publicapi/2020-02-22/cases/activity?apikey=4917fa0ce4694529a9b97ead1a60c932&CaseID={case_id}"
    logger.info(f"🌐 Making API request to: {url}")
    
    headers = {
        "Accept": "application/json",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }

    try:
        response = httpx.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Response status: {response.status_code}")
        response.raise_for_status()
        
        activity_data = response.json()
        logger.info(f"✅ Successfully fetched {len(activity_data)} activity records")
        
        return activity_data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching case activity: {str(e)}")
        raise Exception(f"Error fetching case activity: {str(e)}")

def extract_closing_notes(activity_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract activities with "Closing Notes" subject using flexible regex matching.
    """
    logger.info("🔍 Extracting closing notes from activity data")
    
    closing_notes = []
    
    # Flexible regex patterns for "Closing Notes" subject
    closing_patterns = [
        r'closing\s+notes',
        r'closing\s+note',
        r'case\s+closing',
        r'resolution\s+notes',
        r'closing\s+summary'
    ]
    
    for activity in activity_data:
        if not isinstance(activity, dict):
            continue
            
        subject = activity.get("Subject", "")
        comment = activity.get("Comment", "")
        activity_type = activity.get("ActivityType", "")
        created_date = activity.get("CreatedDate", "")
        
        # Check if subject matches any closing pattern (case insensitive)
        is_closing_note = False
        for pattern in closing_patterns:
            if re.search(pattern, subject, re.IGNORECASE):
                is_closing_note = True
                break
        
        if is_closing_note and comment:
            logger.info(f"✅ Found closing note: {subject}")
            closing_notes.append({
                "activity_id": activity.get("ActivityID"),
                "subject": subject,
                "comment": comment,
                "activity_type": activity_type,
                "created_date": created_date,
                "pin": activity.get("Pin", False)
            })
    
    logger.info(f"✅ Extracted {len(closing_notes)} closing notes")
    return closing_notes

def parse_resolution_details(closing_notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Parse resolution details from closing notes.
    """
    logger.info("🔍 Parsing resolution details from closing notes")
    
    resolution_summary = {
        "resolution_type": None,
        "resolution_amount": None,
        "payment_terms": None,
        "user_fee": None,
        "start_date": None,
        "tax_years": [],
        "lien_status": None,
        "account_balance": None,
        "penalty_abatement": None,
        "additional_notes": []
    }
    
    for note in closing_notes:
        comment = note.get("comment", "")
        
        # --- Resolution Type Detection ---
        # Patterns for explicit types
        resolution_patterns = {
            "IA": r'\b(?:IA|Installment\s+Agreement)\b',
            "PPIA": r'\b(?:PPIA|Partial\s+Payment\s+Installment\s+Agreement)\b',
            "CNC": r'\b(?:CNC|Currently\s+Not\s+Collectible|Currently\s+Non\s+Collectible)\b',
            "FA": r'\b(?:FA|Fresh\s+Start)\b',
            "FPA": r'\b(?:Full\s+Payment\s+Agreement|Pay\s*In\s*Full|PIF)\b',
        }
        found_type = None
        for res_type, pattern in resolution_patterns.items():
            if re.search(pattern, comment, re.IGNORECASE):
                found_type = res_type
                break
        # OIC: Only if not negated
        if re.search(r'\b(OIC|Offer\s+in\s+Compromise)\b', comment, re.IGNORECASE):
            if not re.search(r'(no\s+OIC|not\s+OIC|OIC\s+not|ineligible\s+for\s+OIC|OIC\s+not\s+done|OIC\s+Review:\s*Waived|No\s+OIC\s+Option)', comment, re.IGNORECASE):
                found_type = "OIC"
        # Paid In Full: If balance is zero, full paid, or similar
        if re.search(r'(paid\s+in\s+full|full\s+paid|balance\s+is\s+0|balance\s+zero|balance\s+below\s+\$?500|no\s+balance\s+owed|client\s+full\s+paid)', comment, re.IGNORECASE):
            found_type = "Paid In Full"
        # No resolution needed/voluntary payment/low balance
        if re.search(r'(no\s+resolution\s+needed|voluntary\s+payment|can\s+make\s+voluntary\s+payments|balance\s+below\s+\$?500|not\s+at\s+risk\s+of\s+levy)', comment, re.IGNORECASE):
            found_type = "No Resolution Needed"
        if found_type:
            resolution_summary["resolution_type"] = found_type
        
        # Prefer payoff amount for account_balance if present
        payoff_match = re.search(r'Payoff\s+Amount:\s*\$?([\d,]+\.?\d*)', comment, re.IGNORECASE)
        if payoff_match:
            payoff_str = payoff_match.group(1).replace(',', '')
            try:
                resolution_summary["account_balance"] = float(payoff_str)
            except ValueError:
                pass
        else:
            # Otherwise, use the largest Total Account Balance found
            balance_matches = re.findall(r'Total\s+Account\s+Balance\s+(?:as\s+of\s+[^:]+)?:\s*\$?([\d,]+\.?\d*)', comment, re.IGNORECASE)
            balances = [float(b.replace(',', '')) for b in balance_matches if b]
            if balances:
                resolution_summary["account_balance"] = max(balances)
        
        # Extract payment amount
        payment_match = re.search(r'Payment\s+Amount:\s*\$?([\d,]+\.?\d*)', comment, re.IGNORECASE)
        if payment_match:
            amount_str = payment_match.group(1).replace(',', '')
            try:
                resolution_summary["resolution_amount"] = float(amount_str)
            except ValueError:
                pass
        
        # Extract user fee
        fee_match = re.search(r'User\s+Fee:\s*\$?([\d,]+\.?\d*)', comment, re.IGNORECASE)
        if fee_match:
            fee_str = fee_match.group(1).replace(',', '')
            try:
                resolution_summary["user_fee"] = float(fee_str)
            except ValueError:
                pass
        
        # Extract start date
        start_match = re.search(r'Starting:\s*(\d{1,2}/\d{1,2}/\d{4})', comment, re.IGNORECASE)
        if start_match:
            resolution_summary["start_date"] = start_match.group(1)
        
        # Extract tax years - enhanced to catch more formats and ranges
        years_match = re.search(r'tax\s+year\(s\):\s*([\d,\s\-]+)', comment, re.IGNORECASE)
        years = []
        if years_match:
            years_str = years_match.group(1)
            # Handle ranges like 2021-2022
            for part in years_str.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = part.split('-')
                    try:
                        start, end = int(start), int(end)
                        for y in range(start, end+1):
                            years.append(str(y))
                    except Exception:
                        continue
                else:
                    year_match = re.match(r'\d{2,4}', part)
                    if year_match:
                        y = year_match.group(0)
                        if len(y) == 2:
                            years.append(f"20{y}")
                        else:
                            years.append(y)
            resolution_summary["tax_years"] = years
        else:
            # Try alternative format like "Includes tax year(s): 22, 23"
            alt_years_match = re.search(r'Includes\s+tax\s+year\(s\):\s*([\d,\s\-]+)', comment, re.IGNORECASE)
            if alt_years_match:
                years_str = alt_years_match.group(1)
                for part in years_str.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = part.split('-')
                        try:
                            start, end = int(start), int(end)
                            for y in range(start, end+1):
                                years.append(str(y))
                        except Exception:
                            continue
                    else:
                        year_match = re.match(r'\d{2,4}', part)
                        if year_match:
                            y = year_match.group(0)
                            if len(y) == 2:
                                years.append(f"20{y}")
                            else:
                                years.append(y)
                resolution_summary["tax_years"] = years
        
        # Extract lien status - enhanced
        if re.search(r'liens?.*not.*filed', comment, re.IGNORECASE) or re.search(r'no.*under.*threshold', comment, re.IGNORECASE):
            resolution_summary["lien_status"] = "No liens filed"
        elif re.search(r'liens?.*filed', comment, re.IGNORECASE):
            resolution_summary["lien_status"] = "Liens filed"
        elif re.search(r'will\s+not\s+be\s+filed', comment, re.IGNORECASE):
            resolution_summary["lien_status"] = "No liens filed"
        
        # Extract payment terms
        terms_match = re.search(r'Payment\s+Due\s+Date:\s*(\d+(?:st|nd|rd|th))', comment, re.IGNORECASE)
        if terms_match:
            resolution_summary["payment_terms"] = f"Due on {terms_match.group(1)} of each month"
        
        # Extract penalty abatement information
        if re.search(r'penalty\s+abatement', comment, re.IGNORECASE):
            if re.search(r'not.*qualify|ineligible|waived', comment, re.IGNORECASE):
                resolution_summary["penalty_abatement"] = "Not qualified/Ineligible"
            elif re.search(r'\$[\d,]+.*abated', comment, re.IGNORECASE):
                abatement_match = re.search(r'\$([\d,]+\.?\d*).*abated', comment, re.IGNORECASE)
                if abatement_match:
                    amount_str = abatement_match.group(1).replace(',', '')
                    try:
                        resolution_summary["penalty_abatement"] = f"${float(amount_str):.2f} abated"
                    except ValueError:
                        resolution_summary["penalty_abatement"] = "Abated"
            elif re.search(r'843.*form', comment, re.IGNORECASE):
                resolution_summary["penalty_abatement"] = "843 form prepared"
            else:
                resolution_summary["penalty_abatement"] = "Applied"
        
        # Also check for penalty abatement amounts mentioned in the comment
        if not resolution_summary["penalty_abatement"]:
            abatement_match = re.search(r'\$([\d,]+\.?\d*).*abated.*from', comment, re.IGNORECASE)
            if abatement_match:
                amount_str = abatement_match.group(1).replace(',', '')
                try:
                    resolution_summary["penalty_abatement"] = f"${float(amount_str):.2f} abated"
                except ValueError:
                    pass
        
        # Extract additional notes
        if re.search(r'client.*full.*paid|balance.*\$0|no.*balance.*owed', comment, re.IGNORECASE):
            resolution_summary["additional_notes"].append("Client full paid/zero balance")
        
        if re.search(r'manual.*payments.*until.*433D', comment, re.IGNORECASE):
            resolution_summary["additional_notes"].append("Manual payments until 433D processed")
        
        if re.search(r'client.*to.*full.*pay.*or.*resolve', comment, re.IGNORECASE):
            resolution_summary["additional_notes"].append("Client to full pay or resolve balance")
    
    logger.info(f"✅ Parsed resolution details: {resolution_summary['resolution_type']}")
    return resolution_summary

# --- Case Activities Endpoint ---

@router.get("/caseactivities/{case_id}", tags=["Case Management"])
def get_case_activities(
    case_id: str,
    subject_filter: Optional[str] = Query(None, description="Filter activities by subject (case insensitive)"),
    activity_id: Optional[int] = Query(None, description="Filter by specific activity ID")
):
    """
    Get all case activities from Logiqs API.
    Returns all activities for a case with optional filtering by subject or activity ID.
    """
    logger.info(f"🔍 Received case activities request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch activity data from Logiqs API
        activity_data = fetch_case_activity(case_id, cookies)
        
        # Apply filters if provided
        filtered_activities = []
        for activity in activity_data:
            # Filter by subject if provided
            if subject_filter:
                subject = activity.get("Subject", "")
                if not re.search(subject_filter, subject, re.IGNORECASE):
                    continue
            
            # Filter by activity ID if provided
            if activity_id:
                if activity.get("ActivityID") != activity_id:
                    continue
            
            filtered_activities.append(activity)
        
        logger.info(f"✅ Successfully returned {len(filtered_activities)} activities for case_id: {case_id}")
        return {
            "case_id": case_id,
            "total_activities": len(activity_data),
            "filtered_activities": len(filtered_activities),
            "activities": filtered_activities
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting case activities for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def fetch_case_activity(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch case activity data from Logiqs API.
    """
    logger.info(f"📡 Fetching activity data for case_id: {case_id}")
    
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = f"https://tps.logiqs.com/publicapi/2020-02-22/cases/activity?apikey=4917fa0ce4694529a9b97ead1a60c932&CaseID={case_id}"
    logger.info(f"🌐 Making API request to: {url}")
    
    headers = {
        "Accept": "application/json",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }

    try:
        response = httpx.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Response status: {response.status_code}")
        response.raise_for_status()
        
        activity_data = response.json()
        logger.info(f"✅ Successfully fetched {len(activity_data)} activity records")
        
        return activity_data
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching case activity: {str(e)}")
        raise Exception(f"Error fetching case activity: {str(e)}")

# --- Closing Letter Endpoints ---

@router.get("/closing-letters/files/{case_id}", tags=["Closing Letters"])
def get_closing_letter_files(case_id: str):
    """
    Get closing letter files for a given case from Logiqs.
    Returns a list of closing letter file metadata.
    """
    logger.info(f"🔍 Received closing letter files request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch and filter closing letter files
        closing_letter_files = fetch_closing_letter_file_grid(case_id, cookies)
        if not closing_letter_files:
            raise HTTPException(status_code=404, detail="404: No closing letter files found for this case.")
        
        logger.info(f"✅ Successfully returned {len(closing_letter_files)} closing letter files for case_id: {case_id}")
        return {
            "case_id": case_id,
            "closing_letter_files": closing_letter_files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting closing letter files for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/closing-letters/raw/{case_id}", tags=["Closing Letters"])
def get_closing_letter_raw_data(case_id: str):
    """
    Get raw text from all closing letter files for a case.
    Downloads and extracts text from all closing letter PDFs.
    """
    logger.info(f"🔍 Received closing letter raw data request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch closing letter files
        closing_letter_files = fetch_closing_letter_file_grid(case_id, cookies)
        if not closing_letter_files:
            raise HTTPException(status_code=404, detail="404: No closing letter files found for this case.")
        
        # Download and extract text from all closing letter PDFs
        closing_letter_data = parse_closing_letter_pdfs(closing_letter_files, cookies, case_id)
        
        logger.info(f"✅ Successfully extracted text from {len(closing_letter_files)} closing letter files for case_id: {case_id}")
        return closing_letter_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting closing letter raw data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/download/closing-letter/{case_id}/{case_document_id}", tags=["Closing Letters"])
def download_closing_letter_file(case_id: str, case_document_id: str):
    """
    Download a specific closing letter PDF file by its CaseDocumentID.
    Returns the PDF file as a binary response.
    """
    logger.info(f"📥 Downloading closing letter file - case_id: {case_id}, case_document_id: {case_document_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Download the PDF
        pdf_bytes = download_closing_letter_pdf(case_document_id, case_id, cookies)
        
        if not pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF file not found or empty")
        
        logger.info(f"✅ Successfully downloaded closing letter file. Size: {len(pdf_bytes)} bytes")
        
        # Return PDF as binary response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ClosingLetter_{case_id}_{case_document_id}.pdf"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error downloading closing letter file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def fetch_closing_letter_file_grid(case_id: str, cookies: dict) -> List[Dict[str, Any]]:
    """
    Fetch closing letter file grid for a given case from Logiqs.
    Returns a list of closing letter file metadata dicts.
    """
    logger.info(f"🔍 Starting closing letter file grid fetch for case_id: {case_id}")
    
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = LOGIQS_GRID_URL.format(case_id=case_id)
    logger.info(f"🌐 Making API request to: {url}")
    
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }

    try:
        logger.info("📡 Sending POST request to Logiqs API...")
        response = httpx.post(
            url,
            headers=headers,
            timeout=30,
            follow_redirects=False
        )
        
        logger.info(f"📊 Response status: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        
        if not isinstance(response_data, dict) or "Result" not in response_data:
            logger.error(f"❌ Invalid response structure: {type(response_data)}")
            logger.error(f"📋 Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Not a dict'}")
            raise Exception("Invalid response structure from API")
        
        docs = response_data["Result"]
        logger.info(f"📋 Found {len(docs) if isinstance(docs, list) else 'non-list'} documents in response")
        
        if not isinstance(docs, list):
            logger.error(f"❌ Invalid document list format: {type(docs)}")
            raise Exception("Invalid document list format")
        
        closing_letter_files = []
        logger.info("🔍 Filtering for closing letter files...")
        
        for i, doc in enumerate(docs):
            if not isinstance(doc, dict):
                logger.warning(f"⚠️ Skipping non-dict document at index {i}: {type(doc)}")
                continue
            
            name = doc.get("Name", "")
            if not name:
                logger.warning(f"⚠️ Skipping document with no name at index {i}")
                continue
            
            logger.debug(f"🔍 Checking document: {name}")
            
            # Check for closing letter in the filename (case insensitive)
            if re.search(r'closing\s+letter', name, re.IGNORECASE):
                case_doc_id = doc.get("CaseDocumentID")
                if case_doc_id:
                    closing_letter_files.append({
                        "FileName": name,
                        "CaseDocumentID": case_doc_id
                    })
                    logger.info(f"✅ Found closing letter file: {name} (ID: {case_doc_id})")
                else:
                    logger.warning(f"⚠️ Closing letter file {name} has no CaseDocumentID")
            else:
                logger.debug(f"⏭️ Skipping non-closing letter file: {name}")
        
        logger.info(f"✅ Closing letter file grid fetch completed. Found {len(closing_letter_files)} closing letter files")
        return closing_letter_files
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching closing letter file grid: {str(e)}")
        raise Exception(f"Error fetching closing letter file grid: {str(e)}")

def download_closing_letter_pdf(case_doc_id: str, case_id: str, cookies: dict) -> bytes:
    """
    Download a closing letter PDF file using its CaseDocumentID and case_id.
    Returns PDF bytes.
    """
    logger.info(f"📥 Downloading closing letter PDF - CaseDocumentID: {case_doc_id}, case_id: {case_id}")
    
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for PDF download")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = LOGIQS_DOWNLOAD_URL.format(case_doc_id=case_doc_id, case_id=case_id)
    logger.info(f"🌐 Downloading from: {url}")
    
    headers = {
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }
    
    try:
        logger.info("📡 Sending GET request for PDF...")
        response = httpx.get(
            url,
            headers=headers,
            timeout=30,
            follow_redirects=True
        )
        
        logger.info(f"📊 PDF download response status: {response.status_code}")
        response.raise_for_status()
        
        content = response.content
        logger.info(f"✅ PDF downloaded successfully. Size: {len(content)} bytes")
        
        return content
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error downloading PDF {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error downloading PDF {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error downloading PDF: {str(e)}")
        raise Exception(f"Request error downloading PDF: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error downloading closing letter PDF: {str(e)}")
        raise Exception(f"Error downloading closing letter PDF: {str(e)}")

def parse_closing_letter_pdfs(closing_letter_files: List[Dict[str, Any]], cookies: dict, case_id: str) -> Dict[str, Any]:
    """
    Download and parse all closing letter PDFs for a case.
    Returns extracted text and metadata for each file.
    """
    logger.info(f"🔍 Starting closing letter PDF parsing for case_id: {case_id}")
    
    closing_letter_data = {
        "case_id": case_id,
        "total_files": len(closing_letter_files),
        "files": []
    }
    
    for i, file_info in enumerate(closing_letter_files):
        filename = file_info.get("FileName", f"closing_letter_{i+1}")
        case_doc_id = file_info.get("CaseDocumentID")
        
        logger.info(f"📄 Processing closing letter file {i+1}/{len(closing_letter_files)}: {filename}")
        
        try:
            # Download PDF
            pdf_bytes = download_closing_letter_pdf(case_doc_id, case_id, cookies)
            if not pdf_bytes:
                logger.warning(f"⚠️ No PDF content received for {filename}")
                continue
            
            # Extract text from PDF
            text_content = extract_text_from_pdf(pdf_bytes)
            
            file_data = {
                "filename": filename,
                "case_document_id": case_doc_id,
                "text_content": text_content,
                "text_length": len(text_content) if text_content else 0
            }
            
            closing_letter_data["files"].append(file_data)
            logger.info(f"✅ Successfully parsed {filename} (text length: {len(text_content) if text_content else 0} chars)")
            
        except Exception as e:
            logger.error(f"❌ Error processing closing letter file {filename}: {str(e)}")
            file_data = {
                "filename": filename,
                "case_document_id": case_doc_id,
                "text_content": None,
                "error": str(e)
            }
            closing_letter_data["files"].append(file_data)
    
    logger.info(f"✅ Closing letter PDF parsing completed for case_id: {case_id}")
    return closing_letter_data

@router.get("/closing-letters/parse/{case_id}", tags=["Closing Letters"])
def parse_closing_letter_structured(case_id: str):
    """
    Get structured closing letter data for a case.
    Downloads closing letter PDFs and parses them into structured resolution details.
    """
    logger.info(f"🔍 Received structured closing letter parse request for case_id: {case_id}")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Fetch closing letter files
        closing_letter_files = fetch_closing_letter_file_grid(case_id, cookies)
        if not closing_letter_files:
            raise HTTPException(status_code=404, detail="404: No closing letter files found for this case.")
        
        # Download and parse closing letter PDFs
        closing_letter_data = parse_closing_letter_pdfs(closing_letter_files, cookies, case_id)
        
        # Parse text into structured data
        structured_data = parse_closing_letter_text_to_structured(closing_letter_data)
        
        logger.info(f"✅ Successfully parsed closing letter data for case_id: {case_id}")
        return structured_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error parsing closing letter data for case_id {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def parse_closing_letter_text_to_structured(closing_letter_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse closing letter text into structured resolution details.
    """
    logger.info("🔍 Parsing closing letter text into structured data")
    
    case_id = closing_letter_data.get("case_id")
    files = closing_letter_data.get("files", [])
    
    structured_result = {
        "case_id": case_id,
        "total_files": len(files),
        "resolution_summary": {
            "resolution_type": None,
            "resolution_amount": None,
            "payment_terms": None,
            "user_fee": None,
            "start_date": None,
            "tax_years": [],
            "lien_status": None,
            "account_balance": None,
            "payment_method": None,
            "services_completed": [],
            "additional_terms": []
        },
        "files": []
    }
    
    for file_data in files:
        filename = file_data.get("filename", "")
        text_content = file_data.get("text_content", "")
        
        if not text_content:
            continue
            
        # Parse resolution details from text
        resolution_details = extract_resolution_from_closing_letter(text_content)
        
        # Update main resolution summary (take first non-null values)
        if not structured_result["resolution_summary"]["resolution_type"]:
            structured_result["resolution_summary"].update(resolution_details)
        
        # Add file data with parsed details
        file_structured = {
            "filename": filename,
            "case_document_id": file_data.get("case_document_id"),
            "text_content": text_content,
            "text_length": file_data.get("text_length", 0),
            "parsed_resolution": resolution_details
        }
        
        structured_result["files"].append(file_structured)
    
    logger.info(f"✅ Parsed closing letter data: {structured_result['resolution_summary']['resolution_type']}")
    return structured_result

def extract_resolution_from_closing_letter(text_content: str) -> Dict[str, Any]:
    """
    Extract resolution details from closing letter text.
    """
    resolution_details = {
        "resolution_type": None,
        "resolution_amount": None,
        "payment_terms": None,
        "user_fee": None,
        "start_date": None,
        "tax_years": [],
        "lien_status": None,
        "account_balance": None,
        "payment_method": None,
        "services_completed": [],
        "additional_terms": []
    }
    
    # Extract resolution type
    resolution_patterns = {
        "IA": r'\b(?:Installment\s+Agreement|IA)\b',
        "CNC": r'\b(?:Currently\s+Non[-\s]?Collectible|CNC)\b',
        "OIC": r'\b(?:Offer\s+in\s+Compromise|OIC)\b',
        "PPIA": r'\b(?:Partial\s+Payment\s+Installment\s+Agreement|PPIA)\b',
        "FPA": r'\b(?:Full\s+Payment\s+Agreement|Pay\s*In\s*Full|PIF)\b'
    }
    
    for res_type, pattern in resolution_patterns.items():
        if re.search(pattern, text_content, re.IGNORECASE):
            resolution_details["resolution_type"] = res_type
            break
    
    # Extract account balance
    balance_match = re.search(r'Total\s+account\s+balance\s+(?:as\s+of\s+[^:]+)?:\s*\$?([\d,]+\.?\d*)', text_content, re.IGNORECASE)
    if balance_match:
        balance_str = balance_match.group(1).replace(',', '')
        try:
            resolution_details["account_balance"] = float(balance_str)
        except ValueError:
            pass
    
    # Extract payment amount
    payment_match = re.search(r'Payment\s+Amount:\s*\$?([\d,]+\.?\d*)', text_content, re.IGNORECASE)
    if payment_match:
        amount_str = payment_match.group(1).replace(',', '')
        try:
            resolution_details["resolution_amount"] = float(amount_str)
        except ValueError:
            pass
    
    # Extract user fee
    fee_match = re.search(r'User\s+fee:\s*\$?([\d,]+\.?\d*)', text_content, re.IGNORECASE)
    if fee_match:
        fee_str = fee_match.group(1).replace(',', '')
        try:
            resolution_details["user_fee"] = float(fee_str)
        except ValueError:
            pass
    
    # Extract start date
    start_match = re.search(r'First\s+payment\s+due:\s*(\d{1,2}/\d{1,2}/\d{4})', text_content, re.IGNORECASE)
    if start_match:
        resolution_details["start_date"] = start_match.group(1)
    
    # Extract tax years
    years_match = re.search(r'Tax\s+years\s+included:\s*([\d,\s]+)', text_content, re.IGNORECASE)
    if years_match:
        years_str = years_match.group(1)
        years = re.findall(r'\d{4}', years_str)
        resolution_details["tax_years"] = years
    else:
        # Try alternative format
        alt_years_match = re.search(r'Includes\s+tax\s+year\(s\):\s*([\d,\s]+)', text_content, re.IGNORECASE)
        if alt_years_match:
            years_str = alt_years_match.group(1)
            years = re.findall(r'\d{4}', years_str)
            resolution_details["tax_years"] = years
    
    # Extract payment terms
    terms_match = re.search(r'Monthly\s+due\s+date:\s*(\d+(?:st|nd|rd|th))', text_content, re.IGNORECASE)
    if terms_match:
        resolution_details["payment_terms"] = f"Due on {terms_match.group(1)} of each month"
    
    # Extract lien status
    if re.search(r'Liens:\s*Will\s+not\s+be\s+filed', text_content, re.IGNORECASE):
        resolution_details["lien_status"] = "No liens filed"
    elif re.search(r'Liens:\s*Have\s+already\s+been\s+filed', text_content, re.IGNORECASE):
        resolution_details["lien_status"] = "Liens already filed"
    elif re.search(r'Liens:\s*Will\s+be\s+filed', text_content, re.IGNORECASE):
        resolution_details["lien_status"] = "Liens will be filed"
    
    # Extract payment method
    method_match = re.search(r'Payment\s+method:\s*(\w+)', text_content, re.IGNORECASE)
    if method_match:
        resolution_details["payment_method"] = method_match.group(1).title()
    
    # Extract services completed
    services_section = re.search(r'Services\s+Completed\s+by\s+TPS:(.*?)(?:\n\n|\nTerms|\nTotal|$)', text_content, re.IGNORECASE | re.DOTALL)
    if services_section:
        services_text = services_section.group(1)
        services = []
        for line in services_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('•'):
                services.append(line)
        resolution_details["services_completed"] = services
    
    # Extract additional terms
    terms_section = re.search(r'Additional\s+(?:terms|Terms)\s+(?:for\s+you\s+to\s+consider|to\s+Consider):(.*?)(?:\n\n|Best\s+Regards|$)', text_content, re.IGNORECASE | re.DOTALL)
    if terms_section:
        terms_text = terms_section.group(1)
        terms = []
        for line in terms_text.split('\n'):
            line = line.strip()
            if line and re.match(r'^\d+\.', line):
                terms.append(line)
        resolution_details["additional_terms"] = terms
    
    return resolution_details

# --- Batch Processing Endpoints ---

@router.get("/batch/completed-cases", tags=["Batch Processing"])
def get_completed_cases():
    """
    Get all completed cases from Logiqs API.
    Returns list of case IDs that have status 349 (completed).
    """
    logger.info("🔍 Fetching all completed cases from Logiqs API")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        completed_cases = fetch_completed_cases(cookies)
        
        logger.info(f"✅ Successfully fetched {len(completed_cases)} completed cases")
        return {
            "total_completed_cases": len(completed_cases),
            "case_ids": completed_cases
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching completed cases: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/batch/closing-letters-analysis", tags=["Batch Processing"])
def analyze_all_completed_closing_letters(
    limit: Optional[int] = Query(10, description="Limit number of cases to process (for testing)"),
    start_index: Optional[int] = Query(0, description="Start from this index in the completed cases list")
):
    """
    Analyze closing letters for all completed cases.
    Processes cases in batches and returns structured analysis.
    """
    logger.info(f"🔍 Starting batch closing letter analysis (limit: {limit}, start: {start_index})")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get all completed cases
        completed_cases = fetch_completed_cases(cookies)
        
        # Apply limits
        end_index = min(start_index + limit, len(completed_cases))
        cases_to_process = completed_cases[start_index:end_index]
        
        logger.info(f"📊 Processing {len(cases_to_process)} cases out of {len(completed_cases)} total completed cases")
        
        # Process cases in parallel batches
        results = process_closing_letters_batch(cases_to_process, cookies)
        
        logger.info(f"✅ Successfully processed {len(results)} cases")
        return {
            "total_completed_cases": len(completed_cases),
            "processed_cases": len(cases_to_process),
            "start_index": start_index,
            "end_index": end_index,
            "results": results,
            "summary": generate_batch_summary(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in batch closing letter analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def fetch_completed_cases(cookies: dict) -> List[int]:
    """
    Fetch all completed cases from Logiqs API.
    """
    logger.info("📡 Fetching completed cases from Logiqs API")
    
    # Extract cookie string and user agent from cookies dict
    cookie_header = None
    user_agent = None
    if cookies:
        if isinstance(cookies, dict):
            if 'cookies' in cookies:
                cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies['cookies']])
            if 'user_agent' in cookies:
                user_agent = cookies['user_agent']
        elif isinstance(cookies, str):
            cookie_header = cookies
    
    if not cookie_header:
        logger.error("❌ No valid cookies found for authentication")
        raise Exception("No valid cookies found for authentication.")
    
    if not user_agent:
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    url = "https://tps.logiqs.com/publicapi/2020-02-22/cases/GetCasesByStatus?apikey=4917fa0ce4694529a9b97ead1a60c932&StatusID=349"
    logger.info(f"🌐 Making API request to: {url}")
    
    headers = {
        "Accept": "application/json",
        "User-Agent": user_agent,
        "Cookie": cookie_header
    }

    try:
        response = httpx.get(
            url,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"📊 Response status: {response.status_code}")
        response.raise_for_status()
        
        response_data = response.json()
        
        if response_data.get("status") != "success" or "data" not in response_data:
            logger.error(f"❌ Invalid response structure: {response_data}")
            raise Exception("Invalid response structure from API")
        
        case_ids = response_data["data"]
        logger.info(f"✅ Successfully fetched {len(case_ids)} completed case IDs")
        
        return case_ids
        
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error {e.response.status_code}: {e.response.text}")
        raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"❌ Request error: {str(e)}")
        raise Exception(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error fetching completed cases: {str(e)}")
        raise Exception(f"Error fetching completed cases: {str(e)}")

def process_closing_letters_batch(case_ids: List[int], cookies: dict) -> List[Dict[str, Any]]:
    """
    Process closing letters for a batch of cases.
    """
    logger.info(f"🔍 Processing closing letters for {len(case_ids)} cases")
    
    results = []
    
    for i, case_id in enumerate(case_ids):
        logger.info(f"📄 Processing case {i+1}/{len(case_ids)}: {case_id}")
        
        try:
            # Check if case has closing letters
            closing_letter_files = fetch_closing_letter_file_grid(str(case_id), cookies)
            
            if not closing_letter_files:
                # No closing letters found
                results.append({
                    "case_id": case_id,
                    "has_closing_letters": False,
                    "error": None,
                    "resolution_summary": None
                })
                continue
            
            # Download and parse closing letter PDFs
            closing_letter_data = parse_closing_letter_pdfs(closing_letter_files, cookies, str(case_id))
            
            # Parse text into structured data
            structured_data = parse_closing_letter_text_to_structured(closing_letter_data)
            
            results.append({
                "case_id": case_id,
                "has_closing_letters": True,
                "error": None,
                "resolution_summary": structured_data["resolution_summary"],
                "total_files": structured_data["total_files"]
            })
            
            logger.info(f"✅ Successfully processed case {case_id} ({structured_data['resolution_summary']['resolution_type']})")
            
        except Exception as e:
            logger.error(f"❌ Error processing case {case_id}: {str(e)}")
            results.append({
                "case_id": case_id,
                "has_closing_letters": False,
                "error": str(e),
                "resolution_summary": None
            })
    
    logger.info(f"✅ Batch processing completed. Successfully processed {len([r for r in results if not r['error']])} cases")
    return results

def generate_batch_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics from batch processing results.
    """
    logger.info(f"🔍 Generating batch summary for {len(results)} results...")
    total_cases = len(results)
    successful_cases = len([r for r in results if r and not r.get('error')])
    cases_with_closing_letters = len([r for r in results if r and r.get('has_closing_letters', False)])
    
    # Count resolution types
    resolution_counts = {}
    for result in results:
        if not result:
            continue
        resolution_summary = result.get('resolution_summary') if result else None
        if resolution_summary and resolution_summary.get('resolution_type'):
            res_type = resolution_summary['resolution_type']
            resolution_counts[res_type] = resolution_counts.get(res_type, 0) + 1
    
    # Calculate average account balance
    balances = []
    for result in results:
        if not result:
            continue
        resolution_summary = result.get('resolution_summary') if result else None
        if resolution_summary and resolution_summary.get('account_balance') is not None:
            try:
                balances.append(float(resolution_summary['account_balance']))
            except Exception:
                continue
    avg_balance = sum(balances) / len(balances) if balances else 0
    
    summary = {
        "total_cases": total_cases,
        "successful_cases": successful_cases,
        "cases_with_closing_letters": cases_with_closing_letters,
        "success_rate": (successful_cases / total_cases * 100) if total_cases > 0 else 0,
        "closing_letter_rate": (cases_with_closing_letters / total_cases * 100) if total_cases > 0 else 0,
        "resolution_type_distribution": resolution_counts,
        "average_account_balance": round(avg_balance, 2) if avg_balance > 0 else None
    }
    logger.info(f"🔍 Batch summary generated: {summary}")
    return summary

@router.get("/batch/export-closing-letters-csv", tags=["Batch Processing"])
def export_closing_letters_to_csv(
    limit: Optional[int] = Query(3, description="Limit number of cases to process (None = all cases)"),
    start_index: Optional[int] = Query(0, description="Start from this index in the completed cases list"),
    batch_size: Optional[int] = Query(2, description="Process cases in batches of this size")
):
    """
    Export closing letter analysis for all completed cases to CSV format.
    More efficient for large-scale analysis.
    """
    logger.info(f"📊 Starting CSV export of closing letter analysis (limit: {limit}, start: {start_index}, batch_size: {batch_size})")
    
    # Check authentication
    if not cookies_exist():
        logger.error("❌ Authentication required - no cookies found")
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    cookies = get_cookies()
    
    try:
        # Get all completed cases
        completed_cases = fetch_completed_cases(cookies)
        logger.info(f"✅ Retrieved {len(completed_cases)} completed cases from API.")
        
        # Apply limits
        if limit:
            end_index = min(start_index + limit, len(completed_cases))
        else:
            end_index = len(completed_cases)
            
        cases_to_process = completed_cases[start_index:end_index]
        logger.info(f"📊 Will process {len(cases_to_process)} cases (from {start_index} to {end_index}).")
        
        # Process cases in batches and collect results
        all_results = []
        total_batches = (len(cases_to_process) + batch_size - 1) // batch_size
        logger.info(f"🔄 Total batches to process: {total_batches}")
        
        for batch_num in range(total_batches):
            start_batch = batch_num * batch_size
            end_batch = min(start_batch + batch_size, len(cases_to_process))
            batch_cases = cases_to_process[start_batch:end_batch]
            logger.info(f"📦 Processing batch {batch_num + 1}/{total_batches} (cases {start_batch + 1}-{end_batch})")
            try:
                batch_results = process_closing_letters_batch(batch_cases, cookies)
                all_results.extend(batch_results)
            except Exception as e:
                logger.error(f"❌ Error in batch {batch_num + 1}: {str(e)}")
            import time
            time.sleep(1)
        
        # Generate CSV data
        logger.info(f"📝 Generating CSV data for {len(all_results)} results...")
        csv_data = generate_closing_letters_csv(all_results)
        
        logger.info(f"✅ Successfully processed {len(all_results)} cases and generated CSV data")
        
        summary = generate_batch_summary(all_results)
        logger.info(f"📊 Batch summary: {summary}")
        
        return {
            "total_completed_cases": len(completed_cases),
            "processed_cases": len(cases_to_process),
            "start_index": start_index,
            "end_index": end_index,
            "total_batches": total_batches,
            "batch_size": batch_size,
            "csv_data": csv_data,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in CSV export: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def generate_closing_letters_csv(results: List[Dict[str, Any]]) -> str:
    """
    Generate CSV data from closing letter analysis results.
    """
    import csv
    import io
    
    # Create CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Case ID",
        "Has Closing Letters",
        "Resolution Type",
        "Resolution Amount",
        "Payment Terms",
        "User Fee",
        "Start Date",
        "Tax Years",
        "Lien Status",
        "Account Balance",
        "Payment Method",
        "Services Completed",
        "Additional Terms",
        "Error",
        "Total Files"
    ])
    
    # Write data rows
    for result in results:
        resolution_summary = result.get('resolution_summary')
        if not resolution_summary:
            writer.writerow([
                result.get('case_id', ''),
                result.get('has_closing_letters', False),
                '', '', '', '', '', '', '', '', '', '', '',
                result.get('error', ''),
                result.get('total_files', 0)
            ])
            continue
        writer.writerow([
            result.get('case_id', ''),
            result.get('has_closing_letters', False),
            resolution_summary.get('resolution_type', ''),
            resolution_summary.get('resolution_amount', ''),
            resolution_summary.get('payment_terms', ''),
            resolution_summary.get('user_fee', ''),
            resolution_summary.get('start_date', ''),
            '; '.join(resolution_summary.get('tax_years', [])),
            resolution_summary.get('lien_status', ''),
            resolution_summary.get('account_balance', ''),
            resolution_summary.get('payment_method', ''),
            '; '.join(resolution_summary.get('services_completed', [])),
            '; '.join(resolution_summary.get('additional_terms', [])),
            result.get('error', ''),
            result.get('total_files', 0)
        ])
    
    return output.getvalue()
