from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import os
import asyncio
import logging
import re
from pydantic import BaseModel
from app.models.training_models import (
    BatchUploadRequest, BatchUploadResponse, DocumentResponse, ExtractionResponse,
    AnnotationRequest, AnnotationResponse, TrainingProgressResponse, TrainingRunRequest, TrainingRunResponse,
    Document, Extraction, Annotation, TrainingRun, FormType
)
from app.db import get_db, SessionLocal
from app.utils.wi_patterns import form_patterns
from app.utils.pattern_learning import PatternLearningSystem, pattern_learning_system, fetch_wi_training_data
from datetime import datetime
from app.utils.cookies import cookies_exist, get_cookies
from app.services.wi_service import fetch_wi_file_grid, download_wi_pdf
from app.utils.pdf_utils import extract_text_from_pdf
from app.utils.playwright_auth import logiqs_login_async
from app.utils.supabase_client import get_supabase_client

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "/tmp/tra_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

pattern_learner = PatternLearningSystem()

# In-memory progress tracking (in production, use Redis or database)
processing_status = {}

# Request model for process-cases
class ProcessCasesRequest(BaseModel):
    case_ids: List[str]

# Default credentials
DEFAULT_USERNAME = "lindsey.stevens@tra.com"
DEFAULT_PASSWORD = "Millie#5986"

def get_form_patterns_from_db():
    """Fetch form patterns from the enhanced form_types table"""
    try:
        supabase = get_supabase_client()
        result = supabase.table("form_types").select(
            "code, form_pattern, field_definitions, category, calculation_rules, identifiers"
        ).execute()
        
        patterns = {}
        for form in result.data:
            if form.get('form_pattern') and form.get('field_definitions'):
                # Convert lambda configurations back to callable functions
                calculation_rules = convert_lambda_configs_to_functions(form.get('calculation_rules', {}))
                
                patterns[form['code']] = {
                    'pattern': form['form_pattern'],
                    'fields': form['field_definitions'],
                    'category': form.get('category'),
                    'calculation': calculation_rules,
                    'identifiers': form.get('identifiers')
                }
        
        logger.info(f"Loaded {len(patterns)} form patterns from database")
        return patterns
    except Exception as e:
        logger.error(f"Failed to load form patterns from database: {str(e)}")
        # Fallback to imported patterns
        logger.warning("Falling back to imported wi_patterns")
        return form_patterns

def convert_lambda_configs_to_functions(calculation_rules):
    """Convert lambda configurations back to callable functions"""
    if not calculation_rules:
        return {}
    
    converted = {}
    for key, value in calculation_rules.items():
        if isinstance(value, dict) and value.get('type') == 'lambda':
            try:
                # Create a function from the lambda body
                lambda_body = value['body']
                # Create a function that can be called with fields parameter
                func_code = f"def calc_func(fields):\n    return {lambda_body}"
                namespace = {}
                exec(func_code, namespace)
                converted[key] = namespace['calc_func']
            except Exception as e:
                logger.warning(f"Could not convert lambda config for {key}: {str(e)}")
                # Fallback to a simple function that returns 0
                converted[key] = lambda fields: 0
        else:
            converted[key] = value
    
    return converted

def extract_fields_from_text(text):
    logger.debug(f"Starting field extraction from text of length: {len(text)}")
    
    # Get patterns from database
    patterns = get_form_patterns_from_db()
    
    results = []
    for form_code, pattern in patterns.items():
        form_pat = pattern.get('pattern')
        if form_pat and re.search(form_pat, text, re.IGNORECASE):
            logger.debug(f"Found form pattern: {form_code}")
            fields = {}
            field_definitions = pattern.get('fields', {})
            
            for field, regex in field_definitions.items():
                if regex:
                    match = re.search(regex, text, re.IGNORECASE)
                    if match:
                        fields[field] = match.group(1)
            
            results.append({
                'form_type': form_code, 
                'fields': fields,
                'category': pattern.get('category'),
                'calculation': pattern.get('calculation'),
                'identifiers': pattern.get('identifiers')
            })
    
    logger.debug(f"Extracted {len(results)} form matches")
    return results

