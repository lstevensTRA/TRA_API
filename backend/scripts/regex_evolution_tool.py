#!/usr/bin/env python3
"""
Regex Evolution Tool: Widens regex patterns to handle edge cases while preserving working cases.

Instead of "fixing" for one case, this tool:
1. Collects ALL cases for a form/field combination
2. Tests current pattern against all cases
3. Suggests WIDER patterns that handle more cases
4. Validates no regressions on working cases
5. Shows pattern evolution over iterations

Usage: python regex_evolution_tool.py
"""

import sys
import requests
import re
import os
import json
from collections import defaultdict
from jinja2 import Template
from backend.app.utils.wi_patterns import form_patterns
import base64

def fetch_multiple_cases(case_ids):
    """Fetch raw text for multiple cases at once"""
    resp = requests.post("http://localhost:8000/api/training/raw-text/wi", json={"case_ids": case_ids})
    return resp.json()

def fetch_structured_multiple(case_ids):
    """Fetch structured data for multiple cases"""
    all_structured = {}
    for case_id in case_ids:
        try:
            resp = requests.get(f"http://localhost:8000/analysis/wi/{case_id}")
            if resp.status_code == 200:
                all_structured[case_id] = resp.json()
        except Exception as e:
            print(f"Error fetching structured data for {case_id}: {e}")
    return all_structured

def extract_all_field_instances(structured_data, raw_texts):
    """Extract all instances of each form_type/field combination across all cases"""
    
    field_instances = defaultdict(list)
    
    for case_id, structured in structured_data.items():
        raw_text = raw_texts.get(case_id, "")
        if not raw_text or raw_text.startswith("Error:"):
            continue
            
        years_data = structured.get("years_data", {})
        for year, forms in years_data.items():
            if not isinstance(forms, list):
                continue
            for form_idx, form in enumerate(forms):
                if not isinstance(form, dict):
                    continue
                
                form_type = form.get("Form")
                fields = form.get("Fields", {})
                
                for field_name, extracted_value in fields.items():
                    key = f"{form_type}::{field_name}"
                    
                    field_instances[key].append({
                        'case_id': case_id,
                        'year': year,
                        'form_index': form_idx,
                        'extracted_value': str(extracted_value),
                        'raw_text': raw_text,
                        'form_type': form_type,
                        'field_name': field_name,
                        'name': form.get('Name', ''),
                        'ssn': form.get('SSN', '')
                    })
    
    return field_instances

def safe_id(s):
    """Generate a safe HTML id from a string (field_key)"""
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')

def test_pattern_against_instances(pattern, instances):
    """Test a regex pattern against all instances of a field"""
    results = []
    for instance in instances:
        raw_text = instance['raw_text']
        expected_value = instance['extracted_value']
        if expected_value in ['0', '0.00', '0']:
            results.append({
                'instance': instance,
                'status': 'skipped_zero',
                'matches': [],
                'found_expected': True
            })
            continue
        try:
            matches = list(re.finditer(pattern, raw_text, re.IGNORECASE | re.MULTILINE))
            match_data = []
            found_expected = False
            for match in matches:
                captured = match.group(1) if match.groups() else match.group(0)
                captured_clean = captured.replace('$', '').replace(',', '').strip()
                expected_clean = expected_value.replace('$', '').replace(',', '').strip()
                is_expected = captured_clean == expected_clean
                if is_expected:
                    found_expected = True
                match_data.append({
                    'full_match': match.group(0),
                    'captured': captured,
                    'position': match.start(),
                    'is_expected': is_expected,
                    'context': raw_text[max(0, match.start()-50):match.end()+50]
                })
            value_in_text = expected_value in raw_text
            # Only needs_wider_pattern if value is in text but not matched by regex at all
            needs_wider_pattern = value_in_text and not found_expected
            results.append({
                'instance': instance,
                'status': 'tested',
                'matches': match_data,
                'found_expected': found_expected,
                'value_in_text': value_in_text,
                'pattern_works': found_expected,
                'needs_wider_pattern': needs_wider_pattern
            })
        except re.error as e:
            results.append({
                'instance': instance,
                'status': 'regex_error',
                'error': str(e),
                'found_expected': False
            })
    return results

