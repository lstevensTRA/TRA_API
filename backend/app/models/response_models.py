from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from datetime import datetime

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

class WIFormData(BaseModel):
    Form: str
    UniqueID: Optional[str] = Field(None, description="Unique identifier for the form")
    Label: Optional[str] = Field(None, description="Form label")
    Income: float = Field(0.0, description="Income amount")
    Withholding: float = Field(0.0, description="Withholding amount")
    Category: str = Field("", description="Income category")
    Fields: Dict[str, Any] = Field(default_factory=dict, description="Form fields")
    PayerBlurb: str = Field("", description="Payer information")
    Owner: str = Field("", description="Form owner (TP/S)")
    SourceFile: str = Field("", description="Source file name")

class WIYearSummary(BaseModel):
    number_of_forms: int
    se_income: float
    se_withholding: float
    non_se_income: float
    non_se_withholding: float
    other_income: float
    other_withholding: float
    total_income: float
    total_withholding: float
    estimated_agi: float

class WIOverallTotals(BaseModel):
    total_se_income: float
    total_non_se_income: float
    total_other_income: float
    total_income: float
    estimated_agi: float

class WISummary(BaseModel):
    total_years: int
    years_analyzed: List[str]
    total_forms: int
    by_year: Dict[str, WIYearSummary]
    overall_totals: WIOverallTotals

class WIAnalysisResponse(BaseModel):
    summary: WISummary
    years_data: Dict[str, List[WIFormData]]

