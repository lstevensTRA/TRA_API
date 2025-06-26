"""
Enhanced Tax Investigation (TI) parsing utility
Based on analysis of TI logs to improve extraction of fees, versions, and other data
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class EnhancedTIParser:
    """Enhanced TI parsing with improved regex patterns based on log analysis"""
    
    @staticmethod
    def extract_ti_version_from_filename(filename: str) -> Optional[str]:
        """
        Extract TI version from filename with enhanced patterns
        
        Args:
            filename: The TI filename (e.g., "TI 6.7 - David & Paula.pdf", "TI 7.2 - Sanderson.pdf")
            
        Returns:
            Version string (e.g., "6.7", "7.2") or None if not found
        """
        if not filename:
            return None
            
        logger.info(f"🔍 Extracting TI version from filename: '{filename}'")
        
        # Enhanced patterns for TI version detection based on logs
        patterns = [
            r"TI\s+(\d+\.\d+)",  # TI 6.7, TI 7.2, etc.
            r"TI\s*(\d+)\.(\d+)",  # TI 6.7, TI 7.2, etc.
            r"TI\s*(\d+\.\d+)",  # TI 6.7, TI 7.2, etc.
            r"TI\s+(\d+)\s*-\s*",  # TI 6 - David & Paula
            r"TI\s*(\d+)",  # TI 6, TI 7, etc.
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
                return ti_version
            else:
                logger.info(f"❌ Pattern {i+1} failed")
        
        logger.warning(f"⚠️ Could not extract version from filename: {filename}")
        return None
    
    @staticmethod
    def extract_total_resolution_fees(ti_text: str) -> Optional[float]:
        """
        Extract total resolution fees with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Fee amount as float or None if not found
        """
        # Enhanced patterns for total resolution fees based on logs
        fees_patterns = [
            r"Total\s+Resolution\s+Fees\s+\$?([\d,]+\.?\d*)",  # Standard format
            r"Total\s+Resolution\s+Fees\$?([\d,]+\.?\d*)",  # No space before $
            r"Resolution\s+Fees\s+\$?([\d,]+\.?\d*)",  # Without "Total"
            r"Fees\s+\$?([\d,]+\.?\d*)",  # Just "Fees"
        ]
        
        for pattern in fees_patterns:
            fees_match = re.search(pattern, ti_text, re.IGNORECASE)
            if fees_match:
                try:
                    fee_amount = float(fees_match.group(1).replace(",", ""))
                    logger.info(f"✅ Found total resolution fees: ${fee_amount}")
                    return fee_amount
                except ValueError:
                    continue
        
        logger.warning("⚠️ Could not extract total resolution fees")
        return None
    
    @staticmethod
    def extract_current_tax_liability(ti_text: str) -> Optional[float]:
        """
        Extract current tax liability with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Liability amount as float or None if not found
        """
        current_liability_patterns = [
            r"Current\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)",  # Standard format
            r"Current\s+Tax\s+Liability\$?([\d,]+\.?\d*)",  # No space before $
            r"Current\s+Liability\s+\$?([\d,]+\.?\d*)",  # Without "Tax"
        ]
        
        for pattern in current_liability_patterns:
            current_liability_match = re.search(pattern, ti_text, re.IGNORECASE)
            if current_liability_match:
                try:
                    liability_amount = float(current_liability_match.group(1).replace(",", ""))
                    logger.info(f"✅ Found current tax liability: ${liability_amount}")
                    return liability_amount
                except ValueError:
                    continue
        
        logger.warning("⚠️ Could not extract current tax liability")
        return None
    
    @staticmethod
    def extract_current_and_projected_liability(ti_text: str) -> Optional[float]:
        """
        Extract current & projected tax liability with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Liability amount as float or None if not found
        """
        projected_patterns = [
            r"Current\s+&\s+Projected\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)",  # Standard format
            r"Current\s+&\s+Projected\s+Tax\s+Liability\$?([\d,]+\.?\d*)",  # No space before $
            r"Current\s+and\s+Projected\s+Tax\s+Liability\s+\$?([\d,]+\.?\d*)",  # "and" instead of "&"
            r"Current\s+and\s+Projected\s+Tax\s+Liability\$?([\d,]+\.?\d*)",  # "and" without space
        ]
        
        for pattern in projected_patterns:
            projected_match = re.search(pattern, ti_text, re.IGNORECASE)
            if projected_match:
                try:
                    liability_amount = float(projected_match.group(1).replace(",", ""))
                    logger.info(f"✅ Found current & projected tax liability: ${liability_amount}")
                    return liability_amount
                except ValueError:
                    continue
        
        logger.warning("⚠️ Could not extract current & projected tax liability")
        return None
    
    @staticmethod
    def extract_total_individual_balance(ti_text: str) -> Optional[float]:
        """
        Extract total individual balance with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Balance amount as float or None if not found
        """
        total_balance_patterns = [
            r"Total\s+Individual\s+Balance:\s*\$?([\d,]+\.?\d*)",  # Standard format
            r"Total\s+Individual\s+Balance\s+\$?([\d,]+\.?\d*)",  # No colon
            r"Total\s+Current\s+Balance\s+\$?([\d,]+\.?\d*)",  # "Current" instead of "Individual"
        ]
        
        for pattern in total_balance_patterns:
            total_balance_match = re.search(pattern, ti_text, re.IGNORECASE)
            if total_balance_match:
                try:
                    balance_amount = float(total_balance_match.group(1).replace(",", ""))
                    logger.info(f"✅ Found total individual balance: ${balance_amount}")
                    return balance_amount
                except ValueError:
                    continue
        
        logger.warning("⚠️ Could not extract total individual balance")
        return None
    
    @staticmethod
    def extract_projected_unfiled_balances(ti_text: str) -> Optional[float]:
        """
        Extract projected unfiled balances with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Balance amount as float or None if not found
        """
        unfiled_patterns = [
            r"Projected\s+Unfiled\s+Balances:\s*\$?([\d,]+\.?\d*)",  # Standard format
            r"Projected\s+Unfiled\s+Balances\s+\$?([\d,]+\.?\d*)",  # No colon
            r"Unfiled\s+Balances:\s*\$?([\d,]+\.?\d*)",  # Without "Projected"
        ]
        
        for pattern in unfiled_patterns:
            unfiled_match = re.search(pattern, ti_text, re.IGNORECASE)
            if unfiled_match:
                try:
                    balance_amount = float(unfiled_match.group(1).replace(",", ""))
                    logger.info(f"✅ Found projected unfiled balances: ${balance_amount}")
                    return balance_amount
                except ValueError:
                    continue
        
        logger.warning("⚠️ Could not extract projected unfiled balances")
        return None
    
    @staticmethod
    def extract_interest_calculations(ti_text: str) -> Dict[str, float]:
        """
        Extract interest calculations with enhanced patterns
        
        Args:
            ti_text: Raw TI text content
            
        Returns:
            Dictionary with daily, monthly, and yearly interest amounts
        """
        interest_calculations = {}
        
        # Enhanced interest patterns
        daily_interest_match = re.search(r"Daily:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if daily_interest_match:
            try:
                interest_calculations["daily_interest"] = float(daily_interest_match.group(1).replace(",", ""))
            except ValueError:
                pass
        
        monthly_interest_match = re.search(r"Monthly:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if monthly_interest_match:
            try:
                interest_calculations["monthly_interest"] = float(monthly_interest_match.group(1).replace(",", ""))
            except ValueError:
                pass
        
        yearly_interest_match = re.search(r"Yearly:\s*\$?([\d,]+\.?\d*)", ti_text, re.IGNORECASE)
        if yearly_interest_match:
            try:
                interest_calculations["yearly_interest"] = float(yearly_interest_match.group(1).replace(",", ""))
            except ValueError:
                pass
        
        return interest_calculations
    
    @staticmethod
    def extract_tax_years_enhanced(ti_text: str, ti_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Extract tax years with enhanced patterns for TI 6.x and 7.x
        
        Args:
            ti_text: Raw TI text content
            ti_version: TI version for version-specific parsing
            
        Returns:
            List of tax year dictionaries
        """
        tax_years = []
        
        if ti_version and float(ti_version) >= 6.0:
            # Enhanced new format parsing for TI 6.x and 7.x
            # Look for patterns like: "2023 Filed MFJ PWR $0.00 W-2 1099-S SSA 1099-R g div"
            year_pattern = r"(\d{4})\s+(Filed|Unfiled|Amended|Not Req)\s+([A-Z]{0,4})\s*([A-Za-z]*)\s*\$?([\d,]+\.?\d*|Refund|-[\d,]+\.?\d*)\s*(\d{1,2}\/\d{1,2}\/\d{4})?\s*([^$\d]*?)(?=\d{4}|W-2|1099|\s*$)"
            year_matches = re.finditer(year_pattern, ti_text, re.IGNORECASE)
            
            for match in year_matches:
                year_data = {
                    "year": int(match.group(1)),
                    "return_status": match.group(2),
                    "filing_status": match.group(3) if match.group(3) else None,
                    "additional_status": match.group(4) if match.group(4) else None,  # PWR, etc.
                    "current_balance": match.group(5),
                    "csed_date": match.group(6),
                    "reason_status": match.group(7).strip() if match.group(7) else None,
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
                next_year_match = re.search(rf"\d{{4}}\s+(Filed|Unfiled|Amended|Not Req)", ti_text[year_start:])
                if next_year_match:
                    year_end = year_start + next_year_match.start()
                
                year_text = ti_text[year_start:year_end]
                wage_forms = re.findall(r"\b(W-2[A-Z]*|1099-[A-Z]+(?:credit)?|SSA|401K|W-2G)\b", year_text, re.IGNORECASE)
                year_data["wage_information"] = list(set(wage_forms))
                
                tax_years.append(year_data)
        
        # Sort by year descending
        tax_years.sort(key=lambda x: x["year"], reverse=True)
        
        return tax_years
    
    @staticmethod
    def extract_resolution_plan_enhanced(ti_text: str, ti_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract resolution plan with enhanced patterns for TI 6.x and 7.x
        
        Args:
            ti_text: Raw TI text content
            ti_version: TI version for version-specific parsing
            
        Returns:
            Resolution plan dictionary
        """
        resolution_plan = {"steps": [], "resolution_opportunities": [], "special_notes": []}
        
        if ti_version and float(ti_version) >= 6.0:
            # Enhanced new format parsing for TI 6.x and 7.x
            # Look for patterns like: "1 INT COSTInterest Cost of Inaction"
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
            opportunities = re.findall(r"\b(Offer In Compromise|OIC|CNC|PPIA|PENAB|Amended Returns|Installment Agreement|IA)\b", ti_text, re.IGNORECASE)
            resolution_plan["resolution_opportunities"] = list(set(opportunities))
            
            # Extract special notes
            notes_pattern = r"•\s*([^•\n]+)|^\d+\.\s*([^\n]+)"
            notes_matches = re.finditer(notes_pattern, ti_text, re.MULTILINE)
            for match in notes_matches:
                note = match.group(1) or match.group(2)
                if note and len(note.strip()) > 10:
                    resolution_plan["special_notes"].append(note.strip())
        
        return resolution_plan
    
    @staticmethod
    def parse_ti_text_enhanced(ti_text: str, filename: str = "") -> Dict[str, Any]:
        """
        Enhanced TI text parsing with improved regex patterns
        
        Args:
            ti_text: Raw TI text content
            filename: TI filename for version detection
            
        Returns:
            Structured TI data dictionary
        """
        logger.info(f"🔍 Starting enhanced TI text parsing...")
        result = {}
        
        # Extract TI version
        ti_version = EnhancedTIParser.extract_ti_version_from_filename(filename)
        logger.info(f"📋 TI Version: {ti_version} from filename: {filename}")
        
        # === CASE METADATA ===
        case_metadata = {}
        
        # Case ID
        case_match = re.search(r"Case\s*#\s*(\d+)", ti_text, re.IGNORECASE)
        if case_match:
            case_metadata["case_id"] = case_match.group(1)
        
        # File info
        case_metadata["file_info"] = {
            "filename": filename,
            "case_document_id": 0,  # Will be set by endpoint
            "file_comment": "",
            "ti_version": ti_version
        }
        
        # Investigation dates
        investigation_dates = {}
        ti_completed_match = re.search(r"Date\s+TI\s+Completed\s+(\d{1,2}\/\d{1,2}\/\d{4})", ti_text, re.IGNORECASE)
        if ti_completed_match:
            investigation_dates["ti_completed"] = ti_completed_match.group(1)
        
        resolution_completed_match = re.search(r"Date\s+RESO\s+Plan\s+Completed:\s*(\d{1,2}\/\d{1,2}\/\d{4})", ti_text, re.IGNORECASE)
        if resolution_completed_match:
            investigation_dates["resolution_plan_completed"] = resolution_completed_match.group(1)
        
        if investigation_dates:
            case_metadata["investigation_dates"] = investigation_dates
        
        # Personnel
        personnel = {}
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
        
        # Extract all financial data using enhanced methods
        total_resolution_fees = EnhancedTIParser.extract_total_resolution_fees(ti_text)
        if total_resolution_fees:
            tax_liability_summary["total_resolution_fees"] = total_resolution_fees
        
        current_tax_liability = EnhancedTIParser.extract_current_tax_liability(ti_text)
        if current_tax_liability:
            tax_liability_summary["current_tax_liability"] = current_tax_liability
        
        current_and_projected_liability = EnhancedTIParser.extract_current_and_projected_liability(ti_text)
        if current_and_projected_liability:
            tax_liability_summary["current_and_projected_tax_liability"] = current_and_projected_liability
        
        total_individual_balance = EnhancedTIParser.extract_total_individual_balance(ti_text)
        if total_individual_balance:
            tax_liability_summary["total_individual_balance"] = total_individual_balance
        
        projected_unfiled_balances = EnhancedTIParser.extract_projected_unfiled_balances(ti_text)
        if projected_unfiled_balances:
            tax_liability_summary["projected_unfiled_balances"] = projected_unfiled_balances
        
        if tax_liability_summary:
            result["tax_liability_summary"] = tax_liability_summary
        
        # === INTEREST CALCULATIONS ===
        interest_calculations = EnhancedTIParser.extract_interest_calculations(ti_text)
        if interest_calculations:
            result["interest_calculations"] = interest_calculations
        
        # === TAX YEARS ===
        tax_years = EnhancedTIParser.extract_tax_years_enhanced(ti_text, ti_version)
        if tax_years:
            result["tax_years"] = tax_years
        
        # === RESOLUTION PLAN ===
        resolution_plan = EnhancedTIParser.extract_resolution_plan_enhanced(ti_text, ti_version)
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
        
        logger.info(f"✅ Enhanced TI parsing completed. Found {len(result)} main sections")
        logger.info(f"   📅 Tax years: {len(tax_years)}")
        logger.info(f"   📋 Resolution steps: {len(resolution_plan.get('steps', []))}")
        logger.info(f"   ⚠️ Compliance issues: {len(compliance_requirements)}")
        logger.info(f"   🔍 TI Version: {ti_version}")
        
        return result 