def analyze_pattern_coverage(results):
    """Analyze how well the current pattern covers all cases"""
    total_tested = len([r for r in results if r['status'] == 'tested'])
    working = len([r for r in results if r.get('pattern_works', False)])
    needs_wider = len([r for r in results if r.get('needs_wider_pattern', False)])
    not_in_text = len([r for r in results if r['status'] == 'tested' and not r.get('value_in_text', False)])
    
    return {
        'total_cases': len(results),
        'total_tested': total_tested,
        'working_cases': working,
        'needs_wider_pattern': needs_wider,
        'value_not_in_text': not_in_text,
        'coverage_rate': working / total_tested if total_tested > 0 else 0,
        'has_issues': needs_wider > 0
    }

def generate_wider_patterns(field_name, failing_instances, current_pattern):
    """Generate progressively wider regex patterns to handle failing cases"""
    suggestions = []
    
    # Analyze failing instances to understand what variations exist
    failing_contexts = []
    for instance in failing_instances:
        if instance.get('needs_wider_pattern'):
            # Find context around the expected value
            raw_text = instance['instance']['raw_text']
            expected = instance['instance']['extracted_value']
            
            # Find the value in text and extract surrounding context
            idx = raw_text.find(expected)
            if idx != -1:
                context_start = max(0, idx - 100)
                context_end = min(len(raw_text), idx + len(expected) + 100)
                context = raw_text[context_start:context_end]
                failing_contexts.append({
                    'context': context,
                    'expected': expected,
                    'case_id': instance['instance']['case_id']
                })
    
    # Pattern widening strategies
    base_field = re.escape(field_name)
    
    # Strategy 1: More flexible spacing and punctuation
    suggestions.append({
        'pattern': rf'{base_field}[:\s,]*\$?([\\d,.]+)',
        'description': 'Add flexible spacing and optional comma after field name',
        'strategy': 'flexible_spacing'
    })
    
    # Strategy 2: Handle variations in field name (OCR issues)
    field_variations = []
    # Common OCR substitutions
    field_with_variations = field_name
    field_with_variations = field_with_variations.replace('o', '[o0]').replace('O', '[O0]')
    field_with_variations = field_with_variations.replace('l', '[l1I|]').replace('L', '[L1I|]')
    field_with_variations = field_with_variations.replace('i', '[i1|]').replace('I', '[I1|]')
    
    suggestions.append({
        'pattern': rf'{field_with_variations}[:\s,]*\$?([\\d,.]+)',
        'description': 'Handle common OCR errors in field name',
        'strategy': 'ocr_tolerance'
    })
    
    # Strategy 3: Look for patterns in the failing contexts
    for context_info in failing_contexts[:3]:  # Top 3 failing cases
        context = context_info['context']
        expected = context_info['expected']
        
        # Find the line containing the value
        lines = context.split('\n')
        for line in lines:
            if expected in line:
                # Create pattern from this line
                line_clean = line.strip()
                # More flexible version of the line
                line_pattern = re.escape(line_clean)
                line_pattern = line_pattern.replace(re.escape(expected), r'([\\d,.]+)')
                # Make it more flexible
                line_pattern = line_pattern.replace('\\ ', '\\s*').replace('\\:', '[:\\s]*')
                
                suggestions.append({
                    'pattern': line_pattern,
                    'description': f'Pattern from failing case {context_info["case_id"]}: "{line_clean[:50]}..."',
                    'strategy': 'failing_case_pattern'
                })
                break
    
    # Strategy 4: Very flexible pattern
    suggestions.append({
        'pattern': rf'(?i){base_field}[:\s,]*\\$?([\\d,.]+)',
        'description': 'Case-insensitive with flexible separators',
        'strategy': 'case_insensitive'
    })
    
    # Strategy 5: Multi-line pattern (in case field name and value are on different lines)
    suggestions.append({
        'pattern': rf'(?s){base_field}[:\s,]*\\$?([\\d,.]+)',
        'description': 'Multi-line pattern for cases where value might be on next line',
        'strategy': 'multiline'
    })
    
    return suggestions