class ATTransaction(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    code: Optional[str] = None

class ATRecord(BaseModel):
    tax_year: str
    account_balance: float
    accrued_interest: float
    accrued_penalty: float
    total_balance: float
    adjusted_gross_income: float
    taxable_income: float
    tax_per_return: float
    se_tax_taxpayer: float
    se_tax_spouse: float
    total_se_tax: float
    filing_status: str
    processing_date: str
    transactions: List[ATTransaction]
    owner: str
    source_file: str

class ATAnalysisResponse(BaseModel):
    at_records: List[ATRecord]

class ClientInfo(BaseModel):
    case_id: str = Field("", description="Case ID")
    full_name: str = Field("", description="Full name")
    first_name: str = Field("", description="First name")
    middle_name: str = Field("", description="Middle name")
    last_name: str = Field("", description="Last name")
    ssn: str = Field("", description="Social Security Number")
    ein: str = Field("", description="Employer Identification Number")
    marital_status: Optional[str] = Field(None, description="Marital status")
    business_name: str = Field("", description="Business name")
    business_type: str = Field("", description="Business type")
    business_address: str = Field("", description="Business address")

class ContactInfo(BaseModel):
    primary_phone: str = Field("", description="Primary phone number")
    home_phone: str = Field("", description="Home phone number")
    work_phone: str = Field("", description="Work phone number")
    email: str = Field("", description="Email address")
    address: Dict[str, str] = Field(default_factory=dict, description="Address information")
    sms_permitted: bool = Field(False, description="SMS permission")
    best_time_to_call: str = Field("", description="Best time to call")

class TaxInfo(BaseModel):
    total_liability: Optional[float] = Field(None, description="Total tax liability")
    years_owed: List[str] = Field(default_factory=list, description="Years owed")
    unfiled_years: List[str] = Field(default_factory=list, description="Unfiled years")
    status_id: int = Field(0, description="Status ID")
    status_name: str = Field("", description="Status name")
    tax_type: str = Field("", description="Tax type")

class FinancialProfile(BaseModel):
    income: Dict[str, float] = Field(default_factory=dict, description="Income information")
    expenses: Dict[str, Any] = Field(default_factory=dict, description="Expense information")
    assets: Dict[str, Any] = Field(default_factory=dict, description="Asset information")
    business: Dict[str, Any] = Field(default_factory=dict, description="Business information")
    family: Dict[str, Any] = Field(default_factory=dict, description="Family information")

class CaseManagement(BaseModel):
    sale_date: str = Field("", description="Sale date")
    created_date: str = Field("", description="Created date")
    modified_date: str = Field("", description="Modified date")
    days_in_status: int = Field(0, description="Days in current status")
    source_name: str = Field("", description="Source name")
    team: Dict[str, Any] = Field(default_factory=dict, description="Team information")

class RawData(BaseModel):
    total_tax_debt: Optional[float] = Field(None, description="Total tax debt")
    client_agi: Optional[float] = Field(None, description="Client AGI")
    current_filing_status: Optional[str] = Field(None, description="Current filing status")
    currency: Optional[str] = Field(None, description="Currency")
    extracted_at: str = Field("", description="Extraction timestamp")
    url: str = Field("", description="Source URL")
    success: bool = Field(False, description="Success status")

class ClientData(BaseModel):
    client_info: ClientInfo = Field(default_factory=ClientInfo, description="Client information")
    contact_info: ContactInfo = Field(default_factory=ContactInfo, description="Contact information")
    tax_info: TaxInfo = Field(default_factory=TaxInfo, description="Tax information")
    financial_profile: FinancialProfile = Field(default_factory=FinancialProfile, description="Financial profile")
    case_management: CaseManagement = Field(default_factory=CaseManagement, description="Case management")
    raw_data: RawData = Field(default_factory=RawData, description="Raw data")

class ComparisonInfo(BaseModel):
    most_recent_year: str = Field("", description="Most recent tax year")
    client_annual_income: Optional[float] = Field(None, description="Client annual income")
    wi_total_income: float = Field(0.0, description="WI total income")
    at_agi: Optional[float] = Field(None, description="AT AGI")
    transcript_income_used: float = Field(0.0, description="Transcript income used")
    transcript_source: str = Field("", description="Transcript source")
    percentage_difference: Optional[float] = Field(None, description="Percentage difference")

class IncomeComparisonResponse(BaseModel):
    comparison_info: ComparisonInfo = Field(default_factory=ComparisonInfo, description="Comparison information")
    client_data: ClientData = Field(default_factory=ClientData, description="Client data")
    wi_summary: Dict[str, Any] = Field(default_factory=dict, description="WI summary")
    at_data: List[Any] = Field(default_factory=list, description="AT data")

class ClosingNote(BaseModel):
    activity_id: Optional[int] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    created_date: Optional[str] = None
    created_by: Optional[str] = None

class CaseClosingNotesResponse(BaseModel):
    case_id: str
    total_activities: int
    closing_notes: List[ClosingNote]
    resolution_details: ResolutionSummary

class CaseActivity(BaseModel):
    activity_id: Optional[int] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    created_date: Optional[str] = None
    created_by: Optional[str] = None
    activity_type: Optional[str] = None

class CaseActivitiesResponse(BaseModel):
    case_id: str
    total_activities: int
    filtered_activities: int
    activities: List[CaseActivity]
    filters_applied: Dict[str, Any]

class TaxInvestigationClientInfo(BaseModel):
    name: str = Field("", description="Client name")
    annual_income: Optional[float] = Field(None, description="Annual income")
    employer: str = Field("", description="Employer")
    case_id: str = Field("", description="Case ID")
    ssn: str = Field("", description="Social Security Number")
    address: str = Field("", description="Address")
    phone: str = Field("", description="Phone number")
    email: str = Field("", description="Email address")
    marital_status: str = Field("", description="Marital status")
    filing_status: str = Field("", description="Filing status")
    total_liability: Optional[float] = Field(None, description="Total liability")
    years_owed: List[str] = Field(default_factory=list, description="Years owed")
    unfiled_years: List[str] = Field(default_factory=list, description="Unfiled years")
    status: str = Field("", description="Status")
    resolution_type: str = Field("", description="Resolution type")
    resolution_amount: float = Field(0.0, description="Resolution amount")
    payment_terms: str = Field("", description="Payment terms")
    created_date: str = Field("", description="Created date")
    modified_date: str = Field("", description="Modified date")

class Discrepancy(BaseModel):
    type: str
    description: str
    severity: str
    source1: str
    source2: str
    value1: Any
    value2: Any

class ComparisonSummary(BaseModel):
    total_discrepancies: int
    critical_discrepancies: int
    data_sources_available: List[str]

class TaxInvestigationComparison(BaseModel):
    income_discrepancies: List[Discrepancy]
    employment_discrepancies: List[Discrepancy]
    tax_year_discrepancies: List[Discrepancy]
    balance_discrepancies: List[Discrepancy]
    summary: ComparisonSummary

class TaxInvestigationCompareResponse(BaseModel):
    case_id: str
    client_info: TaxInvestigationClientInfo
    ti_data: Dict[str, Any]
    wi_data: Dict[str, Any]
    at_data: Dict[str, Any]
    comparison: TaxInvestigationComparison

class ClosingLetter(BaseModel):
    letter_id: str
    letter_type: str
    subject: str
    content: str
    generated_date: str
    status: str

class ClosingLettersResponse(BaseModel):
    case_id: str
    total_letters: int
    letters: List[ClosingLetter]
    generated_at: str

class BatchStatusResponse(BaseModel):
    batch_id: str
    status: str
    total_cases: int
    processed_cases: int
    successful_cases: int
    failed_cases: int
    started_at: str
    completed_at: Optional[str] = None
    errors: List[str]

class ComprehensiveAnalysisResponse(BaseModel):
    case_id: str
    analysis_type: str
    summary: Dict[str, Any]
    detailed_analysis: Dict[str, Any]
    recommendations: List[str]
    generated_at: str

class ClientAnalysisResponse(BaseModel):
    case_id: str
    filing_status_detected: Optional[str] = None
    tp_spouse_breakdown: Dict[str, Any]
    suggested_filing_status: Optional[str] = None
    tps_analysis_enabled: bool
    file_patterns: Dict[str, Any]
    logiqs_client_info: Optional[Dict[str, Any]] = None

# Standardized Error Response Model
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Optional error code for categorization")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the error")
    status_code: int = Field(500, description="HTTP status code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Authentication required. Please log in first.",
                "error_code": "AUTH_REQUIRED",
                "timestamp": "2025-06-26T17:35:05.347536",
                "status_code": 401
            }
        }
    }

