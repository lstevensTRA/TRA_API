"""
Taxpayer/Spouse parsing logic for WI and AT transcripts
This matches the Streamlit app's TPSParser functionality
"""

import re
from typing import Dict, List, Optional

class TPSParser:
    """Handle Taxpayer (TP) and Spouse (S) designation parsing from filenames"""
    
    @staticmethod
    def extract_owner_from_filename(filename: str) -> str:
        """
        Extract TP/S designation from filename
        
        Args:
            filename: The uploaded file name (e.g., "WI 19 TP", "WI S 19", "WI 19", "AT 23 E.pdf")
            
        Returns:
            "TP", "S", or "TP" (default)
            
        Examples:
            "WI 19 TP" → "TP"
            "WI S 19" → "S"  
            "WI 19" → "TP" (default)
            "AT 23 E.pdf" → "S" (E indicates spouse)
            "AT 23.pdf" → "TP" (default)
        """
        if not filename:
            return "TP"  # Default to taxpayer
        
        # Clean filename and convert to uppercase for matching
        clean_filename = filename.upper().strip()
        
        # Check for spouse designation first (more specific)
        if re.search(r'\bS\b', clean_filename) or re.search(r'\bSPOUSE\b', clean_filename):
            return "S"
        
        # Check for AT files with E suffix (spouse)
        if re.search(r'AT\s+\d{2}\s+E', clean_filename):
            return "S"
        
        # Check for taxpayer designation
        if re.search(r'\bTP\b', clean_filename):
            return "TP"
        
        # Check for combined/joint designation
        if re.search(r'\b(COMBINED|JOINT)\b', clean_filename):
            return None  # Indicates joint filing data
        
        # Default to taxpayer if no designation found
        return "TP"
    
    @staticmethod
    def enhance_wi_data_with_owner(wi_data: Dict, filename: str) -> Dict:
        """
        Add Owner field to existing WI transcript data based on filename
        
        Args:
            wi_data: Existing WI transcript data structure
            filename: Source filename for owner determination
            
        Returns:
            Enhanced WI data with Owner fields added
        """
        if not wi_data:
            return wi_data
        
        owner = TPSParser.extract_owner_from_filename(filename)
        
        # Add owner designation to all forms in this file
        enhanced_data = {}
        for year, forms in wi_data.items():
            enhanced_data[year] = []
            for form in forms:
                enhanced_form = form.copy()
                enhanced_form['Owner'] = owner
                enhanced_data[year].append(enhanced_form)
        
        return enhanced_data
    
    @staticmethod
    def enhance_at_data_with_owner(at_data: List[Dict], filename: str) -> List[Dict]:
        """
        Add Owner field to existing AT transcript data based on filename
        
        Args:
            at_data: Existing AT transcript data structure
            filename: Source filename for owner determination
            
        Returns:
            Enhanced AT data with Owner fields added
        """
        if not at_data:
            return at_data
        
        owner = TPSParser.extract_owner_from_filename(filename)
        
        # Add owner designation to all AT records in this file
        enhanced_data = []
        for record in at_data:
            enhanced_record = record.copy()
            enhanced_record['owner'] = owner
            enhanced_data.append(enhanced_record)
        
        return enhanced_data
    
    @staticmethod
    def aggregate_wi_income_by_owner(wi_data: Dict) -> Dict:
        """
        Calculate WI income totals broken down by owner (TP/S/Joint)
        
        Args:
            wi_data: WI transcript data with Owner fields
            
        Returns:
            Dictionary with totals by owner type
        """
        totals = {}
        
        for year, forms in wi_data.items():
            year_totals = {
                'taxpayer': {'income': 0, 'withholding': 0, 'se_income': 0, 'non_se_income': 0},
                'spouse': {'income': 0, 'withholding': 0, 'se_income': 0, 'non_se_income': 0},
                'joint': {'income': 0, 'withholding': 0, 'se_income': 0, 'non_se_income': 0},
                'combined': {'income': 0, 'withholding': 0, 'se_income': 0, 'non_se_income': 0}
            }
            
            for form in forms:
                owner = form.get('Owner')
                income = float(form.get('Income', 0))
                withholding = float(form.get('Withholding', 0))
                category = form.get('Category', '')
                
                # Determine which bucket to add to
                if owner == 'TP':
                    bucket = 'taxpayer'
                elif owner == 'S':
                    bucket = 'spouse'
                elif owner is None:
                    bucket = 'joint'
                else:
                    bucket = 'taxpayer'  # Default fallback
                
                # Add to appropriate bucket
                year_totals[bucket]['income'] += income
                year_totals[bucket]['withholding'] += withholding
                
                # Categorize income type
                if category == 'SE':
                    year_totals[bucket]['se_income'] += income
                elif category == 'Non-SE':
                    year_totals[bucket]['non_se_income'] += income
                
                # Always add to combined totals
                year_totals['combined']['income'] += income
                year_totals['combined']['withholding'] += withholding
                if category == 'SE':
                    year_totals['combined']['se_income'] += income
                elif category == 'Non-SE':
                    year_totals['combined']['non_se_income'] += income
            
            totals[year] = year_totals
        
        return totals
    
    @staticmethod
    def aggregate_at_data_by_owner(at_data: List[Dict]) -> Dict:
        """
        Calculate AT data totals broken down by owner (TP/S)
        
        Args:
            at_data: AT transcript data with owner fields
            
        Returns:
            Dictionary with totals by owner type
        """
        totals = {}
        
        for record in at_data:
            year = record.get('tax_year')
            owner = record.get('owner', 'TP')
            
            if year not in totals:
                totals[year] = {
                    'taxpayer': {'records': 0, 'transactions': 0, 'account_balance': 0},
                    'spouse': {'records': 0, 'transactions': 0, 'account_balance': 0},
                    'combined': {'records': 0, 'transactions': 0, 'account_balance': 0}
                }
            
            # Determine bucket
            if owner == 'TP':
                bucket = 'taxpayer'
            elif owner == 'S':
                bucket = 'spouse'
            else:
                bucket = 'taxpayer'  # Default
            
            # Add to appropriate bucket
            totals[year][bucket]['records'] += 1
            totals[year][bucket]['transactions'] += len(record.get('transactions', []))
            totals[year][bucket]['account_balance'] += float(record.get('account_balance', 0))
            
            # Always add to combined
            totals[year]['combined']['records'] += 1
            totals[year]['combined']['transactions'] += len(record.get('transactions', []))
            totals[year]['combined']['account_balance'] += float(record.get('account_balance', 0))
        
        return totals
    
    @staticmethod
    def detect_missing_spouse_data_wi(totals: Dict, filing_status: str) -> List[str]:
        """
        Identify years where spouse data might be missing for WI data
        
        Args:
            totals: Income totals by owner from aggregate_wi_income_by_owner
            filing_status: Client's filing status
            
        Returns:
            List of recommendations for missing data
        """
        recommendations = []
        
        if filing_status not in ['Married Filing Jointly', 'Married Filing Separately']:
            return recommendations  # Not married, no spouse data expected
        
        for year, year_totals in totals.items():
            taxpayer_income = year_totals['taxpayer']['income']
            spouse_income = year_totals['spouse']['income']
            
            # Check for potential missing spouse data
            if taxpayer_income > 0 and spouse_income == 0:
                recommendations.append(
                    f"Year {year}: Consider checking for spouse income - only taxpayer income found"
                )
            elif taxpayer_income == 0 and spouse_income > 0:
                recommendations.append(
                    f"Year {year}: Consider checking for taxpayer income - only spouse income found"
                )
            elif taxpayer_income == 0 and spouse_income == 0:
                recommendations.append(
                    f"Year {year}: No income found for either spouse - verify transcript completeness"
                )
        
        return recommendations
    
    @staticmethod
    def detect_missing_spouse_data_at(at_data: List[Dict], filing_status: str) -> List[str]:
        """
        Identify years where spouse data might be missing for AT data
        
        Args:
            at_data: AT transcript data
            filing_status: Client's filing status
            
        Returns:
            List of recommendations for missing data
        """
        recommendations = []
        
        if filing_status not in ['Married Filing Jointly', 'Married Filing Separately']:
            return recommendations  # Not married, no spouse data expected
        
        # Group by year and owner
        by_year = {}
        for record in at_data:
            year = record.get('tax_year')
            owner = record.get('owner', 'TP')
            
            if year not in by_year:
                by_year[year] = {'TP': [], 'S': []}
            
            by_year[year][owner].append(record)
        
        for year, owners in by_year.items():
            tp_records = owners.get('TP', [])
            s_records = owners.get('S', [])
            
            # Check for potential missing spouse data
            if tp_records and not s_records:
                recommendations.append(
                    f"Year {year}: Consider checking for spouse AT transcript - only taxpayer records found"
                )
            elif not tp_records and s_records:
                recommendations.append(
                    f"Year {year}: Consider checking for taxpayer AT transcript - only spouse records found"
                )
            elif not tp_records and not s_records:
                recommendations.append(
                    f"Year {year}: No AT records found for either spouse - verify transcript availability"
                )
        
        return recommendations
    
    @staticmethod
    def generate_tps_analysis_summary(wi_data: Dict = None, at_data: List[Dict] = None, filing_status: str = None) -> Dict:
        """
        Generate comprehensive TP/S analysis summary for both WI and AT data
        
        Args:
            wi_data: WI transcript data with Owner fields
            at_data: AT transcript data with owner fields
            filing_status: Client's filing status
            
        Returns:
            Complete analysis with recommendations
        """
        analysis = {
            'filing_status': filing_status,
            'missing_data_recommendations': [],
            'analysis_metadata': {
                'has_wi_data': wi_data is not None,
                'has_at_data': at_data is not None,
                'years_analyzed': set(),
                'has_taxpayer_data': False,
                'has_spouse_data': False
            }
        }
        
        # Analyze WI data if available
        if wi_data:
            wi_totals = TPSParser.aggregate_wi_income_by_owner(wi_data)
            analysis['wi_totals_by_year'] = wi_totals
            analysis['missing_data_recommendations'].extend(
                TPSParser.detect_missing_spouse_data_wi(wi_totals, filing_status)
            )
            analysis['analysis_metadata']['years_analyzed'].update(wi_totals.keys())
            analysis['analysis_metadata']['has_taxpayer_data'] = any(t['taxpayer']['income'] > 0 for t in wi_totals.values())
            analysis['analysis_metadata']['has_spouse_data'] = any(t['spouse']['income'] > 0 for t in wi_totals.values())
        
        # Analyze AT data if available
        if at_data:
            at_totals = TPSParser.aggregate_at_data_by_owner(at_data)
            analysis['at_totals_by_year'] = at_totals
            analysis['missing_data_recommendations'].extend(
                TPSParser.detect_missing_spouse_data_at(at_data, filing_status)
            )
            analysis['analysis_metadata']['years_analyzed'].update(at_totals.keys())
            analysis['analysis_metadata']['has_taxpayer_data'] = analysis['analysis_metadata']['has_taxpayer_data'] or any(t['taxpayer']['records'] > 0 for t in at_totals.values())
            analysis['analysis_metadata']['has_spouse_data'] = analysis['analysis_metadata']['has_spouse_data'] or any(t['spouse']['records'] > 0 for t in at_totals.values())
        
        # Convert years_analyzed to sorted list
        analysis['analysis_metadata']['years_analyzed'] = sorted(list(analysis['analysis_metadata']['years_analyzed']), reverse=True)
        
        return analysis 