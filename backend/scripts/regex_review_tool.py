#!/usr/bin/env python3
"""
Improved Regex Review Tool: Compare structured extraction to raw text, find mismatches, show regex, and suggest fixes.
Outputs a detailed HTML report showing exactly what was extracted from where.

Usage:
    python regex_review_tool.py caseid1 [caseid2 ...]
    (or run and follow the prompt)

Dependencies: requests, jinja2
"""
import sys
import requests
import re
import os
from jinja2 import Template
from backend.app.utils.wi_patterns import form_patterns

def fetch_raw_text(case_id):
    resp = requests.post("http://localhost:8000/api/training/raw-text/wi", json={"case_ids": [case_id]})
    return resp.json().get(case_id, "")

def fetch_structured(case_id):
    resp = requests.get(f"http://localhost:8000/analysis/wi/{case_id}")
    return resp.json()

def get_regex(form_type, field):
    return form_patterns.get(form_type, {}).get('fields', {}).get(field, '')

def find_value_in_text_with_context(raw_text, field, value, form_type):
    """Find where the value appears in raw text and show extended context"""
    
    # First try exact value match
    exact_matches = []
    for match in re.finditer(re.escape(str(value)), raw_text):
        start_context = max(0, match.start() - 100)
        end_context = min(len(raw_text), match.end() + 100)
        context = raw_text[start_context:end_context]
        
        exact_matches.append({
            'type': 'exact',
            'position': match.start(),
            'matched_text': match.group(),
            'context': context,
            'pre_context': raw_text[start_context:match.start()],
            'post_context': raw_text[match.end():end_context]
        })
    
    # Try regex pattern match if we have one
    regex_matches = []
    current_regex = get_regex(form_type, field)
    if current_regex:
        try:
            pattern = re.compile(current_regex, re.IGNORECASE | re.MULTILINE)
            for match in pattern.finditer(raw_text):
                start_context = max(0, match.start() - 100)
                end_context = min(len(raw_text), match.end() + 100)
                context = raw_text[start_context:end_context]
                
                # Extract the captured group (usually the value)
                captured_value = match.group(1) if match.groups() else match.group(0)
                
                regex_matches.append({
                    'type': 'regex',
                    'position': match.start(),
                    'matched_text': match.group(0),
                    'captured_value': captured_value,
                    'context': context,
                    'pre_context': raw_text[start_context:match.start()],
                    'post_context': raw_text[match.end():end_context],
                    'matches_extracted': captured_value.strip('$,') == str(value).strip('$,')
                })
        except re.error as e:
            regex_matches.append({
                'type': 'regex_error',
                'error': str(e)
            })
    
    # Try fuzzy matching for common variations
    fuzzy_matches = []
    if not exact_matches:
        # Remove $ and commas for fuzzy matching
        clean_value = str(value).replace('$', '').replace(',', '')
        if clean_value and clean_value != '0' and clean_value != '0.00':
            fuzzy_pattern = re.escape(clean_value)
            for match in re.finditer(fuzzy_pattern, raw_text):
                start_context = max(0, match.start() - 100)
                end_context = min(len(raw_text), match.end() + 100)
                context = raw_text[start_context:end_context]
                
                fuzzy_matches.append({
                    'type': 'fuzzy',
                    'position': match.start(),
                    'matched_text': match.group(),
                    'context': context,
                    'pre_context': raw_text[start_context:match.start()],
                    'post_context': raw_text[match.end():end_context]
                })
    
    return {
        'exact_matches': exact_matches,
        'regex_matches': regex_matches,
        'fuzzy_matches': fuzzy_matches,
        'total_matches': len(exact_matches) + len(regex_matches) + len(fuzzy_matches)
    }

def suggest_improved_regex(field, value, current_regex, match_info):
    """Suggest improvements to regex based on what we found"""
    suggestions = []
    
    # If regex failed but we found exact matches
    if not match_info['regex_matches'] and match_info['exact_matches']:
        context = match_info['exact_matches'][0]['context']
        # Analyze the context to suggest a better pattern
        lines = context.split('\n')
        for line in lines:
            if str(value) in line:
                # Suggest pattern based on the line structure
                line_pattern = re.escape(line).replace(re.escape(str(value)), r'([\\d,.]+)')
                suggestions.append(f"Pattern from context: {line_pattern}")
                break
    
    # If regex matches but captures wrong value
    wrong_captures = [m for m in match_info['regex_matches'] if not m.get('matches_extracted', True)]
    if wrong_captures:
        suggestions.append("Regex pattern matches but captures wrong value - check capture groups")
    
    # General suggestions based on field type
    if 'income' in field.lower() or 'wage' in field.lower() or 'compensation' in field.lower():
        suggestions.append(f"Income field suggestion: {field}[:\\s]*\\$?([\\d,.]+)")
    elif 'tax' in field.lower() or 'withheld' in field.lower():
        suggestions.append(f"Tax field suggestion: {field}[:\\s]*\\$?([\\d,.]+)")
    elif 'ssn' in field.lower() or 'social security' in field.lower():
        suggestions.append(f"SSN suggestion: \\b\\d{{3}}-\\d{{2}}-\\d{{4}}\\b")
    
    if not suggestions:
        suggestions.append("No specific suggestions - manual review needed")
    
    return suggestions

