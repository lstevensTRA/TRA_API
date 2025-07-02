# TRA API Frontend Testing Tool

A lightweight React application for testing TRA API backend endpoints with smart dependency handling and real-time results display.

## Features

- **Simple Configuration Interface**: Easy server URL selection and case ID input
- **Auto-Discovery**: Automatically detects and tests available endpoints
- **Real-Time Results**: Live progress tracking and status updates
- **Smart Dependencies**: Handles authentication and endpoint dependencies
- **Export Options**: Save results as JSON or TXT files with full response data
- **Modern UI**: Clean, responsive design with status indicators

## Quick Start

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- TRA API backend running (default: http://localhost:8000)

### Installation

1. Navigate to the frontend testing tool directory:
```bash
cd backend/frontend-testing-tool
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Open your browser to `http://localhost:3000`

## Usage

### Configuration

1. **Server URL**: Select your backend server (localhost:8000, localhost:3000, or production)
2. **Case IDs**: Enter one or more case IDs separated by commas (e.g., "54820, 67890, 99999")
3. **Endpoint Selection**: Check/uncheck endpoint categories to test:
   - Authentication
   - Health Check
   - Client Profile
   - Transcripts
   - Analysis
   - Disposable Income
   - Income Comparison
   - Closing Letters
   - Case Management
   - IRS Standards
   - Tax Investigation

### Running Tests

1. Click the "🚀 Run Tests" button
2. Watch real-time progress in the progress bar
3. View results in the status grid and detailed table
4. Expand rows to see full response data
5. Export results using the action buttons

### Results Display

- **Status Grid**: Overview of each endpoint category with pass/fail counts
- **Results Table**: Detailed view of each endpoint test with:
  - Endpoint path and method
  - HTTP status code
  - Response time
  - Case ID
  - Expandable response data

### Export Options

- **Save JSON**: Full test results with complete response data in JSON format
- **Save TXT**: Human-readable summary with detailed response data in text format
- **Copy Results**: Quick copy to clipboard with full response data
- **Save Response Models**: Export only successful responses with their data models

## Configuration Persistence

The tool automatically saves your configuration to localStorage:
- Server URL
- Case IDs
- Selected endpoint categories

Your settings will be restored when you reload the page.

## Endpoint Categories

### Authentication
- `POST /auth/login` - User login
- `GET /auth/status` - Authentication status

### Health Check
- `GET /health/` - Backend health status

### Client Profile
- `GET /client_profile/{case_id}` - Get client profile data

### Transcripts
- `GET /transcripts/wi/{case_id}` - WI transcript discovery
- `GET /transcripts/at/{case_id}` - AT transcript discovery
- `GET /transcripts/raw/wi/{case_id}` - WI raw data
- `GET /transcripts/raw/at/{case_id}` - AT raw data

### Analysis
- `GET /analysis/wi/{case_id}` - WI analysis
- `GET /analysis/at/{case_id}` - AT analysis

### Disposable Income
- `GET /disposable-income/case/{case_id}` - Calculate disposable income

### Income Comparison
- `GET /income-comparison/{case_id}` - Income comparison analysis

### Closing Letters
- `GET /closing-letters/{case_id}` - Generate closing letters

### Case Management
- `GET /case-management/caseactivities/{case_id}` - Get case activities

### IRS Standards
- `GET /irs-standards/case/{case_id}` - Get IRS standards data

### Tax Investigation
- `GET /tax-investigation/compare/{case_id}` - Compare tax investigation data

## Output Format

### JSON Export Structure (Full Results)
```json
{
  "timestamp": "2024-12-26T10:00:00Z",
  "server": "http://localhost:8000",
  "casesTested": ["54820", "67890"],
  "summary": {
    "total": 45,
    "passed": 42,
    "failed": 3
  },
  "results": {
    "case_54820": {
      "GET /client_profile/54820": {
        "status": 200,
        "time": "340ms",
        "success": true,
        "response": {
          "case_id": "54820",
          "client_name": "John Doe",
          "filing_status": "Single",
          "income": 75000
        },
        "error": null,
        "endpoint": "GET /client_profile/54820",
        "caseId": "54820"
      }
    }
  },
  "errors": [
    {
      "endpoint": "GET /client_profile/67890",
      "error": "Case not found",
      "caseId": "67890",
      "status": 404,
      "responseTime": "200ms"
    }
  ]
}
```

### Response Models Export Structure
```json
{
  "timestamp": "2024-12-26T10:00:00Z",
  "server": "http://localhost:8000",
  "casesTested": ["54820", "67890"],
  "responseModels": {
    "case_54820": {
      "GET /client_profile/54820": {
        "response": {
          "case_id": "54820",
          "client_name": "John Doe",
          "filing_status": "Single",
          "income": 75000
        },
        "status": 200,
        "responseTime": "340ms"
      }
    }
  }
}
```

### TXT Export Format
```
TRA API Test Results
Generated: 2024-12-26T10:00:00Z
Server: http://localhost:8000
Cases Tested: 54820, 67890

Summary:
- Total: 45
- Passed: 42
- Failed: 3
- Success Rate: 93.3%

Detailed Results by Case:

54820:
  ✅ GET /client_profile/54820
    Status: 200
    Time: 340ms
    Response:
    {
        "case_id": "54820",
        "client_name": "John Doe",
        "filing_status": "Single",
        "income": 75000
    }

  ✅ GET /transcripts/wi/54820
    Status: 200
    Time: 450ms
    Response:
    {
        "transcripts": [...]
    }

Errors Summary:
❌ GET /client_profile/67890 (67890): Case not found
```

## Troubleshooting

### Common Issues

1. **CORS Errors**: Ensure your backend allows requests from `http://localhost:3000`
2. **Connection Refused**: Verify your backend server is running on the correct port
3. **404 Errors**: Check that the endpoint paths match your backend routes
4. **Authentication Errors**: Some endpoints may require valid credentials

### Development

To modify the tool for your specific needs:

1. **Add New Endpoints**: Update the `endpointConfig` object in `App.js`
2. **Custom Styling**: Modify `src/index.css`
3. **Additional Features**: Extend the React components as needed

## Dependencies

- **React**: UI framework
- **Axios**: HTTP client for API calls
- **Lucide React**: Icon library
- **React Scripts**: Development and build tools

## License

This tool is part of the TRA API backend project and follows the same licensing terms. 