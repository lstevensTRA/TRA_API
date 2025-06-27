import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Play, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Pause, 
  Download, 
  Copy, 
  Eye,
  EyeOff,
  Server,
  TestTube,
  FileText,
  Settings,
  Database
} from 'lucide-react';

const App = () => {
  const [serverUrl, setServerUrl] = useState('http://localhost:8000');
  const [caseIds, setCaseIds] = useState('54820');
  const [selectedEndpoints, setSelectedEndpoints] = useState({
    auth: true,
    health: true,
    clientProfile: true,
    transcripts: true,
    analysis: true,
    disposableIncome: true,
    incomeComparison: true,
    closingLetters: true,
    caseManagement: true,
    irsStandards: true,
    taxInvestigation: true
  });
  
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState([]);
  const [summary, setSummary] = useState({ total: 0, passed: 0, failed: 0 });
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [error, setError] = useState(null);

  // Load saved configuration from localStorage
  useEffect(() => {
    const savedServerUrl = localStorage.getItem('tra-api-server-url');
    const savedCaseIds = localStorage.getItem('tra-api-case-ids');
    const savedEndpoints = localStorage.getItem('tra-api-endpoints');
    
    if (savedServerUrl) setServerUrl(savedServerUrl);
    if (savedCaseIds) setCaseIds(savedCaseIds);
    if (savedEndpoints) {
      try {
        setSelectedEndpoints(JSON.parse(savedEndpoints));
      } catch (e) {
        console.error('Failed to parse saved endpoints:', e);
      }
    }
  }, []);

  // Save configuration to localStorage
  useEffect(() => {
    localStorage.setItem('tra-api-server-url', serverUrl);
    localStorage.setItem('tra-api-case-ids', caseIds);
    localStorage.setItem('tra-api-endpoints', JSON.stringify(selectedEndpoints));
  }, [serverUrl, caseIds, selectedEndpoints]);

  const endpointConfig = {
    auth: {
      name: 'Authentication',
      endpoints: [
        { path: '/auth/login', method: 'POST', name: 'Login' },
        { path: '/auth/status', method: 'GET', name: 'Status' }
      ]
    },
    health: {
      name: 'Health Check',
      endpoints: [
        { path: '/health/', method: 'GET', name: 'Health Check' }
      ]
    },
    clientProfile: {
      name: 'Client Profile',
      endpoints: [
        { path: '/client_profile/{case_id}', method: 'GET', name: 'Get Client Profile' }
      ]
    },
    transcripts: {
      name: 'Transcripts',
      endpoints: [
        { path: '/transcripts/wi/{case_id}', method: 'GET', name: 'WI Transcript Discovery' },
        { path: '/transcripts/at/{case_id}', method: 'GET', name: 'AT Transcript Discovery' },
        { path: '/transcripts/raw/wi/{case_id}', method: 'GET', name: 'WI Raw Data' },
        { path: '/transcripts/raw/at/{case_id}', method: 'GET', name: 'AT Raw Data' }
      ]
    },
    analysis: {
      name: 'Analysis',
      endpoints: [
        { path: '/analysis/wi/{case_id}', method: 'GET', name: 'WI Analysis' },
        { path: '/analysis/at/{case_id}', method: 'GET', name: 'AT Analysis' }
      ]
    },
    disposableIncome: {
      name: 'Disposable Income',
      endpoints: [
        { path: '/disposable-income/case/{case_id}', method: 'GET', name: 'Calculate Disposable Income' }
      ]
    },
    incomeComparison: {
      name: 'Income Comparison',
      endpoints: [
        { path: '/income-comparison/{case_id}', method: 'GET', name: 'Income Comparison' }
      ]
    },
    closingLetters: {
      name: 'Closing Letters',
      endpoints: [
        { path: '/closing-letters/{case_id}', method: 'GET', name: 'Generate Closing Letters' }
      ]
    },
    caseManagement: {
      name: 'Case Management',
      endpoints: [
        { path: '/case-management/caseactivities/{case_id}', method: 'GET', name: 'Get Case Activities' },
        { path: '/case-management/sms-logs/{case_id}', method: 'GET', name: 'Get SMS Logs' }
      ]
    },
    irsStandards: {
      name: 'IRS Standards',
      endpoints: [
        { path: '/irs-standards/case/{case_id}', method: 'GET', name: 'Get IRS Standards' }
      ]
    },
    taxInvestigation: {
      name: 'Tax Investigation',
      endpoints: [
        { path: '/tax-investigation/compare/{case_id}', method: 'GET', name: 'Compare Tax Investigation Data' }
      ]
    }
  };

  const safeRender = (data) => {
    if (data === null || data === undefined) {
      return 'null';
    }
    if (typeof data === 'string') {
      return data;
    }
    if (typeof data === 'object') {
      try {
        return JSON.stringify(data, null, 2);
      } catch (e) {
        return String(data);
      }
    }
    return String(data);
  };

  const testEndpoint = async (endpoint, caseId) => {
    const startTime = Date.now();
    const url = `${serverUrl}${endpoint.path.replace('{case_id}', caseId)}`;
    
    try {
      let response;
      if (endpoint.method === 'POST') {
        response = await axios.post(url, {});
      } else {
        response = await axios.get(url);
      }
      
      const endTime = Date.now();
      const responseTime = endTime - startTime;
      
      return {
        endpoint: `${endpoint.method} ${endpoint.path}`,
        caseId,
        status: response.status,
        responseTime: `${responseTime}ms`,
        success: response.status >= 200 && response.status < 300,
        response: response.data,
        error: null
      };
    } catch (error) {
      const endTime = Date.now();
      const responseTime = endTime - startTime;
      
      // Handle different types of error responses
      let errorMessage;
      if (error.response?.data) {
        if (typeof error.response.data === 'object') {
          errorMessage = JSON.stringify(error.response.data, null, 2);
        } else {
          errorMessage = String(error.response.data);
        }
      } else if (error.message) {
        errorMessage = error.message;
      } else {
        errorMessage = 'Unknown error occurred';
      }
      
      return {
        endpoint: `${endpoint.method} ${endpoint.path}`,
        caseId,
        status: error.response?.status || 0,
        responseTime: `${responseTime}ms`,
        success: false,
        response: null,
        error: errorMessage
      };
    }
  };

  const runTests = async () => {
    try {
      setIsRunning(true);
      setProgress(0);
      setResults([]);
      setError(null);
      setExpandedRows(new Set());
      
      const caseIdList = caseIds.split(',').map(id => id.trim()).filter(id => id);
      const allEndpoints = [];
      
      // Build list of all endpoints to test
      Object.entries(selectedEndpoints).forEach(([category, isSelected]) => {
        if (isSelected && endpointConfig[category]) {
          endpointConfig[category].endpoints.forEach(endpoint => {
            caseIdList.forEach(caseId => {
              allEndpoints.push({ endpoint, caseId });
            });
          });
        }
      });
      
      setSummary({ total: allEndpoints.length, passed: 0, failed: 0 });
      
      let passed = 0;
      let failed = 0;
      const newResults = [];
      
      for (let i = 0; i < allEndpoints.length; i++) {
        const { endpoint, caseId } = allEndpoints[i];
        const result = await testEndpoint(endpoint, caseId);
        
        newResults.push(result);
        
        if (result.success) {
          passed++;
        } else {
          failed++;
        }
        
        setResults([...newResults]);
        setSummary({ total: allEndpoints.length, passed, failed });
        setProgress(((i + 1) / allEndpoints.length) * 100);
        
        // Small delay to show progress
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    } catch (err) {
      setError(`Test execution failed: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const toggleRowExpansion = (index) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedRows(newExpanded);
  };

  const exportResults = (format) => {
    const exportData = {
      timestamp: new Date().toISOString(),
      server: serverUrl,
      casesTested: caseIds.split(',').map(id => id.trim()).filter(id => id),
      summary,
      results: results.reduce((acc, result) => {
        if (!acc[`case_${result.caseId}`]) {
          acc[`case_${result.caseId}`] = {};
        }
        acc[`case_${result.caseId}`][result.endpoint] = {
          status: result.status,
          time: result.responseTime,
          success: result.success,
          response: result.response,
          error: result.error,
          endpoint: result.endpoint,
          caseId: result.caseId
        };
        return acc;
      }, {}),
      errors: results.filter(r => !r.success).map(r => ({
        endpoint: r.endpoint,
        error: r.error,
        caseId: r.caseId,
        status: r.status,
        responseTime: r.responseTime
      }))
    };

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tra-api-test-results-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === 'txt') {
      const text = `TRA API Test Results
Generated: ${new Date().toISOString()}
Server: ${serverUrl}
Cases Tested: ${caseIds}

Summary:
- Total: ${summary.total}
- Passed: ${summary.passed}
- Failed: ${summary.failed}
- Success Rate: ${((summary.passed / summary.total) * 100).toFixed(1)}%

Detailed Results by Case:

${Object.entries(exportData.results).map(([caseKey, caseResults]) => {
  const caseId = caseKey.replace('case_', '');
  return `${caseId}:
${Object.entries(caseResults).map(([endpoint, data]) => {
  const status = data.success ? '✅' : '❌';
  return `  ${status} ${endpoint}
    Status: ${data.status}
    Time: ${data.time}
    ${data.success ? 'Response:' : 'Error:'}
    ${data.success ? 
      (typeof data.response === 'object' ? JSON.stringify(data.response, null, 4) : data.response) :
      (typeof data.error === 'object' ? JSON.stringify(data.error, null, 4) : data.error)
    }`;
}).join('\n\n')}`;
}).join('\n\n')}

Errors Summary:
${results.filter(r => !r.success).map(r => `❌ ${r.endpoint} (${r.caseId}): ${r.error}`).join('\n')}`;

      const blob = new Blob([text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tra-api-test-results-${new Date().toISOString().split('T')[0]}.txt`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const copyToClipboard = () => {
    const text = `TRA API Test Results
Generated: ${new Date().toISOString()}
Server: ${serverUrl}
Cases Tested: ${caseIds}

Summary: ${summary.passed}/${summary.total} endpoints passed (${((summary.passed / summary.total) * 100).toFixed(1)}% success rate)

Detailed Results by Case:

${Object.entries(results.reduce((acc, result) => {
  if (!acc[`case_${result.caseId}`]) {
    acc[`case_${result.caseId}`] = {};
  }
  acc[`case_${result.caseId}`][result.endpoint] = result;
  return acc;
}, {})).map(([caseKey, caseResults]) => {
  const caseId = caseKey.replace('case_', '');
  return `${caseId}:
${Object.entries(caseResults).map(([endpoint, data]) => {
  const status = data.success ? '✅' : '❌';
  return `  ${status} ${endpoint}
    Status: ${data.status}
    Time: ${data.time}
    ${data.success ? 'Response:' : 'Error:'}
    ${data.success ? 
      (typeof data.response === 'object' ? JSON.stringify(data.response, null, 4) : data.response) :
      (typeof data.error === 'object' ? JSON.stringify(data.error, null, 4) : data.error)
    }`;
}).join('\n\n')}`;
}).join('\n\n')}

Errors Summary:
${results.filter(r => !r.success).map(r => `❌ ${r.endpoint} (${r.caseId}): ${r.error}`).join('\n')}`;

    navigator.clipboard.writeText(text);
  };

  const getStatusIcon = (status) => {
    if (status === 'success') return <CheckCircle className="status-icon" style={{ color: '#10b981' }} />;
    if (status === 'error') return <XCircle className="status-icon" style={{ color: '#ef4444' }} />;
    if (status === 'pending') return <Clock className="status-icon" style={{ color: '#f59e0b' }} />;
    return <Pause className="status-icon" style={{ color: '#6b7280' }} />;
  };

  const getStatusText = (status) => {
    if (status === 'success') return 'Success';
    if (status === 'error') return 'Error';
    if (status === 'pending') return 'Pending';
    return 'Paused';
  };

  const safeDisplay = (value) => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  const exportResponseModels = () => {
    const responseModels = results.reduce((acc, result) => {
      if (!acc[`case_${result.caseId}`]) {
        acc[`case_${result.caseId}`] = {};
      }
      if (result.success && result.response) {
        acc[`case_${result.caseId}`][result.endpoint] = {
          response: result.response,
          status: result.status,
          responseTime: result.responseTime
        };
      }
      return acc;
    }, {});

    const exportData = {
      timestamp: new Date().toISOString(),
      server: serverUrl,
      casesTested: caseIds.split(',').map(id => id.trim()).filter(id => id),
      responseModels
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tra-api-response-models-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container">
      <div className="header">
        <h1>🚀 TRA API Backend Tester</h1>
      </div>

      <div className="config-panel">
        <div className="config-row">
          <label>Server:</label>
          <select 
            value={serverUrl} 
            onChange={(e) => setServerUrl(e.target.value)}
          >
            <option value="http://localhost:8000">localhost:8000</option>
            <option value="http://localhost:3000">localhost:3000</option>
            <option value="https://api.tra.com">Production</option>
          </select>
        </div>

        <div className="config-row">
          <label>Cases:</label>
          <input
            type="text"
            value={caseIds}
            onChange={(e) => setCaseIds(e.target.value)}
            placeholder="54820, 67890, 99999"
          />
        </div>

        <div className="config-row">
          <label>Test:</label>
          <div className="checkbox-group">
            {Object.entries(endpointConfig).map(([key, config]) => (
              <div key={key} className="checkbox-item">
                <input
                  type="checkbox"
                  id={key}
                  checked={selectedEndpoints[key]}
                  onChange={(e) => setSelectedEndpoints(prev => ({
                    ...prev,
                    [key]: e.target.checked
                  }))}
                />
                <label htmlFor={key}>{config.name}</label>
              </div>
            ))}
          </div>
        </div>

        <button 
          className="btn btn-primary" 
          onClick={runTests}
          disabled={isRunning}
        >
          {isRunning ? <div className="loading"></div> : <Play size={16} />}
          {isRunning ? 'Running Tests...' : '🚀 Run Tests'}
        </button>
      </div>

      {isRunning && (
        <div className="progress-section">
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="progress-text">
            <span>Progress: {Math.round(progress)}%</span>
            <span>({summary.passed + summary.failed}/{summary.total})</span>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-section">
          <h3>Test Results</h3>
          
          <div className="status-grid">
            {Object.entries(endpointConfig).map(([key, config]) => {
              if (!selectedEndpoints[key]) return null;
              
              const categoryResults = results.filter(r => 
                config.endpoints.some(e => r.endpoint.includes(e.path.split('/')[1]))
              );
              
              const passed = categoryResults.filter(r => r.success).length;
              const total = categoryResults.length;
              const status = total === 0 ? 'paused' : 
                           passed === total ? 'success' : 
                           passed === 0 ? 'error' : 'pending';
              
              return (
                <div key={key} className={`status-card ${status}`}>
                  <div className="status-header">
                    {getStatusIcon(status)}
                    {config.name}
                  </div>
                  <div>{passed}/{total} passed</div>
                </div>
              );
            })}
          </div>

          <table className="results-table">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th>Status</th>
                <th>Response Time</th>
                <th>Case ID</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result, index) => (
                <React.Fragment key={index}>
                  <tr 
                    className="expandable-row"
                    onClick={() => toggleRowExpansion(index)}
                  >
                    <td>{result.endpoint}</td>
                    <td>
                      <span className={`status-badge ${result.success ? 'success' : 'error'}`}>
                        {safeDisplay(result.status)}
                      </span>
                    </td>
                    <td>{result.responseTime}</td>
                    <td>{result.caseId}</td>
                    <td>
                      {expandedRows.has(index) ? <EyeOff size={16} /> : <Eye size={16} />}
                    </td>
                  </tr>
                  {expandedRows.has(index) && (
                    <tr>
                      <td colSpan="5">
                        <div className="expandable-content">
                          {result.success ? 
                            safeRender(result.response) :
                            safeRender(result.error)
                          }
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>

          <div className="actions">
            <button className="btn btn-secondary" onClick={() => exportResults('json')}>
              <Download size={16} />
              Save JSON
            </button>
            <button className="btn btn-secondary" onClick={() => exportResults('txt')}>
              <FileText size={16} />
              Save TXT
            </button>
            <button className="btn btn-secondary" onClick={copyToClipboard}>
              <Copy size={16} />
              Copy Results
            </button>
            <button className="btn btn-secondary" onClick={exportResponseModels}>
              <Database size={16} />
              Save Response Models
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="error-boundary">
          <h4>Error</h4>
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};

export default App; 