def compare_and_collect(case_id):
    raw_text = fetch_raw_text(case_id)
    structured = fetch_structured(case_id)
    rows = []
    
    years_data = structured.get("years_data", {})
    for year, forms in years_data.items():
        if not isinstance(forms, list):
            continue
        for form_idx, form in enumerate(forms):
            if not isinstance(form, dict):
                continue
            form_type = form.get("Form")
            fields = form.get("Fields", {})
            name = form.get("Name", "")
            ssn = form.get("SSN", "")
            source_file = form.get("SourceFile", "")
            form_year = form.get("Year", year)
            
            for field, value in fields.items():
                value_str = str(value)
                current_regex = get_regex(form_type, field)
                
                # Get detailed match information
                match_info = find_value_in_text_with_context(raw_text, field, value_str, form_type)
                
                # Generate suggestions
                suggestions = suggest_improved_regex(field, value_str, current_regex, match_info)
                
                rows.append({
                    "case_id": case_id,
                    "year": form_year,
                    "form_type": form_type,
                    "form_index": form_idx,
                    "field": field,
                    "extracted_value": value_str,
                    "current_regex": current_regex,
                    "match_info": match_info,
                    "suggestions": suggestions,
                    "name": name,
                    "ssn": ssn,
                    "source_file": source_file,
                    "has_issues": match_info['total_matches'] == 0 or any(not m.get('matches_extracted', True) for m in match_info['regex_matches'])
                })
    return rows