# Standardized Success Response Model
class SuccessResponse(BaseModel):
    message: str = Field(..., description="Success message")
    status: str = Field("success", description="Status indicator")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Timestamp of the response")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional response data")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Operation completed successfully",
                "status": "success",
                "timestamp": "2025-06-26T17:35:05.347536",
                "data": {"case_id": "12345", "status": "processed"}
            }
        }
    }

class ClientProfileTeam(BaseModel):
    set_officer: Optional[str] = None
    case_advocate: Optional[str] = None
    tax_pro: Optional[str] = None
    tax_preparer: Optional[str] = None
    ti_agent: Optional[str] = None
    offer_analyst: Optional[str] = None
    team_name: Optional[str] = None

class ClientProfileCaseManagement(BaseModel):
    case_id: Optional[str] = None
    status: Optional[str] = None
    sale_date: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    days_in_status: Optional[int] = None
    team: Optional[ClientProfileTeam] = None
    source_name: Optional[str] = None

class ClientProfileTaxInfo(BaseModel):
    total_liability: Optional[float] = None
    years_owed: Optional[List[str]] = None

class ClientProfileExpenses(BaseModel):
    housing: Optional[float] = None
    housing_utilities: Optional[float] = None
    auto_operating: Optional[float] = None
    food: Optional[float] = None
    personal_care: Optional[float] = None
    apparel: Optional[float] = None
    other1: Optional[float] = None
    other1_label: Optional[str] = None
    other2: Optional[float] = None
    other2_label: Optional[str] = None
    total: Optional[float] = None

class ClientProfileFinancialProfile(BaseModel):
    taxpayer_income: Optional[float] = None
    spouse_income: Optional[float] = None
    monthly_net: Optional[float] = None
    yearly_income: Optional[float] = None
    expenses: Optional[ClientProfileExpenses] = None

