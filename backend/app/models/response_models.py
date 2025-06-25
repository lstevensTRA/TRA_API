from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

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

    class Config:
        schema_extra = {
            "example": {
                "resolution_type": "IA",
                "resolution_amount": 450.0,
                "payment_terms": "Due on 28th of each month",
                "user_fee": 178.0,
                "start_date": "7/28/2025",
                "tax_years": ["2019", "2020", "2021", "2022", "2023"],
                "lien_status": "No liens filed",
                "account_balance": 35369.0,
                "payment_method": "Manual",
                "services_completed": [],
                "additional_terms": [
                    "1. To avoid default of your Installment Agreement, all future tax returns must be filed on",
                    "2. To prevent future balances, make sure to increase your IRS tax withholdings"
                ]
            }
        }

class CaseResult(BaseModel):
    case_id: int = Field(example=732334, description="Case ID")
    has_closing_letters: bool = Field(example=True, description="Whether case has closing letters")
    error: Optional[str] = Field(None, example=None, description="Error message if processing failed")
    resolution_summary: Optional[ResolutionSummary] = Field(None, description="Parsed resolution details")
    total_files: Optional[int] = Field(None, example=1, description="Number of closing letter files")

    class Config:
        schema_extra = {
            "example": {
                "case_id": 732334,
                "has_closing_letters": True,
                "error": None,
                "resolution_summary": ResolutionSummary.Config.schema_extra["example"],
                "total_files": 1
            }
        }

class BatchSummary(BaseModel):
    total_cases: int = Field(example=3, description="Total number of cases processed")
    successful_cases: int = Field(example=3, description="Number of successfully processed cases")
    cases_with_closing_letters: int = Field(example=2, description="Number of cases with closing letters")
    success_rate: float = Field(example=100.0, description="Success rate percentage")
    closing_letter_rate: float = Field(example=66.67, description="Percentage of cases with closing letters")
    resolution_type_distribution: Dict[str, int] = Field(example={"IA": 1}, description="Distribution of resolution types")
    average_account_balance: Optional[float] = Field(None, example=30945.97, description="Average account balance")

    class Config:
        schema_extra = {
            "example": {
                "total_cases": 3,
                "successful_cases": 3,
                "cases_with_closing_letters": 2,
                "success_rate": 100.0,
                "closing_letter_rate": 66.67,
                "resolution_type_distribution": {"IA": 1},
                "average_account_balance": 30945.97
            }
        }

class CompletedCasesResponse(BaseModel):
    total_completed_cases: int
    case_ids: List[int]

    class Config:
        schema_extra = {
            "example": {
                "total_completed_cases": 5,
                "case_ids": [123, 456, 789, 1011, 1213]
            }
        }

class BatchAnalysisResponse(BaseModel):
    total_completed_cases: int
    processed_cases: int
    start_index: int
    end_index: int
    results: List[Dict[str, Any]]
    summary: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "total_completed_cases": 5,
                "processed_cases": 3,
                "start_index": 0,
                "end_index": 3,
                "results": [
                    {"case_id": 123, "has_closing_letters": True, "resolution_summary": {"resolution_type": "IA"}},
                    {"case_id": 456, "has_closing_letters": False, "error": "No closing letter found"}
                ],
                "summary": {"success_rate": 66.67, "average_account_balance": 30945.97}
            }
        }

class CSVExportResponse(BaseModel):
    total_completed_cases: int
    processed_cases: int
    start_index: int
    end_index: int
    total_batches: int
    batch_size: int
    csv_data: str
    summary: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "total_completed_cases": 5,
                "processed_cases": 3,
                "start_index": 0,
                "end_index": 3,
                "total_batches": 2,
                "batch_size": 2,
                "csv_data": "Case ID,Has Closing Letters,Resolution Type\n123,True,IA\n456,False,\n",
                "summary": {"success_rate": 66.67, "average_account_balance": 30945.97}
            }
        }

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

    class Config:
        schema_extra = {
            "example": {
                "case_id": "123456",
                "transcript_type": "WI",
                "total_files": 2,
                "files": [
                    {
                        "index": 1,
                        "filename": "WI_2021.pdf",
                        "case_document_id": "abc123",
                        "owner": "TP"
                    },
                    {
                        "index": 2,
                        "filename": "WI_2020.pdf",
                        "case_document_id": "def456",
                        "owner": "S"
                    }
                ]
            }
        }

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
                    {
                        "index": 1,
                        "filename": "AT_2021.pdf",
                        "case_document_id": "abc123",
                        "owner": "TP"
                    },
                    {
                        "index": 2,
                        "filename": "AT_2020.pdf",
                        "case_document_id": "def456",
                        "owner": "S"
                    }
                ]
            }
        }
    } 