def render_html_report(all_rows, output_html="regex_review_report.html"):
    template_str = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Regex Review Report</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f5f5f5;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            
            .summary-stats {
                display: flex; 
                gap: 20px; 
                margin-bottom: 30px;
                justify-content: center;
            }
            .stat-box {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
                min-width: 120px;
            }
            .stat-number { font-size: 2em; font-weight: bold; }
            .stat-good { color: #28a745; }
            .stat-bad { color: #dc3545; }
            .stat-neutral { color: #6c757d; }
            
            .filter-controls {
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .filter-controls label {
                margin-right: 15px;
                font-weight: 500;
            }
            .filter-controls input, .filter-controls select {
                margin-right: 20px;
                padding: 5px 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            
            .extraction-row {
                background: white;
                margin-bottom: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .extraction-row.has-issues {
                border-left: 5px solid #dc3545;
            }
            .extraction-row.no-issues {
                border-left: 5px solid #28a745;
            }
            
            .extraction-header {
                background: #f8f9fa;
                padding: 15px 20px;
                border-bottom: 1px solid #dee2e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .extraction-title {
                font-weight: 600;
                font-size: 1.1em;
            }
            .extraction-meta {
                color: #6c757d;
                font-size: 0.9em;
            }
            .status-badge {
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.8em;
                font-weight: 500;
            }
            .status-good { background: #d4edda; color: #155724; }
            .status-bad { background: #f8d7da; color: #721c24; }
            .status-warning { background: #fff3cd; color: #856404; }
            
            .extraction-body {
                padding: 20px;
            }
            
            .field-details {
                display: grid;
                grid-template-columns: 200px 200px 1fr;
                gap: 20px;
                margin-bottom: 20px;
                align-items: start;
            }
            .detail-box {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                border: 1px solid #e9ecef;
            }
            .detail-label {
                font-weight: 600;
                margin-bottom: 8px;
                color: #495057;
            }
            .detail-value {
                font-family: monospace;
                background: white;
                padding: 8px;
                border-radius: 4px;
                border: 1px solid #dee2e6;
                word-break: break-all;
            }
            
            .matches-section {
                margin-top: 20px;
            }
            .match-type {
                margin-bottom: 15px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                overflow: hidden;
            }
            .match-type-header {
                background: #e9ecef;
                padding: 10px 15px;
                font-weight: 600;
                border-bottom: 1px solid #dee2e6;
            }
            .match-item {
                padding: 15px;
                border-bottom: 1px solid #f1f3f4;
            }
            .match-item:last-child { border-bottom: none; }
            
            .context-display {
                font-family: monospace;
                background: #f8f9fa;
                padding: 12px;
                border-radius: 4px;
                border-left: 4px solid #007bff;
                white-space: pre-wrap;
                font-size: 0.9em;
                line-height: 1.4;
            }
            .highlight-exact { background: #fff3cd; padding: 2px 4px; border-radius: 3px; }
            .highlight-regex { background: #d4edda; padding: 2px 4px; border-radius: 3px; }
            .highlight-fuzzy { background: #f8d7da; padding: 2px 4px; border-radius: 3px; }
            
            .suggestions {
                background: #e7f3ff;
                border: 1px solid #b3d7ff;
                border-radius: 6px;
                padding: 15px;
                margin-top: 15px;
            }
            .suggestions h4 {
                margin: 0 0 10px 0;
                color: #0066cc;
            }
            .suggestion-item {
                background: white;
                padding: 8px 12px;
                margin: 5px 0;
                border-radius: 4px;
                font-family: monospace;
                font-size: 0.9em;
            }
            
            .regex-display {
                background: #2d3748;
                color: #e2e8f0;
                padding: 12px;
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
                overflow-x: auto;
            }
            
            .toggle-btn {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 0.9em;
            }
            .toggle-btn:hover { background: #0056b3; }
            
            .hidden { display: none; }
        </style>
        <script>
            function toggleDetails(id) {
                const element = document.getElementById(id);
                element.classList.toggle('hidden');
            }
            
            function filterRows() {
                const showIssuesOnly = document.getElementById('issues-filter').checked;
                const caseFilter = document.getElementById('case-filter').value.toLowerCase();
                const formFilter = document.getElementById('form-filter').value.toLowerCase();
                
                const rows = document.querySelectorAll('.extraction-row');
                rows.forEach(row => {
                    const hasIssues = row.classList.contains('has-issues');
                    const caseId = row.dataset.caseId.toLowerCase();
                    const formType = row.dataset.formType.toLowerCase();
                    
                    let show = true;
                    if (showIssuesOnly && !hasIssues) show = false;
                    if (caseFilter && !caseId.includes(caseFilter)) show = false;
                    if (formFilter && !formType.includes(formFilter)) show = false;
                    
                    row.style.display = show ? 'block' : 'none';
                });
            }
            
            window.onload = function() {
                document.getElementById('issues-filter').onchange = filterRows;
                document.getElementById('case-filter').oninput = filterRows;
                document.getElementById('form-filter').onchange = filterRows;
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Regex Review Report</h1>
            
            <div class="summary-stats">
                <div class="stat-box">
                    <div class="stat-number stat-neutral">{{ rows|length }}</div>
                    <div>Total Extractions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number stat-good">{{ rows|selectattr('has_issues', 'equalto', false)|list|length }}</div>
                    <div>Working Correctly</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number stat-bad">{{ rows|selectattr('has_issues', 'equalto', true)|list|length }}</div>
                    <div>Need Attention</div>
                </div>
            </div>
            
            <div class="filter-controls">
                <label><input type="checkbox" id="issues-filter"> Show only issues</label>
                <label>Case ID: <input type="text" id="case-filter" placeholder="Filter by case..."></label>
                <label>Form Type: 
                    <select id="form-filter">
                        <option value="">All Forms</option>
                        {% for form_type in rows|map(attribute='form_type')|unique %}
                        <option value="{{ form_type }}">{{ form_type }}</option>
                        {% endfor %}
                    </select>
                </label>
            </div>
            
            {% for row in rows %}
            <div class="extraction-row {{ 'has-issues' if row.has_issues else 'no-issues' }}" 
                 data-case-id="{{ row.case_id }}" data-form-type="{{ row.form_type }}">
                <div class="extraction-header">
                    <div>
                        <div class="extraction-title">
                            {{ row.form_type }} - {{ row.field }}
                        </div>
                        <div class="extraction-meta">
                            Case {{ row.case_id }} | {{ row.year }} | {{ row.name or 'No Name' }} | {{ row.ssn or 'No SSN' }}
                        </div>
                    </div>
                    <div>
                        <span class="status-badge {{ 'status-bad' if row.has_issues else 'status-good' }}">
                            {{ 'Issues Found' if row.has_issues else 'Working' }}
                        </span>
                        <button class="toggle-btn" onclick="toggleDetails('details-{{ loop.index }}')">
                            Toggle Details
                        </button>
                    </div>
                </div>
                
                <div class="extraction-body">
                    <div class="field-details">
                        <div class="detail-box">
                            <div class="detail-label">Extracted Value</div>
                            <div class="detail-value">{{ row.extracted_value }}</div>
                        </div>
                        <div class="detail-box">
                            <div class="detail-label">Total Matches Found</div>
                            <div class="detail-value">{{ row.match_info.total_matches }}</div>
                        </div>
                        <div class="detail-box">
                            <div class="detail-label">Current Regex</div>
                            <div class="regex-display">{{ row.current_regex or 'No regex pattern defined' }}</div>
                        </div>
                    </div>
                    
                    <div id="details-{{ loop.index }}" class="hidden">
                        <div class="matches-section">
                            {% if row.match_info.exact_matches %}
                            <div class="match-type">
                                <div class="match-type-header">✅ Exact Matches ({{ row.match_info.exact_matches|length }})</div>
                                {% for match in row.match_info.exact_matches %}
                                <div class="match-item">
                                    <div><strong>Position:</strong> {{ match.position }}</div>
                                    <div class="context-display">{{ match.pre_context }}<span class="highlight-exact">{{ match.matched_text }}</span>{{ match.post_context }}</div>
                                </div>
                                {% endfor %}
                            </div>
                            {% endif %}
                            
                            {% if row.match_info.regex_matches %}
                            <div class="match-type">
                                <div class="match-type-header">🔧 Regex Matches ({{ row.match_info.regex_matches|length }})</div>
                                {% for match in row.match_info.regex_matches %}
                                <div class="match-item">
                                    {% if match.type == 'regex_error' %}
                                        <div style="color: #dc3545;"><strong>Regex Error:</strong> {{ match.error }}</div>
                                    {% else %}
                                        <div><strong>Position:</strong> {{ match.position }}</div>
                                        <div><strong>Full Match:</strong> "{{ match.matched_text }}"</div>
                                        <div><strong>Captured Value:</strong> "{{ match.captured_value }}"</div>
                                        <div><strong>Matches Extracted:</strong> 
                                            <span style="color: {{ '#28a745' if match.matches_extracted else '#dc3545' }}">
                                                {{ '✓' if match.matches_extracted else '✗' }}
                                            </span>
                                        </div>
                                        <div class="context-display">{{ match.pre_context }}<span class="highlight-regex">{{ match.matched_text }}</span>{{ match.post_context }}</div>
                                    {% endif %}
                                </div>
                                {% endfor %}
                            </div>
                            {% endif %}
                            
                            {% if row.match_info.fuzzy_matches %}
                            <div class="match-type">
                                <div class="match-type-header">🔍 Fuzzy Matches ({{ row.match_info.fuzzy_matches|length }})</div>
                                {% for match in row.match_info.fuzzy_matches %}
                                <div class="match-item">
                                    <div><strong>Position:</strong> {{ match.position }}</div>
                                    <div class="context-display">{{ match.pre_context }}<span class="highlight-fuzzy">{{ match.matched_text }}</span>{{ match.post_context }}</div>
                                </div>
                                {% endfor %}
                            </div>
                            {% endif %}
                            
                            {% if row.match_info.total_matches == 0 %}
                            <div class="match-type">
                                <div class="match-type-header" style="color: #dc3545;">❌ No Matches Found</div>
                                <div class="match-item">
                                    <p>The extracted value "{{ row.extracted_value }}" was not found in the raw text using exact, regex, or fuzzy matching.</p>
                                    <p>This could indicate:</p>
                                    <ul>
                                        <li>OCR errors in the original document</li>
                                        <li>The value was calculated/derived rather than directly extracted</li>
                                        <li>The extraction logic has bugs</li>
                                        <li>The raw text API returned different content</li>
                                    </ul>
                                </div>
                            </div>
                            {% endif %}
                        </div>
                        
                        {% if row.suggestions %}
                        <div class="suggestions">
                            <h4>💡 Suggestions</h4>
                            {% for suggestion in row.suggestions %}
                            <div class="suggestion-item">{{ suggestion }}</div>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    '''
    
    template = Template(template_str)
    html = template.render(rows=all_rows)
    with open(output_html, "w", encoding='utf-8') as f:
        f.write(html)
    print(f"Enhanced HTML report written to {output_html}")

def main():
    case_ids = sys.argv[1:]
    if not case_ids:
        case_ids = input("Enter case IDs (comma separated): ").split(",")
        case_ids = [c.strip() for c in case_ids if c.strip()]
    
    all_rows = []
    for case_id in case_ids:
        print(f"Processing case {case_id}...")
        try:
            rows = compare_and_collect(case_id)
            all_rows.extend(rows)
            print(f"  Found {len(rows)} extractions")
        except Exception as e:
            print(f"  Error processing case {case_id}: {e}")
    
    if all_rows:
        render_html_report(all_rows)
        print(f"\nProcessed {len(all_rows)} total extractions")
        issues = sum(1 for row in all_rows if row['has_issues'])
        print(f"Found {issues} extractions with issues")
    else:
        print("No data to process")

if __name__ == "__main__":
    main() 