class ClientProfileAddress(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None

class ClientProfileContact(BaseModel):
    primary_phone: Optional[str] = None
    home_phone: Optional[str] = None
    work_phone: Optional[str] = None
    email: Optional[str] = None
    sms_permitted: Optional[bool] = None
    best_time_to_call: Optional[str] = None

class ClientProfilePersonal(BaseModel):
    marital_status: Optional[str] = None
    household_size: Optional[int] = None
    members_under_65: Optional[int] = None
    members_over_65: Optional[int] = None
    county_id: Optional[int] = None
    county_name: Optional[str] = None

class ClientProfileResponse(BaseModel):
    personal: Optional[ClientProfilePersonal] = None
    contact: Optional[ClientProfileContact] = None
    address: Optional[ClientProfileAddress] = None
    financial_profile: Optional[ClientProfileFinancialProfile] = None
    tax_info: Optional[ClientProfileTaxInfo] = None
    case_management: Optional[ClientProfileCaseManagement] = None
    assets: Optional[Dict[str, Any]] = None
    income_details: Optional[Dict[str, Any]] = None
    asset_details: Optional[Dict[str, Any]] = None

class CountyResponse(BaseModel):
    CountyId: int = Field(..., description="County ID")
    CountyName: str = Field(..., description="County name")
    State: Optional[str] = Field(None, description="State code")
    RegionId: int = Field(0, description="Region ID")
    ExpHousingOne: float = Field(0, description="Housing expense for 1 person")
    ExpHousingTwo: float = Field(0, description="Housing expense for 2 people")
    ExpHousingThree: float = Field(0, description="Housing expense for 3 people")
    ExpHousingFour: float = Field(0, description="Housing expense for 4 people")
    ExpHousingFive: float = Field(0, description="Housing expense for 5+ people")

    model_config = {
        "json_schema_extra": {
            "example": {
                "CountyId": 185,
                "CountyName": "Alameda County",
                "State": "CA",
                "RegionId": 0,
                "ExpHousingOne": 1500.0,
                "ExpHousingTwo": 1800.0,
                "ExpHousingThree": 2100.0,
                "ExpHousingFour": 2400.0,
                "ExpHousingFive": 2700.0
            }
        }
    }

class IRSStandardsResponse(BaseModel):
    Error: bool = Field(False, description="Whether the request resulted in an error")
    Result: Optional[Dict[str, Any]] = Field(None, description="IRS Standards data")
    Message: Optional[str] = Field(None, description="Error message if applicable")

    model_config = {
        "json_schema_extra": {
            "example": {
                "Error": False,
                "Result": {
                    "data": {
                        "Housing": 1200.0,
                        "OperatingCostCar": 500.0,
                        "Food": 800.0,
                        "PersonalCare": 200.0,
                        "Apparel": 150.0,
                        "Misc": 100.0,
                        "Housekeeping": 50.0,
                        "PublicTrans": 0.0,
                        "HealthOutOfPocket": 100.0
                    }
                },
                "Message": None
            }
        }
    }

class ExpenseCategoryComparison(BaseModel):
    real_expense: float = Field(0.0, description="Real expense amount")
    irs_standard: float = Field(0.0, description="IRS Standard amount")
    allowable_amount: float = Field(0.0, description="Final allowable amount (higher of real vs IRS)")
    source_used: str = Field("", description="Source used: 'real' or 'irs'")

class ExpenseBreakdown(BaseModel):
    category_comparisons: Dict[str, ExpenseCategoryComparison] = Field(default_factory=dict, description="Category-by-category comparison")
    total_real_expenses: float = Field(0.0, description="Total real expenses")
    total_irs_standards: float = Field(0.0, description="Total IRS Standards")
    total_allowable: float = Field(0.0, description="Total allowable expenses")

class ClientProfileSummary(BaseModel):
    household_size: Optional[int] = Field(None, description="Total household size")
    members_under_65: Optional[int] = Field(None, description="Number of household members under 65")
    members_over_65: Optional[int] = Field(None, description="Number of household members 65 and over")
    state: Optional[str] = Field(None, description="State")
    city: Optional[str] = Field(None, description="City")
    county_id: Optional[int] = Field(None, description="County ID")
    county_name: Optional[str] = Field(None, description="County name")

class DisposableIncomeResponse(BaseModel):
    case_id: str = Field(..., description="Case ID")
    calculation_date: str = Field(..., description="Date and time of calculation")
    monthly_income: float = Field(0.0, description="Monthly net income")
    total_allowable_expenses: float = Field(0.0, description="Total allowable expenses (higher of real vs IRS Standards)")
    monthly_disposable_income: float = Field(0.0, description="Monthly disposable income (income - allowable expenses)")
    expense_breakdown: ExpenseBreakdown = Field(default_factory=ExpenseBreakdown, description="Detailed expense breakdown")
    client_profile: ClientProfileSummary = Field(default_factory=ClientProfileSummary, description="Client profile summary")
    irs_standards_used: Optional[Dict[str, Any]] = Field(None, description="IRS Standards data used in calculation")
    real_expenses: Optional[Dict[str, Any]] = Field(None, description="Real expenses from client profile")

    model_config = {
        "json_schema_extra": {
            "example": {
                "case_id": "123456",
                "calculation_date": "2024-01-15T10:30:00",
                "monthly_income": 5000.0,
                "total_allowable_expenses": 3200.0,
                "monthly_disposable_income": 1800.0,
                "expense_breakdown": {
                    "category_comparisons": {
                        "housing": {
                            "real_expense": 1500.0,
                            "irs_standard": 1200.0,
                            "allowable_amount": 1500.0,
                            "source_used": "real"
                        },
                        "food": {
                            "real_expense": 600.0,
                            "irs_standard": 800.0,
                            "allowable_amount": 800.0,
                            "source_used": "irs"
                        }
                    },
                    "total_real_expenses": 2800.0,
                    "total_irs_standards": 3200.0,
                    "total_allowable": 3200.0
                },
                "client_profile": {
                    "household_size": 3,
                    "members_under_65": 2,
                    "members_over_65": 1,
                    "state": "WI",
                    "city": "Milwaukee",
                    "county_id": 79,
                    "county_name": "Milwaukee County"
                },
                "irs_standards_used": {
                    "data": {
                        "Housing": 1200.0,
                        "Food": 800.0,
                        "OperatingCostCar": 500.0
                    }
                },
                "real_expenses": {
                    "housing": 1500.0,
                    "food": 600.0,
                    "auto_operating": 400.0
                }
            }
        }
    }

class AllTranscriptsResponse(BaseModel):
    case_id: str
    wi_transcripts: Optional[WITranscriptResponse] = None
    at_transcripts: Optional[ATTranscriptResponse] = None

class SMSLog(BaseModel):
    CaseID: int
    SMSLogID: int
    MsgDirection: str
    MsgDateSent: str
    FormattedMsgDateSent: str
    MsgBody: str
    ClientName: str
    UserName: str
    MsgStatus: int
    MsgStatusName: str

class SMSLogsResponse(BaseModel):
    case_id: int
    logs: List[SMSLog]

    class Config:
        schema_extra = {
            "example": {
                "case_id": 1124144,
                "logs": [
                    {
                        "CaseID": 1124144,
                        "SMSLogID": 3375862,
                        "MsgDirection": "outbound-api",
                        "MsgDateSent": "2025-05-09T11:01:00.957",
                        "FormattedMsgDateSent": "5/9/2025 11:01 AM",
                        "MsgBody": "https://esignapi.com/auth.html?guid=_HfHmMaCjU6s13vXckx69g . Reply STOP to unsubscribe",
                        "ClientName": "Arlys Kuehn",
                        "UserName": "Steve Baker",
                        "MsgStatus": 1,
                        "MsgStatusName": "Sent"
                    }
                ]
            }
        } 