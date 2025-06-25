from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI()

# --- /transcripts/wi/{case_id} ---
class WITranscriptFile(BaseModel):
    index: int
    filename: str
    case_document_id: str
    owner: str

class WITranscriptResponse(BaseModel):
    case_id: str
    transcript_type: str
    total_files: int
    files: List[WITranscriptFile]
    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "transcript_type": "WI",
                "total_files": 2,
                "files": [
                    {"index": 1, "filename": "WI_2021.pdf", "case_document_id": "abc123", "owner": "TP"},
                    {"index": 2, "filename": "WI_2020.pdf", "case_document_id": "def456", "owner": "S"}
                ]
            }
        }
    }

@app.get("/transcripts/wi/{case_id}", response_model=WITranscriptResponse)
def get_wi_transcripts(case_id: str):
    return WITranscriptResponse(
        case_id=case_id,
        transcript_type="WI",
        total_files=2,
        files=[
            WITranscriptFile(index=1, filename="WI_2021.pdf", case_document_id="abc123", owner="TP"),
            WITranscriptFile(index=2, filename="WI_2020.pdf", case_document_id="def456", owner="S"),
        ]
    )

# --- /transcripts/at/{case_id} ---
class ATTranscriptFile(BaseModel):
    index: int
    filename: str
    case_document_id: str
    owner: str

class ATTranscriptResponse(BaseModel):
    case_id: str
    transcript_type: str
    total_files: int
    files: List[ATTranscriptFile]
    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "transcript_type": "AT",
                "total_files": 2,
                "files": [
                    {"index": 1, "filename": "AT_2021.pdf", "case_document_id": "abc123", "owner": "TP"},
                    {"index": 2, "filename": "AT_2020.pdf", "case_document_id": "def456", "owner": "S"}
                ]
            }
        }
    }

@app.get("/transcripts/at/{case_id}", response_model=ATTranscriptResponse)
def get_at_transcripts(case_id: str):
    return ATTranscriptResponse(
        case_id=case_id,
        transcript_type="AT",
        total_files=2,
        files=[
            ATTranscriptFile(index=1, filename="AT_2021.pdf", case_document_id="abc123", owner="TP"),
            ATTranscriptFile(index=2, filename="AT_2020.pdf", case_document_id="def456", owner="S"),
        ]
    )

# --- /transcripts/{case_id} ---
class TranscriptFile(BaseModel):
    index: int
    filename: str
    case_document_id: str
    transcript_type: str
    owner: str

class AllTranscriptsResponse(BaseModel):
    case_id: str
    total_files: int
    wi_files: int
    at_files: int
    files: List[TranscriptFile]
    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "total_files": 4,
                "wi_files": 2,
                "at_files": 2,
                "files": [
                    {"index": 1, "filename": "WI_2021.pdf", "case_document_id": "abc123", "transcript_type": "WI", "owner": "TP"},
                    {"index": 2, "filename": "WI_2020.pdf", "case_document_id": "def456", "transcript_type": "WI", "owner": "S"},
                    {"index": 3, "filename": "AT_2021.pdf", "case_document_id": "ghi789", "transcript_type": "AT", "owner": "TP"},
                    {"index": 4, "filename": "AT_2020.pdf", "case_document_id": "jkl012", "transcript_type": "AT", "owner": "S"}
                ]
            }
        }
    }

@app.get("/transcripts/{case_id}", response_model=AllTranscriptsResponse)
def get_all_transcripts(case_id: str):
    return AllTranscriptsResponse(
        case_id=case_id,
        total_files=4,
        wi_files=2,
        at_files=2,
        files=[
            TranscriptFile(index=1, filename="WI_2021.pdf", case_document_id="abc123", transcript_type="WI", owner="TP"),
            TranscriptFile(index=2, filename="WI_2020.pdf", case_document_id="def456", transcript_type="WI", owner="S"),
            TranscriptFile(index=3, filename="AT_2021.pdf", case_document_id="ghi789", transcript_type="AT", owner="TP"),
            TranscriptFile(index=4, filename="AT_2020.pdf", case_document_id="jkl012", transcript_type="AT", owner="S"),
        ]
    )

# --- /wi/{case_id} ---
class WIYearSummary(BaseModel):
    tax_year: str
    total_income: float
    form_count: int

class WIAnalysisResponse(BaseModel):
    case_id: str
    summary: List[WIYearSummary]
    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "summary": [
                    {"tax_year": "2021", "total_income": 50000.0, "form_count": 5},
                    {"tax_year": "2020", "total_income": 48000.0, "form_count": 4}
                ]
            }
        }
    }

@app.get("/wi/{case_id}", response_model=WIAnalysisResponse)
def get_wi_analysis(case_id: str):
    return WIAnalysisResponse(
        case_id=case_id,
        summary=[
            WIYearSummary(tax_year="2021", total_income=50000.0, form_count=5),
            WIYearSummary(tax_year="2020", total_income=48000.0, form_count=4),
        ]
    )

# --- /at/{case_id} ---
class ATYearSummary(BaseModel):
    tax_year: str
    total_balance: float
    transaction_count: int

class ATAnalysisResponse(BaseModel):
    case_id: str
    summary: List[ATYearSummary]
    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "summary": [
                    {"tax_year": "2021", "total_balance": 1200.0, "transaction_count": 12},
                    {"tax_year": "2020", "total_balance": 0.0, "transaction_count": 10}
                ]
            }
        }
    }

@app.get("/at/{case_id}", response_model=ATAnalysisResponse)
def get_at_analysis(case_id: str):
    return ATAnalysisResponse(
        case_id=case_id,
        summary=[
            ATYearSummary(tax_year="2021", total_balance=1200.0, transaction_count=12),
            ATYearSummary(tax_year="2020", total_balance=0.0, transaction_count=10),
        ]
    ) 