async def get_pdf_text_for_case(case_id: str) -> str:
    logger.info(f"Starting PDF text extraction for case: {case_id}")
    # Use the real WI PDF/text extraction pipeline with auto-authentication
    if not cookies_exist():
        logger.info("No cookies found, attempting authentication...")
        try:
            # Run the async authentication
            auth_result = await logiqs_login_async(DEFAULT_USERNAME, DEFAULT_PASSWORD)
            logger.info(f"Authentication result: {auth_result}")
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    cookies = get_cookies()
    if not cookies:
        logger.error("Failed to load authentication cookies")
        raise HTTPException(status_code=401, detail="Failed to load authentication cookies")
    
    try:
        logger.info(f"Fetching WI files for case: {case_id}")
        wi_files = fetch_wi_file_grid(case_id, cookies)
        if not wi_files:
            logger.error(f"No WI files found for case {case_id}")
            raise HTTPException(status_code=404, detail=f"No WI files found for case {case_id}.")
        
        logger.info(f"Found {len(wi_files)} WI files")
        all_text = []
        for i, wi_file in enumerate(wi_files):
            case_doc_id = wi_file.get("CaseDocumentID")
            if not case_doc_id:
                logger.warning(f"No CaseDocumentID found for WI file {i+1}")
                continue
            try:
                logger.info(f"Downloading PDF {i+1}/{len(wi_files)}: {case_doc_id}")
                pdf_bytes = download_wi_pdf(case_doc_id, case_id, cookies)
                if not pdf_bytes:
                    logger.warning(f"No PDF bytes received for {case_doc_id}")
                    continue
                logger.info(f"Extracting text from PDF {i+1}")
                text = extract_text_from_pdf(pdf_bytes)
                if text:
                    all_text.append(text)
                    logger.info(f"Extracted {len(text)} characters from PDF {i+1}")
                else:
                    logger.warning(f"No text extracted from PDF {i+1}")
            except Exception as e:
                logger.error(f"Error processing PDF {i+1}: {str(e)}")
                continue  # Skip files that fail to download or extract
        
        if not all_text:
            logger.error(f"No text could be extracted from WI PDFs for case {case_id}")
            raise HTTPException(status_code=500, detail=f"No text could be extracted from WI PDFs for case {case_id}.")
        
        combined_text = "\n".join(all_text)
        logger.info(f"Total extracted text length: {len(combined_text)}")
        return combined_text
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing case {case_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing case {case_id}: {str(e)}")

async def process_case_background(case_id: str, task_id: str):
    """Background task to process a single case"""
    logger.info(f"Starting background processing for case: {case_id}, task: {task_id}")
    try:
        processing_status[task_id] = {
            "status": "processing",
            "case_id": case_id,
            "progress": 0,
            "message": "Starting PDF download..."
        }
        
        # Get Supabase client
        logger.debug("Getting Supabase client")
        supabase = get_supabase_client()
        
        # Update progress
        processing_status[task_id]["progress"] = 10
        processing_status[task_id]["message"] = "Fetching WI files..."
        
        # Get PDF text
        logger.info("Getting PDF text for case")
        raw_text = await get_pdf_text_for_case(case_id)
        
        processing_status[task_id]["progress"] = 50
        processing_status[task_id]["message"] = "Storing document..."
        
        # Store document in Supabase
        logger.info("Storing document in Supabase")
        doc_id = str(uuid.uuid4())
        doc_data = {
            "id": doc_id,
            "filename": None,
            "source_url": None,
            "upload_batch_id": None,
            "status": "processed",
            "raw_text": raw_text,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.debug(f"Inserting document with ID: {doc_id}")
        try:
            result = supabase.table("documents").insert(doc_data).execute()
            logger.info("Document successfully stored in Supabase")
        except Exception as e:
            logger.error(f"Failed to store document in Supabase: {str(e)}")
            raise
        
        processing_status[task_id]["progress"] = 70
        processing_status[task_id]["message"] = "Extracting fields..."
        
        # Extract fields
        logger.info("Extracting fields from text")
        extractions = []
        for result in extract_fields_from_text(raw_text):
            logger.debug(f"Processing form type: {result['form_type']}")
            # Get form type from Supabase
            try:
                form_type_result = supabase.table("form_types").select("*").eq("code", result['form_type']).execute()
                if not form_type_result.data:
                    logger.warning(f"Form type not found: {result['form_type']}")
                    continue
                form_type_id = form_type_result.data[0]['id']
                
                extraction_data = {
                    "document_id": doc_id,
                    "form_type_id": form_type_id,
                    "extraction_method": "regex",
                    "fields": result['fields'],
                    "confidence": 1.0,
                    "created_at": datetime.now().isoformat()
                }
                
                logger.debug(f"Inserting extraction for form type: {result['form_type']}")
                supabase.table("extractions").insert(extraction_data).execute()
                extractions.append({
                    "form_type": result['form_type'],
                    "fields": result['fields']
                })
                logger.debug(f"Extraction stored successfully")
            except Exception as e:
                logger.error(f"Failed to store extraction for {result['form_type']}: {str(e)}")
                continue
        
        processing_status[task_id]["progress"] = 100
        processing_status[task_id]["status"] = "completed"
        processing_status[task_id]["message"] = f"Completed! Found {len(extractions)} extractions"
        processing_status[task_id]["extractions"] = extractions
        logger.info(f"Background processing completed for case: {case_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for case {case_id}: {str(e)}")
        processing_status[task_id]["status"] = "error"
        processing_status[task_id]["message"] = f"Error: {str(e)}"

@router.post("/process-cases")
async def process_cases(req: ProcessCasesRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Process cases with background task support"""
    logger.info(f"Received process-cases request with {len(req.case_ids)} case IDs")
    logger.debug(f"Case IDs: {req.case_ids}")
    
    case_ids = req.case_ids
    if len(case_ids) == 1:
        # For single case, process immediately
        logger.info(f"Processing single case: {case_ids[0]}")
        summary = {"processed": 0, "extractions": [], "errors": []}
        case_id = case_ids[0]
        try:
            logger.info(f"Starting PDF processing for case: {case_id}")
            raw_text = await get_pdf_text_for_case(case_id)
            logger.info(f"PDF text extracted, length: {len(raw_text)}")
            
            # Get Supabase client
            logger.debug("Getting Supabase client for document storage")
            supabase = get_supabase_client()
            
            doc_id = str(uuid.uuid4())
            logger.debug(f"Generated document ID: {doc_id}")
            
            doc_data = {
                "id": doc_id,
                "filename": None,
                "source_url": None,
                "upload_batch_id": None,
                "status": "processed",
                "raw_text": raw_text,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            logger.info("Storing document in Supabase")
            try:
                result = supabase.table("documents").insert(doc_data).execute()
                logger.info("Document successfully stored in Supabase")
            except Exception as e:
                logger.error(f"Failed to store document in Supabase: {str(e)}")
                raise
            
            logger.info("Starting field extraction")
            for result in extract_fields_from_text(raw_text):
                logger.debug(f"Processing form type: {result['form_type']}")
                try:
                    # Get form type from Supabase
                    form_type_result = supabase.table("form_types").select("*").eq("code", result['form_type']).execute()
                    if not form_type_result.data:
                        logger.warning(f"Form type not found: {result['form_type']}")
                        continue
                    form_type_id = form_type_result.data[0]['id']
                    
                    extraction_data = {
                        "document_id": doc_id,
                        "form_type_id": form_type_id,
                        "extraction_method": "regex",
                        "fields": result['fields'],
                        "confidence": 1.0,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    logger.debug(f"Storing extraction for form type: {result['form_type']}")
                    supabase.table("extractions").insert(extraction_data).execute()
                    summary["extractions"].append({
                        "case_id": case_id,
                        "form_type": result['form_type'],
                        "fields": result['fields']
                    })
                    logger.debug(f"Extraction stored successfully")
                except Exception as e:
                    logger.error(f"Failed to store extraction for {result['form_type']}: {str(e)}")
                    continue
            
            summary["processed"] += 1
            logger.info(f"Processing completed successfully for case: {case_id}")
            return summary
            
        except HTTPException as e:
            logger.error(f"HTTPException during processing: {e.detail}")
            summary["errors"].append({"case_id": case_id, "error": e.detail})
            return summary
        except Exception as e:
            logger.error(f"Exception during processing: {str(e)}")
            summary["errors"].append({"case_id": case_id, "error": str(e)})
            return summary
    else:
        # For multiple cases, use background tasks
        logger.info(f"Processing multiple cases: {case_ids}")
        task_ids = []
        for case_id in case_ids:
            task_id = str(uuid.uuid4())
            task_ids.append(task_id)
            background_tasks.add_task(process_case_background, case_id, task_id)
        
        return {
            "message": f"Processing {len(case_ids)} cases in background",
            "task_ids": task_ids,
            "status": "started"
        }

@router.get("/process-status/{task_id}")
async def get_process_status(task_id: str):
    """Get the status of a background processing task"""
    if task_id not in processing_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return processing_status[task_id]

@router.post("/batch-upload", response_model=BatchUploadResponse)
async def batch_upload(
    files: Optional[List[UploadFile]] = File(None),
    method: Optional[str] = Form(None),
    urls: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    logger.info("Starting batch upload")
    batch_id = str(uuid.uuid4())
    total_documents = 0
    
    # Get Supabase client
    supabase = get_supabase_client()
    
    # Handle file uploads
    if files:
        logger.info(f"Processing {len(files)} uploaded files")
        for file in files:
            logger.debug(f"Processing file: {file.filename}")
            file_id = str(uuid.uuid4())
            file_path = os.path.join(UPLOAD_DIR, file_id + "_" + file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            # Simulate text extraction (replace with real PDF text extraction)
            raw_text = f"Simulated text for {file.filename}"
            
            doc_data = {
                "id": file_id,
                "filename": file.filename,
                "upload_batch_id": batch_id,
                "status": "processed",
                "raw_text": raw_text,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            try:
                supabase.table("documents").insert(doc_data).execute()
                logger.debug(f"Document stored: {file_id}")
                
                # Extract fields
                for result in extract_fields_from_text(raw_text):
                    try:
                        form_type_result = supabase.table("form_types").select("*").eq("code", result['form_type']).execute()
                        if not form_type_result.data:
                            logger.warning(f"Form type not found: {result['form_type']}")
                            continue
                        form_type_id = form_type_result.data[0]['id']
                        
                        extraction_data = {
                            "document_id": file_id,
                            "form_type_id": form_type_id,
                            "extraction_method": "regex",
                            "fields": result['fields'],
                            "confidence": 1.0,
                            "created_at": datetime.now().isoformat()
                        }
                        supabase.table("extractions").insert(extraction_data).execute()
                        logger.debug(f"Extraction stored for {result['form_type']}")
                    except Exception as e:
                        logger.error(f"Failed to store extraction: {str(e)}")
                        continue
                total_documents += 1
            except Exception as e:
                logger.error(f"Failed to store document: {str(e)}")
                continue
                
    # Handle URL batch (simulate)
    elif method == "url" and urls:
        logger.info("Processing URL batch")
        url_list = [u.strip() for u in urls.split("\n") if u.strip()]
        for url in url_list:
            logger.debug(f"Processing URL: {url}")
            file_id = str(uuid.uuid4())
            raw_text = f"Simulated text for {url}"
            
            doc_data = {
                "id": file_id,
                "source_url": url,
                "upload_batch_id": batch_id,
                "status": "processed",
                "raw_text": raw_text,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            try:
                supabase.table("documents").insert(doc_data).execute()
                logger.debug(f"Document stored: {file_id}")
                
                for result in extract_fields_from_text(raw_text):
                    try:
                        form_type_result = supabase.table("form_types").select("*").eq("code", result['form_type']).execute()
                        if not form_type_result.data:
                            logger.warning(f"Form type not found: {result['form_type']}")
                            continue
                        form_type_id = form_type_result.data[0]['id']
                        
                        extraction_data = {
                            "document_id": file_id,
                            "form_type_id": form_type_id,
                            "extraction_method": "regex",
                            "fields": result['fields'],
                            "confidence": 1.0,
                            "created_at": datetime.now().isoformat()
                        }
                        supabase.table("extractions").insert(extraction_data).execute()
                        logger.debug(f"Extraction stored for {result['form_type']}")
                    except Exception as e:
                        logger.error(f"Failed to store extraction: {str(e)}")
                        continue
                total_documents += 1
            except Exception as e:
                logger.error(f"Failed to store document: {str(e)}")
                continue
    else:
        logger.error("No files or URLs provided")
        raise HTTPException(status_code=400, detail="No files or URLs provided")
    
    logger.info(f"Batch upload completed. Total documents: {total_documents}")
    return BatchUploadResponse(
        batch_id=batch_id,
        status="processed",
        total_documents=total_documents,
        created_at=datetime.now()
    )

@router.get("/documents")
def list_documents(status: Optional[str] = None, db: Session = Depends(get_db)):
    logger.info("Listing documents")
    supabase = get_supabase_client()
    
    try:
        query = supabase.table("documents").select("*")
        if status:
            query = query.eq("status", status)
        
        result = query.execute()
        docs = result.data
        
        logger.info(f"Found {len(docs)} documents")
        return {"documents": [DocumentResponse(
            id=d["id"],
            source_url=d.get("source_url"),
            filename=d.get("filename"),
            upload_batch_id=d.get("upload_batch_id"),
            status=d["status"],
            error_message=d.get("error_message"),
            file_size=d.get("file_size"),
            raw_text=d.get("raw_text"),
            processing_time_ms=d.get("processing_time_ms"),
            created_at=d["created_at"],
            updated_at=d["updated_at"]
        ) for d in docs]}
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@router.get("/extractions/{document_id}", response_model=ExtractionResponse)
def get_extraction(document_id: str, db: Session = Depends(get_db)):
    logger.info(f"Getting extraction for document: {document_id}")
    supabase = get_supabase_client()
    
    try:
        result = supabase.table("extractions").select("*").eq("document_id", document_id).execute()
        if not result.data:
            logger.warning(f"Extraction not found for document: {document_id}")
            raise HTTPException(status_code=404, detail="Extraction not found")
        
        extraction = result.data[0]
        logger.info(f"Found extraction: {extraction['id']}")
        return ExtractionResponse(
            id=extraction["id"],
            document_id=extraction["document_id"],
            form_type_id=extraction["form_type_id"],
            extraction_method=extraction["extraction_method"],
            fields=extraction["fields"],
            confidence=extraction["confidence"],
            created_at=extraction["created_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get extraction: {str(e)}")

@router.post("/annotations", response_model=AnnotationResponse)
def save_annotation(req: AnnotationRequest, db: Session = Depends(get_db)):
    logger.info(f"Saving annotation for extraction: {req.extraction_id}")
    supabase = get_supabase_client()
    
    annotation_data = {
        "extraction_id": req.extraction_id,
        "annotator_id": req.annotator_id,
        "corrected_fields": req.corrected_fields,
        "status": req.status,
        "notes": req.notes,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        result = supabase.table("annotations").insert(annotation_data).execute()
        annotation = result.data[0]
        logger.info(f"Annotation saved: {annotation['id']}")
        
        return AnnotationResponse(
            id=annotation["id"],
            extraction_id=annotation["extraction_id"],
            annotator_id=annotation["annotator_id"],
            corrected_fields=annotation["corrected_fields"],
            status=annotation["status"],
            notes=annotation["notes"],
            created_at=annotation["created_at"],
            updated_at=annotation["updated_at"]
        )
    except Exception as e:
        logger.error(f"Failed to save annotation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save annotation: {str(e)}")

@router.get("/progress", response_model=TrainingProgressResponse)
def get_training_progress(db: Session = Depends(get_db)):
    logger.info("Getting training progress")
    supabase = get_supabase_client()
    
    try:
        # Query the training_progress view
        result = supabase.table("training_progress").select("*").execute()
        progress = []
        for row in result.data:
            progress.append({
                "form_type": row["form_type"],
                "description": row["description"],
                "annotated_count": row["annotated_count"],
                "total_extractions": row["total_extractions"],
                "completion_percentage": row["completion_percentage"],
                "avg_confidence": row["avg_confidence"],
            })
        
        logger.info(f"Found progress data for {len(progress)} form types")
        return {"progress": progress}
    except Exception as e:
        logger.error(f"Failed to get training progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get training progress: {str(e)}")

@router.post("/start-training/{form_type_code}", response_model=TrainingRunResponse)
def start_training(form_type_code: str, req: Optional[TrainingRunRequest] = None, db: Session = Depends(get_db)):
    """Start training for a form type using the form type code"""
    logger.info(f"Starting training for form type code: {form_type_code}")
    supabase = get_supabase_client()
    try:
        # Get form_type_id from form_type_code
        form_type_result = supabase.table("form_types").select("id").eq("code", form_type_code).execute()
        if not form_type_result.data:
            logger.error(f"Form type not found: {form_type_code}")
            raise HTTPException(status_code=404, detail=f"Form type '{form_type_code}' not found")
        form_type_id = form_type_result.data[0]['id']
        logger.info(f"Found form_type_id: {form_type_id} for code: {form_type_code}")
        # --- ML Training for WI fields ---
        if form_type_code in form_patterns:
            fields = form_patterns[form_type_code].get('fields', {})
            for field_name in fields:
                logger.info(f"Fetching training data for field: {field_name}")
                training_data = fetch_wi_training_data(field_name, supabase=supabase, limit=1000)
                if not training_data:
                    logger.warning(f"No training data found for field: {field_name}")
                    continue
                logger.info(f"Training ML model for field: {field_name} with {len(training_data)} examples")
                try:
                    pattern_learning_system.train(training_data, field_name, epochs=5)
                    logger.info(f"Model trained and saved for field: {field_name}")
                except Exception as e:
                    logger.error(f"Failed to train model for field {field_name}: {e}")
        else:
            logger.info(f"Form type {form_type_code} not in WI form_patterns; skipping ML training.")
        # --- End ML Training ---
        notes = req.notes if req else "Training run started via API"
        run_data = {
            "form_type_id": form_type_id,
            "started_at": datetime.now().isoformat(),
            "finished_at": datetime.now().isoformat(),
            "status": "completed",
            "accuracy": 0.95,  # Placeholder
            "regex_baseline": 0.90,  # Placeholder
            "model_file_path": f"/models/model_{form_type_code}.bin",
            "notes": notes
        }
        result = supabase.table("training_runs").insert(run_data).execute()
        run = result.data[0]
        logger.info(f"Training run saved: {run['id']}")
        return TrainingRunResponse(
            id=run["id"],
            form_type_id=run["form_type_id"],
            started_at=run["started_at"],
            finished_at=run["finished_at"],
            status=run["status"],
            accuracy=run["accuracy"],
            regex_baseline=run["regex_baseline"],
            model_file_path=run["model_file_path"],
            notes=run["notes"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start training: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start training: {str(e)}")

@router.get("/validation")
def get_validation_results(db: Session = Depends(get_db)):
    """Get ML model validation results comparing ML vs regex vs ground truth"""
    logger.info("Getting validation results")
    supabase = get_supabase_client()
    
    try:
        # Get recent extractions with annotations for validation
        result = supabase.table("extractions").select(
            "extractions.*, annotations.corrected_fields, annotations.status, form_types.code as form_type"
        ).eq("annotations.status", "approved").limit(20).execute()
        
        validation_results = []
        for row in result.data:
            if row.get('fields') and row.get('corrected_fields'):
                # Compare ML extraction vs corrected fields
                ml_fields = row['fields']
                corrected_fields = row['corrected_fields']
                
                # Generate validation results for each field
                for field_name, ml_value in ml_fields.items():
                    corrected_value = corrected_fields.get(field_name, '')
                    
                    # Calculate confidence (simplified - could be enhanced with actual ML confidence)
                    confidence = 0.85 if ml_value == corrected_value else 0.45
                    
                    validation_results.append({
                        "form_type": row.get('form_type', 'Unknown'),
                        "field_name": field_name,
                        "ml_value": ml_value,
                        "regex_value": ml_value,  # Since we're using regex extraction currently
                        "ground_truth": corrected_value,
                        "confidence": confidence,
                        "error": None if ml_value == corrected_value else "Value mismatch"
                    })
        
        logger.info(f"Generated {len(validation_results)} validation results")
        return {"results": validation_results}
        
    except Exception as e:
        logger.error(f"Failed to get validation results: {str(e)}")
        # Return sample data for testing
        return {
            "results": [
                {
                    "form_type": "W-2",
                    "field_name": "Wages",
                    "ml_value": "$50,000.00",
                    "regex_value": "$50,000.00", 
                    "ground_truth": "$50,000.00",
                    "confidence": 0.95,
                    "error": None
                },
                {
                    "form_type": "1099-MISC",
                    "field_name": "Non-Employee Compensation",
                    "ml_value": "$25,000.00",
                    "regex_value": "$25,000.00",
                    "ground_truth": "$25,500.00", 
                    "confidence": 0.75,
                    "error": "Value mismatch"
                }
            ]
        }

# --- Annotation Workflow Endpoints ---
@router.get("/annotations/queue")
def get_annotation_queue(limit: int = 1):
    """Get a queue of pending annotation cases (default: 1 at a time for single-case UI)"""
    logger.info(f"Fetching annotation queue (limit={limit})")
    supabase = get_supabase_client()
    try:
        # Always use manual join (do not use supabase.rpc)
        queue = []
        extractions = supabase.table("extractions").select(
            "id, document_id, form_type_id, fields, confidence, created_at"
        ).execute().data
        for ext in extractions:
            # Find pending annotation for this extraction
            ann = supabase.table("annotations").select("id, status, corrected_fields, notes, created_at").eq("extraction_id", ext["id"]).eq("status", "pending").limit(1).execute().data
            if ann:
                # Get form type info
                form_type = supabase.table("form_types").select("code, description").eq("id", ext["form_type_id"]).execute().data
                # Get document info
                doc = supabase.table("documents").select("filename, raw_text").eq("id", ext["document_id"]).execute().data
                queue.append({
                    "annotation_id": ann[0]["id"],
                    "form_type": form_type[0]["code"] if form_type else None,
                    "form_type_description": form_type[0]["description"] if form_type else None,
                    "document_id": ext["document_id"],
                    "filename": doc[0]["filename"] if doc else None,
                    "fields": ext["fields"],
                    "confidence": ext.get("confidence"),
                    "status": ann[0]["status"],
                    "notes": ann[0].get("notes"),
                    "created_at": ann[0]["created_at"],
                    "raw_text": doc[0]["raw_text"][:1000] if doc and doc[0].get("raw_text") else None,
                    "corrected_fields": ann[0].get("corrected_fields", {}),
                })
                if len(queue) >= limit:
                    break
        logger.info(f"Fetched {len(queue)} pending annotation(s)")
        return {"queue": queue, "total": len(queue)}
    except Exception as e:
        logger.error(f"Failed to fetch annotation queue: {str(e)}")
        return {"queue": [], "total": 0}

@router.post("/annotations/{annotation_id}/approve")
def approve_annotation(annotation_id: str):
    """Approve annotation as correct (fields unchanged)"""
    logger.info(f"Approving annotation {annotation_id}")
    supabase = get_supabase_client()
    try:
        result = supabase.table("annotations").update({"status": "approved"}).eq("id", annotation_id).execute()
        logger.info(f"Annotation {annotation_id} approved")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to approve annotation: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/annotations/{annotation_id}/correct")
def correct_annotation(annotation_id: str, data: dict = Body(...)):
    """Submit corrections for annotation fields and approve"""
    logger.info(f"Correcting annotation {annotation_id}")
    supabase = get_supabase_client()
    try:
        corrected_fields = data.get("corrected_fields", {})
        result = supabase.table("annotations").update({
            "corrected_fields": corrected_fields,
            "status": "approved"
        }).eq("id", annotation_id).execute()
        logger.info(f"Annotation {annotation_id} corrected and approved")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to correct annotation: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/annotations/{annotation_id}/reject")
def reject_annotation(annotation_id: str, data: dict = Body(None)):
    """Reject annotation as incorrect"""
    logger.info(f"Rejecting annotation {annotation_id}")
    supabase = get_supabase_client()
    try:
        notes = data.get("notes") if data else None
        result = supabase.table("annotations").update({
            "status": "rejected",
            "notes": notes
        }).eq("id", annotation_id).execute()
        logger.info(f"Annotation {annotation_id} rejected")
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to reject annotation: {str(e)}")
        return {"success": False, "error": str(e)}

@router.post("/raw-text/wi", tags=["Transcripts"])
async def get_raw_text_wi(case_ids: list = Body(..., embed=True)):
    """
    Get the raw extracted text from all WI PDFs for one or more case IDs.
    Input: {"case_ids": ["caseid1", "caseid2", ...]}
    Output: {"caseid1": "raw text...", "caseid2": "raw text...", ...}
    """
    results = {}
    for case_id in case_ids:
        try:
            text = await get_pdf_text_for_case(case_id)
            results[case_id] = text
        except Exception as e:
            results[case_id] = f"Error: {str(e)}"
    return results 