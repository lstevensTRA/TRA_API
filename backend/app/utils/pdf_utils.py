import io
import re
import pypdf
import warnings
import logging
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import base64

# Suppress pypdf FloatObject warnings at module level
warnings.filterwarnings(
    "ignore",
    message=r"FloatObject .+ invalid; use 0.0 instead",
    module="pypdf.generic._base"
)

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes using pypdf, then pdfplumber, then OCR as fallback."""
    text = ""
    used_method = None

    def is_text_readable(text):
        if not text or len(text) < 100:
            return False
        # Too many (cid:xx) patterns = garbage
        if len(re.findall(r'\(cid:\d+\)', text)) > 10:
            return False
        # Too many non-ASCII or non-printable chars
        ascii_ratio = sum(32 <= ord(c) < 127 for c in text) / len(text)
        if ascii_ratio < 0.7:
            return False
        # At least 20% letters, at least 10 spaces per 1000 chars
        letter_ratio = sum(c.isalpha() for c in text) / len(text)
        space_ratio = text.count(' ') / max(1, len(text))
        return letter_ratio > 0.2 and space_ratio > 0.01

    # Try pypdf first
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            page_texts = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                page_texts.append(page_text)
            text = "\n".join(page_texts)
        if is_text_readable(text):
            used_method = "pypdf"
            logger.info(f"✅ Successfully extracted text using pypdf ({len(text)} chars)")
            return text
        else:
            logger.warning("⚠️ pypdf extraction unreadable, trying fallback")
    except Exception as e:
        logger.warning(f"⚠️ pypdf failed: {e}")

    # Try pdfplumber next
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_texts = []
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                page_texts.append(page_text)
            text = "\n".join(page_texts)
        if is_text_readable(text):
            used_method = "pdfplumber"
            logger.info(f"✅ Successfully extracted text using pdfplumber ({len(text)} chars)")
            return text
        else:
            logger.warning("⚠️ pdfplumber extraction unreadable, trying OCR")
    except Exception as e:
        logger.warning(f"⚠️ pdfplumber failed: {e}")

    # OCR fallback (optional - only if pdf2image and pytesseract are available)
    try:
        from pdf2image import convert_from_bytes
        import pytesseract
        images = convert_from_bytes(pdf_bytes)
        ocr_text = "\n".join(pytesseract.image_to_string(img) for img in images)
        if is_text_readable(ocr_text):
            used_method = "OCR"
            logger.info(f"✅ Successfully extracted text using OCR ({len(ocr_text)} chars)")
            return ocr_text
        else:
            logger.warning("⚠️ OCR extraction also unreadable")
    except ImportError as e:
        logger.warning(f"⚠️ OCR dependencies not available ({e}), skipping OCR fallback")
    except Exception as e:
        logger.warning(f"⚠️ OCR fallback failed: {e}")

    logger.error("❌ Could not extract readable text from PDF with any method")
    return ""

def generate_pdf_letter(case_data: Dict[str, Any], letter_template: Dict[str, Any], custom_content: Optional[str] = None) -> str:
    """
    Generate a PDF letter based on case data and template.
    
    Args:
        case_data: Case information from Logiqs
        letter_template: Letter template data
        custom_content: Optional custom content to include
    
    Returns:
        Base64 encoded PDF content
    """
    logger.info("🔍 Generating PDF letter")
    
    try:
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build story (content)
        story = []
        
        # Add letterhead
        story.append(Paragraph("Tax Resolution Associates", title_style))
        story.append(Paragraph("Professional Tax Resolution Services", normal_style))
        story.append(Spacer(1, 20))
        
        # Add date
        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"Date: {current_date}", normal_style))
        story.append(Spacer(1, 20))
        
        # Add client information
        client_name = case_data.get("ClientName", "Client")
        client_address = case_data.get("ClientAddress", "")
        case_id = case_data.get("CaseID", "")
        
        story.append(Paragraph(f"To: {client_name}", normal_style))
        if client_address:
            story.append(Paragraph(client_address, normal_style))
        story.append(Spacer(1, 20))
        
        # Add subject line
        subject = letter_template.get("subject", f"Case {case_id} - Tax Resolution")
        story.append(Paragraph(f"Subject: {subject}", header_style))
        story.append(Spacer(1, 20))
        
        # Add letter content
        letter_content = letter_template.get("content", "")
        if custom_content:
            letter_content += f"\n\n{custom_content}"
        
        # Split content into paragraphs and add to story
        paragraphs = letter_content.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip(), normal_style))
                story.append(Spacer(1, 12))
        
        # Add closing
        story.append(Spacer(1, 20))
        story.append(Paragraph("Sincerely,", normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Tax Resolution Associates", normal_style))
        story.append(Paragraph("Professional Tax Resolution Services", normal_style))
        
        # Add case information table
        story.append(Spacer(1, 30))
        case_info_data = [
            ["Case Information", ""],
            ["Case ID", case_id],
            ["Client Name", client_name],
            ["Case Status", case_data.get("Status", "N/A")],
            ["Resolution Type", case_data.get("ResolutionType", "N/A")],
            ["Resolution Amount", f"${case_data.get('ResolutionAmount', 0):,.2f}"],
        ]
        
        case_table = Table(case_info_data, colWidths=[2*inch, 4*inch])
        case_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(case_table)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        logger.info("✅ Successfully generated PDF letter")
        return pdf_base64
        
    except Exception as e:
        logger.error(f"❌ Error generating PDF letter: {str(e)}")
        raise

def generate_case_summary_pdf(case_data: Dict[str, Any], activities: list = None, resolution_details: Dict[str, Any] = None) -> str:
    """
    Generate a PDF case summary report.
    
    Args:
        case_data: Case information from Logiqs
        activities: Optional list of case activities
        resolution_details: Optional resolution details
    
    Returns:
        Base64 encoded PDF content
    """
    logger.info("🔍 Generating case summary PDF")
    
    try:
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build story (content)
        story = []
        
        # Add title
        story.append(Paragraph("Case Summary Report", title_style))
        story.append(Spacer(1, 20))
        
        # Add case information
        story.append(Paragraph("Case Information", header_style))
        
        case_id = case_data.get("CaseID", "")
        client_name = case_data.get("ClientName", "")
        case_status = case_data.get("Status", "")
        
        case_info_data = [
            ["Case ID", case_id],
            ["Client Name", client_name],
            ["Case Status", case_status],
            ["Case Type", case_data.get("CaseType", "N/A")],
            ["Created Date", case_data.get("CreatedDate", "N/A")],
            ["Last Modified", case_data.get("LastModified", "N/A")],
        ]
        
        case_table = Table(case_info_data, colWidths=[2*inch, 4*inch])
        case_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(case_table)
        story.append(Spacer(1, 20))
        
        # Add resolution details if available
        if resolution_details:
            story.append(Paragraph("Resolution Details", header_style))
            
            resolution_data = []
            for key, value in resolution_details.items():
                if value is not None:
                    resolution_data.append([key.replace('_', ' ').title(), str(value)])
            
            if resolution_data:
                resolution_table = Table(resolution_data, colWidths=[2*inch, 4*inch])
                resolution_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(resolution_table)
                story.append(Spacer(1, 20))
        
        # Add recent activities if available
        if activities and len(activities) > 0:
            story.append(Paragraph("Recent Activities", header_style))
            
            # Limit to last 10 activities
            recent_activities = activities[-10:]
            
            activity_data = [["Date", "Subject", "User", "Type"]]
            for activity in recent_activities:
                if isinstance(activity, dict):
                    activity_data.append([
                        activity.get("Date", ""),
                        activity.get("Subject", ""),
                        activity.get("User", ""),
                        activity.get("Type", "")
                    ])
            
            activity_table = Table(activity_data, colWidths=[1.5*inch, 2.5*inch, 1*inch, 1*inch])
            activity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(activity_table)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        logger.info("✅ Successfully generated case summary PDF")
        return pdf_base64
        
    except Exception as e:
        logger.error(f"❌ Error generating case summary PDF: {str(e)}")
        raise

def generate_income_comparison_pdf(comparison_data: Dict[str, Any]) -> str:
    """
    Generate a PDF income comparison report.
    
    Args:
        comparison_data: Income comparison data
    
    Returns:
        Base64 encoded PDF content
    """
    logger.info("🔍 Generating income comparison PDF")
    
    try:
        # Create PDF document
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=12
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )
        
        # Build story (content)
        story = []
        
        # Add title
        story.append(Paragraph("Income Comparison Report", title_style))
        story.append(Spacer(1, 20))
        
        # Add client information
        client_info = comparison_data.get("client_info", {})
        story.append(Paragraph("Client Information", header_style))
        
        client_data = [
            ["Client Name", client_info.get("name", "N/A")],
            ["Annual Income", f"${client_info.get('annual_income', 0):,.2f}"],
            ["Employer", client_info.get("employer", "N/A")],
            ["Case ID", comparison_data.get("case_id", "N/A")],
        ]
        
        client_table = Table(client_data, colWidths=[2*inch, 4*inch])
        client_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(client_table)
        story.append(Spacer(1, 20))
        
        # Add income comparison
        comparison = comparison_data.get("comparison", {})
        story.append(Paragraph("Income Comparison Analysis", header_style))
        
        comparison_data_table = []
        comparison_data_table.append(["Source", "Income Amount", "Difference", "Percentage"])
        
        # Add WI comparison if available
        wi_data = comparison_data.get("wi_data", {})
        if wi_data and "total_income" in wi_data:
            wi_income = wi_data["total_income"]
            client_income = client_info.get("annual_income", 0)
            difference = client_income - wi_income
            percentage = (difference / client_income * 100) if client_income > 0 else 0
            
            comparison_data_table.append([
                "Wage Investigation",
                f"${wi_income:,.2f}",
                f"${difference:,.2f}",
                f"{percentage:.1f}%"
            ])
        
        # Add AT comparison if available
        at_data = comparison_data.get("at_data", {})
        if at_data and "agi" in at_data:
            at_agi = at_data["agi"]
            client_income = client_info.get("annual_income", 0)
            difference = client_income - at_agi
            percentage = (difference / client_income * 100) if client_income > 0 else 0
            
            comparison_data_table.append([
                "Account Transcript",
                f"${at_agi:,.2f}",
                f"${difference:,.2f}",
                f"{percentage:.1f}%"
            ])
        
        if len(comparison_data_table) > 1:  # More than just header
            comp_table = Table(comparison_data_table, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(comp_table)
        else:
            story.append(Paragraph("No transcript data available for comparison", normal_style))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        logger.info("✅ Successfully generated income comparison PDF")
        return pdf_base64
        
    except Exception as e:
        logger.error(f"❌ Error generating income comparison PDF: {str(e)}")
        raise 

def parse_ti_text(raw_text: str) -> dict:
    """
    Parse raw TI text into structured JSON with client_info, summary, years, and resolution highlights.
    """
    import re
    from datetime import datetime
    
    # Helper to extract a value by regex
    def extract(pattern, text, group=1, default=None, flags=0):
        m = re.search(pattern, text, flags)
        return m.group(group).strip() if m else default

    # Extract client info
    client_info = {
        "opening_investigator": extract(r"Opening Investigator\s*([\w .'-]+)", raw_text),
        "case_number": extract(r"Case #\s*(\d+)", raw_text),
        "client_name": extract(r"Client Name\s*([\w .'-]+)", raw_text),
        "date_ti_completed": extract(r"Date TI Completed\s*([\d/\-]+)", raw_text),
        "current_tax_liability": float(extract(r"Current Tax Liability\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "current_and_projected_tax_liability": float(extract(r"Current & Projected Tax Liability\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "total_resolution_fees": float(extract(r"Total Resolution Fees\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "resolution_plan_completed_by": extract(r"Resolution Plan Completed by:([\w .'-]+)", raw_text),
        "date_reso_plan_completed": extract(r"Date RESO Plan Completed:([\d/\-]+)", raw_text),
        "settlement_officer": extract(r"Settlement Officer:([\w .'-]+)", raw_text),
        "tra_code": extract(r"TRA Code:([\w\d]+)", raw_text)
    }

    # Extract summary
    summary = {
        "total_individual_balance": float(extract(r"Total Individual Balance:\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "projected_unfiled_balances": float(extract(r"Projected Unfiled Balances:\$([\d,\.]+)", raw_text, 1, "0").replace(",", ""))
    }

    # Extract years table (very basic, can be improved)
    years = []
    table_match = re.search(r"Tax Years.*?Notes(.*?)(?:Print Amendment Sheet|Resolution Highlights|$)", raw_text, re.DOTALL)
    if table_match:
        table_text = table_match.group(1)
        for row in table_text.split("\n"):
            # Skip empty or header rows
            if not row.strip() or re.match(r"^\s*Tax Years", row):
                continue
            # Try to extract year and columns
            cols = re.split(r"\s{2,}|\t|(?<=\$)\s+", row.strip())
            if len(cols) < 3:
                continue
            # Try to parse columns by position (fragile, but works for most cases)
            year = extract(r"(\d{4})", cols[0])
            if not year:
                continue
            years.append({
                "tax_year": int(year),
                "return_filed": cols[1] if len(cols) > 1 else "",
                "filing_status": cols[2] if len(cols) > 2 else "",
                "current_balance": float(cols[3].replace("$", "").replace(",", "")) if len(cols) > 3 and "$" in cols[3] else 0.0,
                "csed_date": cols[4] if len(cols) > 4 else "",
                "reason": cols[5] if len(cols) > 5 else "",
                "status": cols[6] if len(cols) > 6 else "",
                "legal_action": cols[7] if len(cols) > 7 else "",
                "projected_balance": float(cols[8].replace("$", "").replace(",", "")) if len(cols) > 8 and "$" in cols[8] else 0.0,
                "wage_information": [w.strip() for w in cols[9:12] if w.strip()] if len(cols) > 9 else [],
                "notes": cols[12] if len(cols) > 12 else ""
            })

    # Extract resolution highlights and interest cost
    highlights = {}
    highlights["total_timeframe_months"] = int(extract(r"Total Timeframe(\d+) Months", raw_text, 1, "0"))
    highlights["compliance_phase_months"] = int(extract(r"Compliance and Tax Preparation(\d+) Months", raw_text, 1, "0"))
    highlights["resolution_phase_months"] = int(extract(r"Resolution Phase\n(\d+)\n", raw_text, 1, "0"))
    highlights["interest_cost"] = {
        "daily": float(extract(r"Daily:\s*\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "monthly": float(extract(r"Monthly:\s*\$([\d,\.]+)", raw_text, 1, "0").replace(",", "")),
        "yearly": float(extract(r"Yearly:\s*\$([\d,\.]+)", raw_text, 1, "0").replace(",", ""))
    }

    return {
        "client_info": client_info,
        "summary": summary,
        "years": years,
        "resolution_highlights": highlights
    } 