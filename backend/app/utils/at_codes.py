# AT (Account Transcript) transaction codes and their interpretations.
# This matches the exact format from the Streamlit app

AT_CODES = [
    {
        "code": "150",
        "meaning": "Return filed / tax assessed OR indicator that a return is still missing",
        "date_note": "Return-filed date (or IRS input date if scanned)",
        "amount_note": "Total tax liability assessed",
        "file_status_rules": {
            "filed_if_text_contains": [
                "return filed",
                "tax assessed",
                "original return",
                "as filed"
            ],
            "not_filed_if_text_contains": [
                "return not filed",
                "no return filed",
                "unfiled return",
                "missing return"
            ],
            "field_to_check": "Outcome"
        }
    },
    {
        "code": "290",
        "meaning": "Additional tax assessed",
        "date_note": "Assessment date",
        "amount_note": "Extra tax added"
    },
    {
        "code": "291",
        "meaning": "Tax abatement (reversal of tax)",
        "date_note": "Abatement date",
        "amount_note": "Tax removed (negative amount)"
    },
    {
        "code": "300",
        "meaning": "Additional penalty/interest assessed",
        "date_note": "Assessment date",
        "amount_note": "Penalty or interest added"
    },
    {
        "code": "301",
        "meaning": "Penalty/interest abated",
        "date_note": "Abatement date",
        "amount_note": "Penalty or interest removed (negative)"
    },
    {
        "code": "306",
        "meaning": "Credit transferred from another tax module",
        "date_note": "Transfer posting date",
        "amount_note": "Credit amount (negative = out, positive = in)"
    },
    {
        "code": "320",
        "meaning": "Amended return filed (Form 1040-X)",
        "date_note": "Amended-return received date"
    },
    {
        "code": "420",
        "meaning": "Examination (audit) opened",
        "date_note": "Audit-opening date"
    },
    {
        "code": "424",
        "meaning": "Examination in process / post-audit",
        "date_note": "Audit-status date"
    },
    {
        "code": "430",
        "meaning": "Examination case closed – no change",
        "date_note": "Closure date"
    },
    {
        "code": "460",
        "meaning": "Extension of time to file (Form 4868/7004)",
        "date_note": "Extension-request date"
    },
    {
        "code": "480",
        "meaning": "Offer-in-Compromise (OIC) pending",
        "date_note": "OIC-pending date"
    },
    {
        "code": "482",
        "meaning": "Offer-in-Compromise accepted",
        "date_note": "Acceptance date",
        "amount_note": "Accepted offer amount"
    },
    {
        "code": "520",
        "meaning": "Litigation / CI / collection freeze (varies by closing code)",
        "date_note": "Freeze-start date"
    },
    {
        "code": "530",
        "meaning": "Account classified Currently Not Collectible (CNC)",
        "date_note": "CNC-start date"
    },
    {
        "code": "570",
        "meaning": "Additional liability pending / refund freeze",
        "date_note": "Freeze-start date",
        "amount_note": "Amount in dispute (often blank)"
    },
    {
        "code": "571",
        "meaning": "Additional liability reversed (freeze released)",
        "date_note": "Release date"
    },
    {
        "code": "599",
        "meaning": "Return filed by IRS (substitute or scanned copy)",
        "date_note": "IRS-input date"
    },
    {
        "code": "610",
        "meaning": "Payment with return",
        "date_note": "Payment posting date",
        "amount_note": "Payment amount (negative = credit)"
    },
    {
        "code": "670",
        "meaning": "Subsequent payment",
        "date_note": "Payment posting date",
        "amount_note": "Payment amount (negative = credit)"
    },
    {
        "code": "680",
        "meaning": "Payment applied to civil penalty",
        "date_note": "Payment posting date",
        "amount_note": "Payment amount (negative = credit)"
    },
    {
        "code": "706",
        "meaning": "Bad-check penalty assessed",
        "date_note": "Assessment date",
        "amount_note": "Penalty amount"
    },
    {
        "code": "720",
        "meaning": "Credit transferred out to another module",
        "date_note": "Transfer date",
        "amount_note": "Credit transferred (positive = out)"
    },
    {
        "code": "766",
        "meaning": "Credit to your account (e.g., refundable credit or offset)",
        "date_note": "Credit posting date",
        "amount_note": "Credit amount (negative = credit)"
    },
    {
        "code": "768",
        "meaning": "Earned Income Credit allowed",
        "date_note": "Credit posting date",
        "amount_note": "EIC amount (negative = credit)"
    },
    {
        "code": "780",
        "meaning": "Account included in bankruptcy",
        "date_note": "Bankruptcy-filed date"
    },
    {
        "code": "806",
        "meaning": "Credit for federal tax withheld",
        "date_note": "Return-filed date",
        "amount_note": "Withholding amount (negative = credit)"
    },
    {
        "code": "810",
        "meaning": "Refund freeze / manual refund hold",
        "date_note": "Freeze-start date"
    },
    {
        "code": "811",
        "meaning": "Refund freeze released",
        "date_note": "Release date"
    },
    {
        "code": "846",
        "meaning": "Refund issued",
        "date_note": "Refund issue date",
        "amount_note": "Refund amount (negative = refund sent)"
    },
    {
        "code": "898",
        "meaning": "TOP (Treasury Offset Program) refund offset",
        "date_note": "Offset date",
        "amount_note": "Offset amount (positive = taken from refund)"
    },
    {
        "code": "960",
        "meaning": "Appointed representative",
        "date_note": "Representation date"
    },
    {
        "code": "196",
        "meaning": "Interest charged for late payment",
        "date_note": "Interest assessment date",
        "amount_note": "Interest amount"
    },
    {
        "code": "336",
        "meaning": "Interest charged for late payment",
        "date_note": "Interest assessment date",
        "amount_note": "Interest amount"
    }
]

def get_code_info(code):
    """Get information about a specific transaction code."""
    for code_info in AT_CODES:
        if code_info["code"] == code:
            return code_info
    return None

def interpret_transaction(code, description, date, amount):
    """Interpret a transaction based on its code and details."""
    code_info = get_code_info(code)
    if not code_info:
        return None
    
    return {
        "code": code,
        "meaning": code_info["meaning"],
        "description": description,
        "date": date,
        "amount": amount,
        "date_note": code_info.get("date_note", ""),
        "amount_note": code_info.get("amount_note", "")
    }

# Create a simple dictionary mapping for backward compatibility
at_codes = {}
for code_info in AT_CODES:
    at_codes[code_info["code"]] = code_info["meaning"] 