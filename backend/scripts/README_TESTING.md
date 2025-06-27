# IRS Standards Testing Strategy

This document outlines the comprehensive testing strategy to ensure IRS Standards work correctly for every county and state.

## Overview

The goal is to validate that your IRS Standards API returns the same values as the direct Logiqs API across all counties, states, and household configurations.

## Testing Components

### 1. County Database Builder (`build_county_database.py`)

**Purpose**: Build a comprehensive database of all counties across all states.

**What it does**:
- Fetches all counties for every state from Logiqs API
- Creates a structured database for reference
- Generates validation samples for each state
- Creates a city-to-county mapping structure

**Usage**:
```bash
cd backend/scripts
# Set your authentication cookies first
export COOKIE_HEADER="your_cookie_header_here"
export USER_AGENT="your_user_agent_here"
python3 build_county_database.py
```

**Output**:
- `data/counties_database.json` - Complete county database
- `data/validation_samples.json` - Sample IRS Standards for each state
- `data/city_county_mapping_structure.json` - Structure for city mapping

### 2. Comprehensive Testing Suite (`test_irs_standards_comprehensive.py`)

**Purpose**: Test IRS Standards across multiple counties and household sizes.

**What it tests**:
- 8 major counties across different states
- 6 different household configurations
- Direct API vs your API comparison
- 48 total test cases

**Household configurations tested**:
- Single person under 65
- Two people under 65
- One under 65, one over 65
- Two under 65, one over 65
- Single person over 65
- Two people over 65

**Usage**:
```bash
cd backend/scripts
# Set your authentication cookies first
export COOKIE_HEADER="your_cookie_header_here"
export USER_AGENT="your_user_agent_here"
python3 test_irs_standards_comprehensive.py
```

**Output**:
- `test_results/irs_standards_test_results_YYYYMMDD_HHMMSS.json` - Detailed test results
- Console output with pass/fail summary

### 3. Validation Endpoint (`/irs-standards/validate`)

**Purpose**: On-demand validation of specific counties.

**What it does**:
- Tests a specific county across multiple household sizes
- Compares your API vs direct Logiqs API
- Returns detailed comparison results

**Usage**:
```bash
# Test Cook County (708) with default household sizes
curl -X POST "http://localhost:8000/irs-standards/validate" \
  -H "Content-Type: application/json" \
  -d '{"county_id": 708}'

# Test with custom household sizes
curl -X POST "http://localhost:8000/irs-standards/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "county_id": 708,
    "household_sizes": [
      {"under_65": 1, "over_65": 0},
      {"under_65": 2, "over_65": 1}
    ]
  }'
```

## Testing Strategy

### Phase 1: Manual County Mapping
1. **Identify major cities** that are commonly used in your cases
2. **Add manual mappings** to the `county_mapping` dictionary in `irs_standards_routes.py`
3. **Test each mapping** using the validation endpoint
4. **Document any discrepancies** and investigate

### Phase 2: Automated Testing
1. **Run the comprehensive test suite** to identify issues
2. **Analyze failures** to understand patterns
3. **Fix county lookup logic** based on findings
4. **Re-run tests** to validate fixes

### Phase 3: Full Database Validation
1. **Build the county database** to get all counties
2. **Create a city-to-county mapping** using external data sources
3. **Test a sample of counties** from each state
4. **Implement intelligent fallback logic** for unmapped cities

## Current Manual Mappings

The following cities are currently manually mapped:

### Wisconsin (WI)
- Oak Creek → Milwaukee County (3111)
- Milwaukee → Milwaukee County (3111)
- Madison → Dane County (3101)
- Green Bay → Brown County (3103)

### California (CA)
- Oakland → Alameda County (185)
- San Francisco → San Francisco County (186)
- Los Angeles → Los Angeles County (187)
- San Diego → San Diego County (188)
- Covina → Los Angeles County (189)

### Illinois (IL)
- Chicago → Cook County (708)
- Oak Park → Cook County (708)
- Evanston → Cook County (708)
- Skokie → Cook County (708)

## Getting Authentication Cookies

To run the testing scripts, you need valid authentication cookies from Logiqs:

1. **Log into Logiqs** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Network tab**
4. **Make any API request** (like getting counties)
5. **Find the request** and copy the Cookie header
6. **Copy the User-Agent** from the request headers

Example:
```bash
export COOKIE_HEADER="ASP.NET_SessionId=abc123; .ASPXAUTH=def456"
export USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

## Interpreting Test Results

### Success Criteria
- **100% match** between your API and direct Logiqs API
- **All key fields** match: Food, Housing, OperatingCostCar, HealthOutOfPocket, etc.
- **No authentication errors**
- **No API errors**

### Common Issues
1. **County ID mismatch** - Wrong county selected for city
2. **Authentication failures** - Expired or invalid cookies
3. **API rate limiting** - Too many requests too quickly
4. **Network timeouts** - Slow API responses

### Investigation Steps
1. **Check county lookup logic** - Verify city-to-county mapping
2. **Validate authentication** - Ensure cookies are valid
3. **Test direct API** - Confirm Logiqs API is working
4. **Check parameters** - Verify household size parameters
5. **Review error logs** - Look for specific error messages

## Continuous Monitoring

### Recommended Testing Schedule
- **Daily**: Test major counties (top 10 by case volume)
- **Weekly**: Run comprehensive test suite
- **Monthly**: Full database validation
- **On deployment**: Test all manual mappings

### Monitoring Metrics
- **Success rate** should be 100%
- **Response time** should be under 5 seconds
- **Error rate** should be 0%
- **County accuracy** should be 100%

## Future Enhancements

### Automated City Mapping
1. **Integrate with external APIs** (US Census, Google Maps)
2. **Build machine learning model** for city-to-county prediction
3. **Create crowdsourced mapping** for edge cases

### Real-time Validation
1. **Add validation to case processing**
2. **Alert on discrepancies**
3. **Auto-correct common issues**

### Performance Optimization
1. **Cache county lookups**
2. **Batch API requests**
3. **Implement retry logic**

## Troubleshooting

### Authentication Issues
```bash
# Check if cookies are valid
curl -H "Cookie: $COOKIE_HEADER" "https://tps.logiqs.com/API/CaseInterview/GetCounties?state=CA"
```

### County Lookup Issues
```bash
# Test specific county
curl "http://localhost:8000/irs-standards/standards?county_id=708&family_members_under_65=1&family_members_over_65=0"
```

### API Comparison
```bash
# Compare your API vs direct
curl "http://localhost:8000/irs-standards/validate" -X POST -H "Content-Type: application/json" -d '{"county_id": 708}'
```

## Support

If you encounter issues:
1. **Check the logs** for detailed error messages
2. **Verify authentication** is still valid
3. **Test with known working cases** first
4. **Contact the development team** with specific error details 