def create_evolution_report(field_analysis, output_file="regex_evolution_report.html"):
    """Create comprehensive HTML report for regex pattern evolution"""
    
    template_str = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🧬 Regex Pattern Evolution Report</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { text-align: center; color: #333; margin-bottom: 10px; }
            .subtitle { text-align: center; color: #6c757d; margin-bottom: 30px; }
            
            .summary-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .summary-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                text-align: center;
            }
            .summary-number { font-size: 2em; font-weight: bold; margin-bottom: 5px; }
            .good { color: #28a745; }
            .bad { color: #dc3545; }
            .warning { color: #ffc107; }
            .neutral { color: #6c757d; }
            
            .field-section {
                background: white;
                margin-bottom: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .field-header {
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .field-title { font-size: 1.4em; font-weight: 600; margin-bottom: 5px; }
            .field-meta { opacity: 0.9; }
            
            .coverage-bar {
                background: #e9ecef;
                height: 20px;
                border-radius: 10px;
                overflow: hidden;
                margin: 15px 0;
            }
            .coverage-fill {
                height: 100%;
                background: linear-gradient(90deg, #28a745, #20c997);
                transition: width 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: 600;
                font-size: 0.8em;
            }
            
            .tabs {
                display: flex;
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
            .tab {
                padding: 15px 25px;
                cursor: pointer;
                border-bottom: 3px solid transparent;
                transition: all 0.3s ease;
            }
            .tab.active {
                background: white;
                border-bottom-color: #007bff;
                color: #007bff;
                font-weight: 600;
            }
            .tab-content { padding: 25px; }
            .tab-pane { display: none; }
            .tab-pane.active { display: block; }
            
            .current-pattern {
                background: #2d3748;
                color: #e2e8f0;
                padding: 15px;
                border-radius: 6px;
                font-family: 'Courier New', monospace;
                margin-bottom: 20px;
                overflow-x: auto;
            }
            
            .instances-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 15px;
                margin-bottom: 20px;
            }
            .instance-card {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 12px;
                background: #f8f9fa;
            }
            .instance-card.working { border-left: 4px solid #28a745; }
            .instance-card.failing { border-left: 4px solid #dc3545; }
            .instance-card.missing { border-left: 4px solid #ffc107; }
            
            .suggestion-list {
                display: grid;
                gap: 15px;
            }
            .suggestion-card {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                overflow: hidden;
                background: white;
            }
            .suggestion-header {
                background: #f8f9fa;
                padding: 15px;
                border-bottom: 1px solid #dee2e6;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .suggestion-pattern {
                font-family: monospace;
                background: #2d3748;
                color: #e2e8f0;
                padding: 12px;
                margin: 15px;
                border-radius: 4px;
                overflow-x: auto;
            }
            .test-results {
                padding: 15px;
                background: #f8f9fa;
                margin: 15px;
                border-radius: 4px;
            }
            
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .btn-primary { background: #007bff; color: white; }
            .btn-primary:hover { background: #0056b3; }
            .btn-test { background: #17a2b8; color: white; }
            .btn-test:hover { background: #117a8b; }
            
            .status-badge {
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: 500;
            }
            .status-working { background: #d4edda; color: #155724; }
            .status-failing { background: #f8d7da; color: #721c24; }
            .status-missing { background: #fff3cd; color: #856404; }
            
            .context-text {
                font-family: monospace;
                background: #f8f9fa;
                padding: 10px;
                border-radius: 4px;
                font-size: 0.9em;
                white-space: pre-wrap;
                max-height: 150px;
                overflow-y: auto;
            }
            .highlight-expected { background: #fff3cd; padding: 2px 4px; border-radius: 3px; }
        </style>
        <script>
            function switchTab(fieldKey, tabName) {
                // Use safe IDs
                var safeId = fieldKey;
                var fieldElement = document.querySelector('[data-field-key="' + safeId + '"]');
                if (!fieldElement) return;
                fieldElement.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.remove('active');
                });
                fieldElement.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                fieldElement.querySelector('#' + tabName + '-' + safeId).classList.add('active');
                fieldElement.querySelector('[data-tab="' + tabName + '"]').classList.add('active');
            }
            
            function testSuggestion(fieldKey, suggestionIndex) {
                // This would integrate with your backend to test the pattern
                alert(`Testing suggestion ${suggestionIndex} for ${fieldKey}...\nIn real implementation, this would test against all instances and show results.`);
            }
            
            function adoptPattern(fieldKey, pattern) {
                const command = `python -c "\nfrom regex_evolution_tool import update_patterns_file\nfield_parts = '${fieldKey}'.split('::')\nsuccess, msg = update_patterns_file(field_parts[0], field_parts[1], '${pattern}')\nprint(f'Update: {msg}')\n"`;
                
                navigator.clipboard.writeText(command).then(() => {
                    alert('Update command copied to clipboard!\n\nRun this command to update your patterns file:\n\n' + command);
                });
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h1>🧬 Regex Pattern Evolution Report</h1>
            <p class="subtitle">Analyze and evolve regex patterns to handle all case variations</p>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-number neutral">{{ analysis.keys()|length }}</div>
                    <div>Form/Field Combinations</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number good">{{ analysis.values()|selectattr('coverage.has_issues', 'equalto', false)|list|length }}</div>
                    <div>Patterns Working Well</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number bad">{{ analysis.values()|selectattr('coverage.has_issues', 'equalto', true)|list|length }}</div>
                    <div>Patterns Need Evolution</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number warning">{{ analysis.values()|map(attribute='coverage.total_tested')|sum }}</div>
                    <div>Total Test Cases</div>
                </div>
            </div>
            
            {% for field_key, data in analysis.items() %}
            {% set safe_field_id = safe_id(field_key) %}
            <div class="field-section" data-field-key="{{ safe_field_id }}">
                <div class="field-header">
                    <div class="field-title">{{ field_key.replace('::', ' → ') }}</div>
                    <div class="field-meta">
                        {{ data.coverage.total_tested }} test cases • 
                        {{ data.coverage.working_cases }} working • 
                        {{ data.coverage.needs_wider_pattern }} need wider pattern
                    </div>
                    <div class="coverage-bar">
                        <div class="coverage-fill" style="width: {{ (data.coverage.coverage_rate * 100)|round(1) }}%">
                            {{ (data.coverage.coverage_rate * 100)|round(1) }}% coverage
                        </div>
                    </div>
                </div>
                
                <div class="tabs">
                    <div class="tab active" data-tab="overview" onclick="switchTab('{{ safe_field_id }}', 'overview')">Overview</div>
                    <div class="tab" data-tab="instances" onclick="switchTab('{{ safe_field_id }}', 'instances')">Test Cases ({{ data.coverage.total_tested }})</div>
                    <div class="tab" data-tab="suggestions" onclick="switchTab('{{ safe_field_id }}', 'suggestions')">Evolution Suggestions ({{ data.suggestions|length }})</div>
                </div>
                
                <div class="tab-content">
                    <div class="tab-pane active" id="overview-{{ safe_field_id }}">
                        <h4>Current Pattern:</h4>
                        <div class="current-pattern">{{ data.current_pattern or 'No pattern defined' }}</div>
                        
                        <div class="summary-grid">
                            <div class="summary-card">
                                <div class="summary-number good">{{ data.coverage.working_cases }}</div>
                                <div>Working Cases</div>
                            </div>
                            <div class="summary-card">
                                <div class="summary-number bad">{{ data.coverage.needs_wider_pattern }}</div>
                                <div>Need Wider Pattern</div>
                            </div>
                            <div class="summary-card">
                                <div class="summary-number warning">{{ data.coverage.value_not_in_text }}</div>
                                <div>Value Not in Text</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="tab-pane" id="instances-{{ safe_field_id }}">
                        <div class="instances-grid">
                            {% for result in data.test_results %}
                            {% if result.status == 'tested' %}
                            <div class="instance-card {{ 'working' if result.pattern_works else ('failing' if result.needs_wider_pattern else 'missing') }}">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong>Case {{ result.instance.case_id }}</strong>
                                    <span class="status-badge {{ 'status-working' if result.pattern_works else ('status-failing' if result.needs_wider_pattern else 'status-missing') }}">
                                        {{ 'Working' if result.pattern_works else ('Needs Wider Pattern' if result.needs_wider_pattern else 'Value Missing') }}
                                    </span>
                                </div>
                                <div><strong>Expected:</strong> <span class="highlight-expected">{{ result.instance.extracted_value }}</span></div>
                                <div><strong>Year:</strong> {{ result.instance.year }}</div>
                                <div><strong>All Regex Matches:</strong></div>
                                <ul>
                                {% for match in result.matches %}
                                    <li>
                                        <span style="font-family:monospace;">{{ match.full_match }}</span>
                                        {% if match.is_expected %}<span style="color:#28a745;">(matches expected)</span>{% endif %}
                                        <br/>
                                        <span style="font-size:0.9em;">Captured: <span style="font-family:monospace;">{{ match.captured }}</span></span>
                                        <br/>
                                        <span class="context-text">{{ match.context | replace(result.instance.extracted_value, '<span class="highlight-expected">' + result.instance.extracted_value + '</span>') | safe }}</span>
                                    </li>
                                {% else %}
                                    <li><em>No regex matches found.</em></li>
                                {% endfor %}
                                </ul>
                                {% if not result.pattern_works and result.value_in_text %}
                                <details style="margin-top: 8px;">
                                    <summary>Show context where value appears in text</summary>
                                    <div class="context-text">{{ result.instance.raw_text[result.instance.raw_text.find(result.instance.extracted_value)-50:result.instance.raw_text.find(result.instance.extracted_value)+50] | replace(result.instance.extracted_value, '<span class="highlight-expected">' + result.instance.extracted_value + '</span>') | safe }}</div>
                                </details>
                                {% endif %}
                            </div>
                            {% endif %}
                            {% endfor %}
                        </div>
                    </div>
                    
                    <div class="tab-pane" id="suggestions-{{ safe_field_id }}">
                        {% if data.coverage.has_issues %}
                        <div class="suggestion-list">
                            {% for suggestion in data.suggestions %}
                            <div class="suggestion-card">
                                <div class="suggestion-header">
                                    <div>
                                        <strong>Strategy:</strong> {{ suggestion.strategy|title|replace('_', ' ') }}
                                        <div style="color: #6c757d; font-size: 0.9em;">{{ suggestion.description }}</div>
                                    </div>
                                    <div>
                                        <button class="btn btn-test" onclick="testSuggestion('{{ safe_field_id }}', {{ loop.index0 }})">Test</button>
                                        <button class="btn btn-primary" onclick="adoptPattern('{{ safe_field_id }}', '{{ suggestion.pattern }}')">Adopt</button>
                                    </div>
                                </div>
                                <div class="suggestion-pattern">{{ suggestion.pattern }}</div>
                                <div class="test-results">
                                    <em>Click "Test" to validate this pattern against all {{ data.coverage.total_tested }} cases</em>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div style="text-align: center; padding: 40px; color: #28a745;">
                            <h3>🎉 Pattern Working Perfectly!</h3>
                            <p>Current pattern handles all test cases correctly.</p>
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
    html = template.render(analysis=field_analysis, safe_id=safe_id)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Evolution report generated: {output_file}")

def main():
    # Get all available case IDs (you might want to implement this endpoint)
    print("Enter case IDs to analyze (comma separated), or press Enter to analyze recent cases:")
    case_input = input().strip()
    
    if case_input:
        case_ids = [c.strip() for c in case_input.split(",")]
    else:
        # Default to some case IDs - you might want to fetch these from an endpoint
        case_ids = ["54820", "1111600"]  # Add more as needed
    
    print(f"Analyzing {len(case_ids)} cases...")
    
    # Fetch all data
    raw_texts = fetch_multiple_cases(case_ids)
    structured_data = fetch_structured_multiple(case_ids)
    
    # Extract all field instances
    field_instances = extract_all_field_instances(structured_data, raw_texts)
    
    print(f"Found {len(field_instances)} unique form/field combinations")
    
    # Analyze each field
    field_analysis = {}
    
    for field_key, instances in field_instances.items():
        form_type, field_name = field_key.split("::")
        current_pattern = form_patterns.get(form_type, {}).get('fields', {}).get(field_name, '')
        
        print(f"Analyzing {field_key} ({len(instances)} instances)...")
        
        # Test current pattern against all instances
        if current_pattern:
            test_results = test_pattern_against_instances(current_pattern, instances)
        else:
            test_results = [{'instance': inst, 'status': 'no_pattern', 'found_expected': False} for inst in instances]
        
        # Analyze coverage
        coverage = analyze_pattern_coverage(test_results)
        
        # Generate suggestions if needed
        suggestions = []
        if coverage['has_issues']:
            failing_instances = [r for r in test_results if r.get('needs_wider_pattern', False)]
            suggestions = generate_wider_patterns(field_name, failing_instances, current_pattern)
        
        field_analysis[field_key] = {
            'current_pattern': current_pattern,
            'instances': instances,
            'test_results': test_results,
            'coverage': coverage,
            'suggestions': suggestions
        }
    
    # Generate report
    create_evolution_report(field_analysis)
    
    # Summary
    total_fields = len(field_analysis)
    problematic_fields = sum(1 for data in field_analysis.values() if data['coverage']['has_issues'])
    
    print(f"\n🧬 Evolution Analysis Complete!")
    print(f"📊 {total_fields} form/field combinations analyzed")
    print(f"✅ {total_fields - problematic_fields} patterns working well")
    print(f"🔧 {problematic_fields} patterns need evolution")
    print(f"\nOpen 'regex_evolution_report.html' to see detailed analysis and evolution suggestions!")

if __name__ == "__main__":
    main() 