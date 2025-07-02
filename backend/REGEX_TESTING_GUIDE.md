# 🔧 Comprehensive Regex Testing Guide

## 📊 **Endpoint Analysis Summary**

Your backend has **77 total endpoints** across 15 categories. Here are the key endpoints for regex testing and WI analysis:

### 🎯 **WI-Related Endpoints (14 total)**

#### **Core Analysis Endpoints:**
- `GET /analysis/wi/{case_id}` - **Summary analysis** with totals, SE/non-SE breakdowns
- `GET /transcripts/analysis/wi/{case_id}` - **Regex analysis** with confidence scores
- `GET /transcripts/raw/wi/{case_id}` - **Raw text** from PDFs

#### **Batch Processing:**
- `POST /batch/wi-structured` - Batch structured data
- `POST /regex-review/batch/wi` - Batch regex review
- `POST /wi-scoped` - Batch scoped parsing

#### **Enhanced Analysis:**
- `GET /wi/{case_id}/enhanced` - Enhanced WI analysis with pattern learning

### 🔧 **Regex Testing Endpoints (11 total)**
- `GET /transcripts/raw/wi/{case_id}` - Raw text for manual inspection
- `GET /transcripts/analysis/wi/{case_id}` - Regex extraction results
- `GET /pattern-learning/patterns` - Pattern performance metrics
- `POST /regex-review/batch/wi` - Batch regex testing

## 🔄 **Workflow for Comparing Raw Text with Regex Extraction**

### **Step 1: Authentication**
```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### **Step 2: Get Raw Text**
```bash
curl -X GET "http://localhost:8000/transcripts/raw/wi/54820"
```
**Purpose:** See the actual text content from PDFs for manual inspection.

### **Step 3: Get Regex Analysis**
```bash
curl -X GET "http://localhost:8000/transcripts/analysis/wi/54820"
```
**Purpose:** See what regex patterns extracted with confidence scores and source lines.

### **Step 4: Get Summary Analysis**
```bash
curl -X GET "http://localhost:8000/analysis/wi/54820"
```
**Purpose:** Get calculated totals and breakdowns (SE, non-SE, withholdings).

## 🛠️ **Tools for Testing and Improvement**

### **1. Automated Testing Script**
```bash
python3 test_regex_workflow.py
```
This script provides:
- Interactive case testing
- Raw text vs regex comparison
- Specific pattern testing
- Confidence score analysis
- Issue identification and suggestions

### **2. Pattern Review Endpoint**
```bash
curl -X GET "http://localhost:8000/pattern-learning/regex-review/wi/54820"
```
**Purpose:** Detailed analysis of regex performance with suggestions.

### **3. Batch Testing**
```bash
curl -X POST "http://localhost:8000/batch/regex-review/wi" \
  -H "Content-Type: application/json" \
  -d '{"case_ids": ["54820", "54821", "54822"]}'
```
**Purpose:** Test multiple cases at once to validate pattern improvements.

## 📝 **Pattern Improvement Process**

### **1. Identify Issues**
- Look for low confidence scores (< 0.7)
- Check for missing field extractions
- Review source lines for accuracy

### **2. Analyze Raw Text**
- Find the actual text that should be extracted
- Note variations in formatting
- Identify edge cases

### **3. Update Patterns**
- Edit `backend/app/utils/wi_patterns.py`
- Test with specific cases
- Validate with multiple cases

### **4. Monitor Results**
- Track confidence scores
- Monitor extraction rates
- Validate with batch testing

## 📊 **Key Metrics to Monitor**

### **Extraction Quality:**
- **Field extraction rate:** fields found / expected fields
- **Confidence scores:** should be > 0.7 for good patterns
- **Source line accuracy:** extracted text matches raw text
- **Pattern coverage:** all expected form types detected

### **Performance Indicators:**
- **Total forms found** vs expected
- **Average confidence** across all extractions
- **Pattern success rate** by form type
- **False positive rate** (incorrect extractions)

## 🎯 **Quick Testing Commands**

### **Test a Single Case:**
```bash
# Get all data for case 54820
curl -X GET "http://localhost:8000/transcripts/raw/wi/54820" > raw_54820.json
curl -X GET "http://localhost:8000/transcripts/analysis/wi/54820" > regex_54820.json
curl -X GET "http://localhost:8000/analysis/wi/54820" > summary_54820.json
```

### **Compare Results:**
```bash
# Use jq to extract key metrics
jq '.comparison.overall_stats' regex_54820.json
jq '.summary.by_year' summary_54820.json
```

### **Test Specific Patterns:**
```python
# Use the testing script
python3 test_regex_workflow.py
# Then test specific patterns interactively
```

## 🔍 **Debugging Workflow**

### **When Patterns Don't Work:**

1. **Get raw text** and search for the expected field
2. **Check the exact format** in the raw text
3. **Test the pattern manually** against the raw text
4. **Update the pattern** in `wi_patterns.py`
5. **Test again** with the same case
6. **Validate** with multiple cases

### **Example Debugging Session:**
```bash
# 1. Get raw text
curl -X GET "http://localhost:8000/transcripts/raw/wi/54820" | jq '.raw_texts[0].raw_text' > raw.txt

# 2. Search for specific field
grep -i "wages" raw.txt

# 3. Test pattern manually
python3 -c "
import re
with open('raw.txt', 'r') as f:
    text = f.read()
pattern = r'Wages[,\s]*tips[,\s]*and[,\s]*other[,\s]*compensation[:\s]*\$?([\d,\.]+)'
matches = re.findall(pattern, text, re.IGNORECASE)
print('Matches:', matches)
"

# 4. Update pattern if needed and test again
```

## 📈 **Continuous Improvement Process**

### **Weekly Review:**
1. Run batch testing on recent cases
2. Identify patterns with low confidence
3. Review raw text for missed extractions
4. Update patterns based on findings
5. Validate improvements with test cases

### **Monthly Analysis:**
1. Review overall extraction rates
2. Analyze pattern performance trends
3. Identify new form types or formats
4. Update pattern library
5. Document improvements and lessons learned

## 🚀 **Getting Started**

1. **Run the analysis script:**
   ```bash
   python3 endpoint_analysis.py
   ```

2. **Test with a known case:**
   ```bash
   python3 test_regex_workflow.py
   ```

3. **Start with case 54820** (which we know works well)

4. **Use the three key endpoints** to understand the data flow

5. **Focus on low-confidence extractions** first

6. **Test improvements** with multiple cases

This workflow gives you everything you need to continuously improve your regex patterns without needing data storage - just run cases and validate the extraction quality! 