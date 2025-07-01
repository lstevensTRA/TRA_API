import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Brain, 
  TrendingUp, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  Lightbulb,
  BarChart3,
  Settings,
  RefreshCw
} from 'lucide-react';

const PatternLearningFeedback = ({ serverUrl, caseId }) => {
  const [learningStats, setLearningStats] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [extractions, setExtractions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [feedbackForm, setFeedbackForm] = useState({
    extractionId: '',
    isCorrect: true,
    correctValue: '',
    comments: ''
  });

  useEffect(() => {
    if (caseId) {
      loadLearningData();
    }
  }, [caseId, serverUrl]);

  const loadLearningData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Load pattern learning statistics
      const statsResponse = await axios.get(`${serverUrl}/pattern-learning/stats?pattern_type=WI`);
      setLearningStats(statsResponse.data.data);
      
      // Load pattern suggestions
      const suggestionsResponse = await axios.get(`${serverUrl}/pattern-learning/suggestions`);
      setSuggestions(suggestionsResponse.data.data.suggestions || []);
      
      // Load extraction results for this case
      const extractionsResponse = await axios.get(`${serverUrl}/pattern-learning/extractions?case_id=${caseId}`);
      setExtractions(extractionsResponse.data.data.extractions || []);
      
    } catch (err) {
      console.error('Error loading learning data:', err);
      setError('Failed to load pattern learning data');
    } finally {
      setLoading(false);
    }
  };

  const submitFeedback = async () => {
    if (!feedbackForm.extractionId) {
      setError('Please select an extraction to provide feedback for');
      return;
    }

    try {
      await axios.post(`${serverUrl}/pattern-learning/feedback`, {
        extraction_id: feedbackForm.extractionId,
        is_correct: feedbackForm.isCorrect,
        correct_value: feedbackForm.correctValue || null,
        comments: feedbackForm.comments || null
      });

      // Reset form and reload data
      setFeedbackForm({
        extractionId: '',
        isCorrect: true,
        correctValue: '',
        comments: ''
      });
      
      await loadLearningData();
      
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError('Failed to submit feedback');
    }
  };

  const implementSuggestion = async (suggestionId) => {
    try {
      await axios.post(`${serverUrl}/pattern-learning/suggestions/${suggestionId}/implement`);
      await loadLearningData();
    } catch (err) {
      console.error('Error implementing suggestion:', err);
      setError('Failed to implement suggestion');
    }
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceIcon = (confidence) => {
    if (confidence >= 0.8) return <CheckCircle className="w-4 h-4 text-green-600" />;
    if (confidence >= 0.6) return <AlertCircle className="w-4 h-4 text-yellow-600" />;
    return <XCircle className="w-4 h-4 text-red-600" />;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-center">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span>Loading pattern learning data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <Brain className="w-6 h-6 text-blue-600 mr-2" />
          <h2 className="text-xl font-semibold">Pattern Learning System</h2>
        </div>
        
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
            <div className="flex">
              <AlertCircle className="w-5 h-5 text-red-400 mr-2" />
              <span className="text-red-800">{error}</span>
            </div>
          </div>
        )}

        {/* Statistics Overview */}
        {learningStats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="flex items-center">
                <BarChart3 className="w-5 h-5 text-blue-600 mr-2" />
                <div>
                  <p className="text-sm text-gray-600">Total Patterns</p>
                  <p className="text-lg font-semibold">{learningStats.total_patterns}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-green-50 rounded-lg p-4">
              <div className="flex items-center">
                <TrendingUp className="w-5 h-5 text-green-600 mr-2" />
                <div>
                  <p className="text-sm text-gray-600">Success Rate</p>
                  <p className="text-lg font-semibold">{(learningStats.overall_success_rate * 100).toFixed(1)}%</p>
                </div>
              </div>
            </div>
            
            <div className="bg-yellow-50 rounded-lg p-4">
              <div className="flex items-center">
                <Lightbulb className="w-5 h-5 text-yellow-600 mr-2" />
                <div>
                  <p className="text-sm text-gray-600">Suggestions</p>
                  <p className="text-lg font-semibold">{learningStats.suggestions_generated}</p>
                </div>
              </div>
            </div>
            
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="flex items-center">
                <Settings className="w-5 h-5 text-purple-600 mr-2" />
                <div>
                  <p className="text-sm text-gray-600">Avg Confidence</p>
                  <p className="text-lg font-semibold">{(learningStats.average_confidence * 100).toFixed(1)}%</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Feedback Form */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Provide Feedback</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Extraction
            </label>
            <select
              value={feedbackForm.extractionId}
              onChange={(e) => setFeedbackForm({...feedbackForm, extractionId: e.target.value})}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Choose an extraction...</option>
              {extractions.map((extraction) => (
                <option key={extraction.extraction_id} value={extraction.extraction_id}>
                  {extraction.field_name}: {extraction.extracted_value} (Confidence: {(extraction.confidence_score * 100).toFixed(1)}%)
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Was this extraction correct?
            </label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  checked={feedbackForm.isCorrect}
                  onChange={() => setFeedbackForm({...feedbackForm, isCorrect: true})}
                  className="mr-2"
                />
                <CheckCircle className="w-4 h-4 text-green-600 mr-1" />
                Correct
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  checked={!feedbackForm.isCorrect}
                  onChange={() => setFeedbackForm({...feedbackForm, isCorrect: false})}
                  className="mr-2"
                />
                <XCircle className="w-4 h-4 text-red-600 mr-1" />
                Incorrect
              </label>
            </div>
          </div>
          
          {!feedbackForm.isCorrect && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Correct Value
              </label>
              <input
                type="text"
                value={feedbackForm.correctValue}
                onChange={(e) => setFeedbackForm({...feedbackForm, correctValue: e.target.value})}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter the correct value..."
              />
            </div>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Comments (Optional)
            </label>
            <textarea
              value={feedbackForm.comments}
              onChange={(e) => setFeedbackForm({...feedbackForm, comments: e.target.value})}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="3"
              placeholder="Additional comments..."
            />
          </div>
          
          <button
            onClick={submitFeedback}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Submit Feedback
          </button>
        </div>
      </div>

      {/* Pattern Suggestions */}
      {suggestions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Pattern Suggestions</h3>
          
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <div key={suggestion.suggestion_id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center">
                    <Lightbulb className="w-5 h-5 text-yellow-600 mr-2" />
                    <span className="font-medium">Pattern Suggestion</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`text-sm font-medium ${getConfidenceColor(suggestion.confidence_score)}`}>
                      {(suggestion.confidence_score * 100).toFixed(1)}% confidence
                    </span>
                    {!suggestion.is_implemented && (
                      <button
                        onClick={() => implementSuggestion(suggestion.suggestion_id)}
                        className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                      >
                        Implement
                      </button>
                    )}
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded p-3 mb-2">
                  <p className="text-sm font-mono text-gray-700">{suggestion.suggested_regex}</p>
                </div>
                
                <p className="text-sm text-gray-600">{suggestion.reasoning}</p>
                
                {suggestion.is_implemented && (
                  <div className="mt-2 flex items-center text-green-600">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    <span className="text-sm">Implemented</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Extractions */}
      {extractions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Extractions</h3>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Field
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Confidence
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {extractions.slice(0, 10).map((extraction) => (
                  <tr key={extraction.extraction_id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {extraction.field_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {extraction.extracted_value || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <div className="flex items-center">
                        {getConfidenceIcon(extraction.confidence_score)}
                        <span className="ml-1">{(extraction.confidence_score * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {extraction.success ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Success
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          Failed
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatternLearningFeedback; 