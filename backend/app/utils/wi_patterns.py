form_patterns = {
    # 1099-MISC Form
    '1099-MISC': {
        'pattern': r'Form 1099-MISC',
        'category': 'SE',  # Self-Employment
        'fields': {
            # Income Fields
            'Non-Employee Compensation': r'Non[- ]?Employee[- ]?Compensation[:\s]*\$?([\d,.]+)',
            'Medical Payments': r'Medical[- ]?Payments[:\s]*\$?([\d,.]+)',
            'Fishing Income': r'Fishing[- ]?Income[:\s]*\$?([\d,.]+)',
            'Rents': r'Rents[:\s]*\$?([\d,.]+)',
            'Royalties': r'Royalties[:\s]*\$?([\d,.]+)',
            'Attorney Fees': r'Attorney[- ]?Fees[:\s]*\$?([\d,.]+)',
            'Other Income': r'Other[- ]?Income[:\s]*\$?([\d,.]+)',
            'Substitute for Dividends': r'Substitute[- ]?Payments[- ]?for[- ]?Dividends[:\s]*\$?([\d,.]+)',
            'Excess Golden Parachute': r'Excess[- ]?Golden[- ]?Parachute[:\s]*\$?([\d,.]+)',
            'Crop Insurance': r'Crop[- ]?Insurance[:\s]*\$?([\d,.]+)',
            'Foreign Tax Paid': r'Foreign[- ]?Tax[- ]?Paid[:\s]*\$?([\d,.]+)',
            'Section 409A Deferrals': r'Section[- ]?409A[- ]?Deferrals[:\s]*\$?([\d,.]+)',
            'Section 409A Income': r'Section[- ]?409A[- ]?Income[:\s]*\$?([\d,.]+)',
            'Direct Sales Indicator': r'Direct[- ]?Sales[- ]?Indicator[:\s]*([A-Za-z ]+)',
            'FATCA Filing Requirement': r'FATCA[- ]?Filing[- ]?Requirement[:\s]*([A-Za-z ]+)',
            'Second Notice Indicator': r'Second[- ]?Notice[- ]?Indicator[:\s]*([A-Za-z ]+)',
            # Withholdings
            'Federal Withholding': r'Federal[\s,]*income[\s,]*tax[\s,]*withheld[:\s]*\$?([\d,.]+)',
            'Tax Withheld': r'Tax[- ]?Withheld[:\s]*\$?([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Non-Employee Compensation', 0)) +
                float(fields.get('Medical Payments', 0)) +
                float(fields.get('Fishing Income', 0)) +
                float(fields.get('Rents', 0)) +
                float(fields.get('Royalties', 0)) +
                float(fields.get('Attorney Fees', 0)) +
                float(fields.get('Other Income', 0)) +
                float(fields.get('Substitute for Dividends', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0)) +
                float(fields.get('Tax Withheld', 0))
            )
        }
    },

    # 1099-NEC Form
    '1099-NEC': {
        'pattern': r'Form 1099-NEC',
        'category': 'SE',  # Self-Employment
        'fields': {
            # Income Fields
            'Non-Employee Compensation': r'Non[- ]?Employee[- ]?Compensation[:\s]*\$?([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Federal[\s,]*income[\s,]*tax[\s,]*withheld[:\s]*\$?([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer:\s*([A-Z0-9 &.,\-]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Non-Employee Compensation', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1099-K Form
    '1099-K': {
        'pattern': r'Form 1099-K',
        'category': 'SE',  # Self-Employment
        'fields': {
            # Income Fields
            'Gross Amount': r'Gross amount of payment card/third party transactions[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Federal income tax withheld[:\s]*\$([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer:\s*([A-Z0-9 &.,\-]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Gross Amount', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1099-PATR Form
    '1099-PATR': {
        'pattern': r'Form 1099-PATR',
        'category': 'SE',  # Self-Employment
        'fields': {
            # Income Fields
            'Patronage Dividends': r'Patronage dividends[:\s]*\$([\d,.]+)',
            'Non-Patronage Distribution': r'Non-patronage distribution[:\s]*\$([\d,.]+)',
            'Retained Allocations': r'Retained allocations[:\s]*\$([\d,.]+)',
            'Redemption Amount': r'Redemption amount[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer:\s*([A-Z0-9 &.,\-]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Patronage Dividends', 0)) +
                float(fields.get('Non-Patronage Distribution', 0)) +
                float(fields.get('Retained Allocations', 0)) +
                float(fields.get('Redemption Amount', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1042-S Form
    '1042-S': {
        'pattern': r'Form 1042-S',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Gross Income': r'Gross income[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'U\.S\. federal tax withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Gross Income', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # K-1 (Form 1065)
    'K-1 (Form 1065)': {
        'pattern': r'Schedule K-1 \(Form 1065\)',
        'category': 'SE',  # Self-Employment
        'fields': {
            # Income Fields
            'Royalties': r'Royalties[:\s]*\$([\d,.]+)',
            'Ordinary Income K-1': r'Ordinary income[:\s]*\$([\d,.]+)',
            'Real Estate': r'Real estate[:\s]*\$([\d,.]+)',
            'Other Rental': r'Other rental[:\s]*\$([\d,.]+)',
            'Guaranteed Payments': r'Guaranteed payments[:\s]*\$([\d,.]+)',
            # Non-Income Fields
            'Section 179 Expenses': r'Section 179 expenses[:\s]*\$([\d,.]+)',
            'Nonrecourse Beginning': r'Nonrecourse beginning[:\s]*\$([\d,.]+)',
            'Qualified Nonrecourse Beginning': r'Qualified nonrecourse beginning[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Royalties', 0)) +
                float(fields.get('Ordinary Income K-1', 0)) +
                float(fields.get('Real Estate', 0)) +
                float(fields.get('Other Rental', 0)) +
                float(fields.get('Guaranteed Payments', 0))
            ),
            'Withholding': lambda fields: 0  # No withholdings specified
        }
    },

    # K-1 (Form 1041)
    'K-1 (Form 1041)': {
        'pattern': r'Schedule K-1 \(Form 1041\)',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Net Rental Real Estate Income': r'Net rental real estate income[:\s]*\$([\d,.]+)',
            'Other Rental Income': r'Other rental income[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # Explicitly stated as "None"
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Net Rental Real Estate Income', 0)) +
                float(fields.get('Other Rental Income', 0))
            ),
            'Withholding': lambda fields: 0  # No withholdings specified
        }
    }
}

form_patterns.update({
    # W-2 Form (robust pattern)
    'W-2': {
        # This pattern matches 'Form W-2 Wage and Tax Statement' with optional spaces, hyphens, and OCR quirks
        'pattern': r'Form\s*W\s*[-–]?\s*2.*W\s*-?\s*a\s*-?\s*g\s*-?\s*e.*T\s*-?\s*a\s*-?\s*x.*S\s*-?\s*t\s*-?\s*a\s*-?\s*t\s*-?\s*e\s*-?\s*m\s*-?\s*e\s*-?\s*n\s*-?\s*t',
        'category': 'Non-SE',  # Non-Self-Employment
        'fields': {
            # Income Fields
            'Wages, Tips, and Other Compensation': r'Wages[\s,]*tips[\s,]*and[\s,]*other[\s,]*compensation[:\s]*\$?([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Federal[\s,]*income[\s,]*tax[\s,]*withheld[:\s]*\$?([\d,.]+)'
        },
        'identifiers': {
            'EIN': r'Employer Identification Number \(EIN\):\s*([\d\-]+)',
            'Employer': r'Employer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Wages, Tips, and Other Compensation', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # W-2G Form
    'W-2G': {
        'pattern': r'Form W-2G',
        'category': 'Non-SE',  # Non-Self-Employment
        'fields': {
            # Income Fields
            'Gross Winnings': r'Gross winnings[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Federal income tax withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Gross Winnings', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1099-R Form
    '1099-R': {
        'pattern': r'Form 1099-R',
        'category': 'Non-SE',  # Non-Self-Employment
        'fields': {
            # Income Fields
            'Taxable Amount': r'Taxable amount[:\s]*\$([\d,.]+)',
            'Gross Distribution': r'Gross distribution[:\s]*\$([\d,.]+)',
            # Distribution Codes
            'Distribution Code 1': r'Distribution code 1[:\s]*\$([\d,.]+)',
            'Distribution Code 2': r'Distribution code 2[:\s]*\$([\d,.]+)',
            'Distribution Code 3': r'Distribution code 3[:\s]*\$([\d,.]+)',
            'Distribution Code 4': r'Distribution code 4[:\s]*\$([\d,.]+)',
            'Distribution Code 7': r'Distribution code 7[:\s]*\$([\d,.]+)',
            'Distribution Code 8': r'Distribution code 8[:\s]*\$([\d,.]+)',
            # Non-Income Fields
            'Distribution Code G': r'Distribution code G[:\s]*\$([\d,.]+)',
            'Distribution Code J': r'Distribution code J[:\s]*\$([\d,.]+)',
            'Distribution Code L': r'Distribution code L[:\s]*\$([\d,.]+)',
            'Distribution Code M': r'Distribution code M[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            # Income Calculation: Conditional logic for Distribution Codes
            'Income': lambda fields: (
                float(fields.get('Taxable Amount', 0)) if fields.get('Taxable Amount') else (
                    float(fields.get('Gross Distribution', 0)) if any(fields.get(f'Distribution Code {i}') for i in range(1, 9)) else 0
                )
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    }
})

form_patterns.update({
    # 1099-B Form
    '1099-B': {
        'pattern': r'Form 1099-B',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Proceeds': r'Proceeds[:\s]*\$([\d,.]+)',
            'Cost or Basis': r'Cost or basis[:\s]*\$([\d,.]+)',
            'Calculated Income (Gain/Loss)': r'Proceeds[:\s]*\$([\d,.]+) - Cost or basis[:\s]*\$([\d,.]+)',  # Placeholder for calculation reference
            # Withholdings
            'Federal Withholding': r'Federal income tax withheld[:\s]*\$([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer:\s*([A-Z0-9 &.,\-]+)'
        },
        'calculation': {
            'Income': lambda fields: float(fields.get('Proceeds', 0)) - float(fields.get('Cost or Basis', 0))  # Dynamic calculation logic
        }
    }
})

form_patterns.update({
    # SSA Income - Pensions and Annuities
    'SSA-1099': {
        'pattern': r'Form SSA-1099',
        'category': 'Non-SE',  # Non-Self-Employment
        'fields': {
            # Income Fields
            'Total Benefits Paid': r'Pensions and Annuities \(Total Benefits Paid\)[:\s]*[\r\n\s]*\$?([\d,.]+)',
            'Repayments': r'Repayments[:\s]*\$([\d,.]+)',
            # Matches lines like 'TY 2022 Payments: $20,808.00' and captures year and value
            'TY Payments': r'TY (\d{4}) Payments[:\s]*\$([\d,.]+)',
            'Federal Withholding': r'Tax Withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            # Income Calculation: Filing status-dependent logic
            'Income': lambda fields, filing_status, combined_income: (
                float(fields.get('Total Benefits Paid', 0)) * 0.85 if (
                    filing_status in ['Single', 'HOH'] and combined_income > 25000
                ) or (
                    filing_status in ['MFS', 'MFJ'] and combined_income > 34000
                ) else (
                    float(fields.get('Total Benefits Paid', 0)) * 0.85 if combined_income == 0 else 0
                )
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    }
})

form_patterns.update({
    # 1099-DIV Form
    '1099-DIV': {
        'pattern': r'Form 1099-DIV',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Qualified Dividends': r'Qualified dividends[:\s]*\$([\d,.]+)',
            'Cash Liquidation Distribution': r'Cash liquidation distribution[:\s]*\$([\d,.]+)',
            'Capital Gains': r'Capital gains[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Qualified Dividends', 0)) +
                float(fields.get('Cash Liquidation Distribution', 0)) +
                float(fields.get('Capital Gains', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    }
})

form_patterns.update({
    # 1099-INT Form (with identifiers)
    '1099-INT': {
        'pattern': r'Form 1099-INT',
        'category': 'Neither',
        'fields': {
            'Interest': r'Interest[:\s]*\$([\d,.]+)',
            'Savings Bonds': r'Savings bonds[:\s]*\$([\d,.]+)',
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Interest', 0)) +
                (float(fields.get('Savings Bonds', 0)) if float(fields.get('Savings Bonds', 0)) >= 1000 else 0)
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1099-G Form
    '1099-G': {
        'pattern': r'Form 1099-G',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Unemployment Compensation': r'Unemployment compensation[:\s]*\$([\d,.]+)',
            'Agricultural Subsidies': r'Agricultural subsidies[:\s]*\$([\d,.]+)',
            'Taxable Grants': r'Taxable grants[:\s]*\$([\d,.]+)',
            # Not Income Fields
            'Prior Year Refund': r'Prior year refund[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Unemployment Compensation', 0)) +
                float(fields.get('Agricultural Subsidies', 0)) +
                float(fields.get('Taxable Grants', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    },

    # 1099-S Form
    '1099-S': {
        'pattern': r'Form 1099-S',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Gross Proceeds': r'Gross proceeds[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Gross Proceeds', 0))
            ),
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-LTC Form
    '1099-LTC': {
        'pattern': r'Form 1099-LTC',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Gross Long-Term Care Benefits Paid': r'Gross long-term care benefits paid[:\s]*\$([\d,.]+)',
            'Accelerated Death Benefits Paid': r'Accelerated death benefits paid[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Gross Long-Term Care Benefits Paid', 0)) +
                float(fields.get('Accelerated Death Benefits Paid', 0))
            ),
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 3922 Form
    '3922': {
        'pattern': r'Form 3922',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Calculation
            'Exercise Fair Market Value': r'Exercise fair market value per share[:\s]*\$([\d,.]+)',
            'Exercise Price Per Share (EPS)': r'Exercise price per share[:\s]*\$([\d,.]+)',
            'Number of Shares Transferred': r'Number of shares transferred[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: 0,  # ISO exercises are not income until sale; keep for cost basis reference
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # K-1 1120S Form
    'K-1 1120S': {
        'pattern': r'Schedule K-1 \(Form 1120S\)',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Dividends': r'Dividends[:\s]*\$([\d,.]+)',
            'Interest': r'Interest[:\s]*\$([\d,.]+)',
            'Royalties': r'Royalties[:\s]*\$([\d,.]+)',
            'Ordinary Income K-1': r'Ordinary income[:\s]*\$([\d,.]+)',
            'Real Estate': r'Real estate[:\s]*\$([\d,.]+)',
            'Other Rental': r'Other rental[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Dividends', 0)) +
                float(fields.get('Interest', 0)) +
                float(fields.get('Royalties', 0)) +
                float(fields.get('Ordinary Income K-1', 0)) +
                float(fields.get('Real Estate', 0)) +
                float(fields.get('Other Rental', 0))
            ),
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-OID Form
    '1099-OID': {
        'pattern': r'Form 1099-OID',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Original Issue Discount': r'Original issue discount[:\s]*\$([\d,.]+)',
            'Interest': r'Interest[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': r'Tax withheld[:\s]*\$([\d,.]+)'
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Original Issue Discount', 0)) +
                float(fields.get('Interest', 0))
            ),
            'Withholding': lambda fields: (
                float(fields.get('Federal Withholding', 0))
            )
        }
    }
})

form_patterns.update({
    # 5498 Form
    '5498': {
        'pattern': r'Form 5498',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Fair Market Value of Account': r'Fair market value of account[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: 0,  # Account balances are not income
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 5498-SA Form
    '5498-SA': {
        'pattern': r'Form 5498-SA',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # No explicit income or withholding fields
        },
        'calculation': {
            'Income': lambda fields: 0,  # No income fields
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1098 Form (exclude 1098-E)
    '1098': {
        'pattern': r'Form 1098(?!-E)',  # Match 'Form 1098' but not 'Form 1098-E'
        'category': 'Neither',
        'fields': {
            'Outstanding Mortgage Principal': r'Outstanding Mortgage Principle[:\s]*\$([\d,.]+)',
            'Mortgage Interest Received': r'Mortgage Interest Received from Payer\(s\)/Borrower\(s\)[:\s]*\$([\d,.]+)',
            'Federal Withholding': None
        },
        'calculation': {
            'Income': lambda fields: 0,  # Mortgage amounts are not income and are for deduction/reference only
            'Withholding': lambda fields: 0
        }
    },

    # 1098-E Form (specific pattern)
    '1098-E': {
        'pattern': r'Form 1098-E',
        'category': 'Neither',
        'fields': {
            'Received by Lender': r'Received by Lender[:\s]*\$([\d,.]+)',
        },
        'calculation': {
            'Income': lambda fields: 0,  # Student loan interest is not income and may be deductible
            'Withholding': lambda fields: 0
        }
    },

    # 1098-T Form
    '1098-T': {
        'pattern': r'Form 1098-T',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Qualified Tuition and Related Expenses': r'Qualified tuition and related expenses[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: 0,  # Tuition is an expense, not income
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-C Form
    '1099-C': {
        'pattern': r'Form 1099-C',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Amount of Debt Discharged': r'Amount of debt discharged[:\s]*\$([\d,.]+)',
            'Property Fair Market Value': r'Property fair market value[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: (
                float(fields.get('Amount of Debt Discharged', 0))  # Only debt discharge is potentially taxable; property value is informational
            ),
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-Q Form
    '1099-Q': {
        'pattern': r'Form 1099-Q',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Gross Distributions': r'Gross Distribution[s]?[:\s]*\$([\d,.]+)',  # Match singular or plural
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'identifiers': {
            'FIN': r"Payer's Federal Identification Number \(FIN\):\s*([\d\-]+)",
            'Payer': r'Payer[\s,]*:?\s*([A-Z0-9 &.,\-()\n]+?)(?=\n|Recipient|$)'
        },
        'calculation': {
            'Income': lambda fields: 0,  # Distributions may be non-taxable if used for qualified expenses
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-SA Form
    '1099-SA': {
        'pattern': r'Form 1099-SA',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'MSA Gross Distributions': r'MSA gross distributions[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: 0,  # Distributions may be non-taxable if used for qualified expenses
            'Withholding': lambda fields: 0  # No withholdings
        }
    },

    # 1099-LTC Form (Repeated for Gross Benefits)
    '1099-LTC': {
        'pattern': r'Form 1099-LTC',
        'category': 'Neither',  # Not SE or Non-SE
        'fields': {
            # Income Fields
            'Gross Benefits': r'Gross benefits[:\s]*\$([\d,.]+)',
            # Withholdings
            'Federal Withholding': None  # No withholdings
        },
        'calculation': {
            'Income': lambda fields: 0,  # Distributions may be non-taxable if used for qualified expenses
            'Withholding': lambda fields: 0  # No withholdings
        }
    }
})