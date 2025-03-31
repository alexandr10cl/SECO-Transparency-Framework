import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ScatterChart, Scatter, ZAxis, Cell, Treemap, LabelList } from 'recharts';
import { Info, FileText, Users, Settings, CheckCircle, AlertTriangle, XCircle, Search, Globe, BookOpen, Code, Shield, Zap, Clock, Activity, Target, Eye, Lightbulb } from 'lucide-react';
import { PieChart, Pie, ReferenceLine } from 'recharts';
import { fetchEvaluationData, fetchGuidelineData, testDatabaseConnection } from './api/evaluation';
import HeatmapVisualization from './components/HeatmapVisualization';
// Import the troubleshooter functions
import { runDiagnostics } from './api/databaseTroubleshooter';

const SECODashboard = () => {
  // Add these state declarations at the top with the other useState declarations
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedGuideline, setSelectedGuideline] = useState(null);
  const [selectedGuidelineData, setSelectedGuidelineData] = useState(null);
  const [timeframe, setTimeframe] = useState('monthly');
  const [selectedFactor, setSelectedFactor] = useState(null);
  const [showGuidelinesForDimension, setShowGuidelinesForDimension] = useState(null);
  const [selectedDimension, setSelectedDimension] = useState(null);
  const [isLoadingEvaluation, setIsLoadingEvaluation] = useState(true);
  const [evaluationData, setEvaluationData] = useState({
    taskCompletionTimes: [],
    userResponses: [],
    interactionTypes: [],
    heatmapData: []
  });
  
  // Track expanded dimensions for the dropdowns
  const [expandedDimensions, setExpandedDimensions] = useState({
    technical: false,
    social: false,
    economic: false,
    environmental: false
  });
  
  // Software Ecosystem Dimensions (distinct from Sustainability Dimensions)
  const secoSystemDimensions = [
    { id: 'technical', name: 'Technical', color: 'blue', score: 70 },
    { id: 'social', name: 'Social', color: 'green', score: 80 },
    { id: 'business', name: 'Business', color: 'purple', score: 65 }
  ];

  // Sustainability Dimensions
  const sustainabilityDimensions = [
    { id: 'technical', name: 'Technical', color: 'blue', score: 70 },
    { id: 'social', name: 'Social', color: 'green', score: 80 },
    { id: 'environmental', name: 'Environmental', color: 'teal', score: 30 },
    { id: 'economic', name: 'Economic', color: 'yellow', score: 50 }
  ];
  
  // Conditioning factors data
  const conditioningFactors = [
    { id: 'CF1', name: 'Communication Channels', status: 'developing', description: 'The existence of communication channels between actors and keystone' },
    { id: 'CF2', name: 'Accessible Information', status: 'established', description: 'Information about platform made available in an accessible way' },
    { id: 'CF3', name: 'Understanding', status: 'established', description: 'The actors\' understanding of SECO information' },
    { id: 'CF4', name: 'Information Quality', status: 'established', description: 'The quality of platform information provided by a keystone' },
    { id: 'CF5', name: 'Interface Usability', status: 'established', description: 'The usability of interfaces with platform documentation' },
    { id: 'CF6', name: 'Auditability', status: 'developing', description: 'The auditability of platform processes and information' },
    { id: 'CF7', name: 'Evolution Visualization', status: 'initial', description: 'Visualization of the evolution of projects in SECO' },
    { id: 'CF8', name: 'Information Reliability', status: 'advanced', description: 'Reliability of information provided by a keystone' }
  ];
  
  // Developer experience factors data
  const devExpFactors = [
    { group: 'Common Technological Platform', id: 'F1', name: 'Technical resources', status: 'established', dimension: 'Technical' },
    { group: 'Common Technological Platform', id: 'F5', name: 'Platform transparency', status: 'established', dimension: 'Technical' },
    { group: 'Common Technological Platform', id: 'F8', name: 'Documentation quality', status: 'established', dimension: 'Technical' },
    { group: 'Common Technological Platform', id: 'F7', name: 'Communication channels', status: 'developing', dimension: 'Social' },
    { group: 'Projects and Applications', id: 'F9', name: 'Clients/users for applications', status: 'developing', dimension: 'Social' },
    { group: 'Projects and Applications', id: 'F13', name: 'Ease of learning', status: 'developing', dimension: 'Technical' },
    { group: 'Community Interaction', id: 'F17', name: 'Good relationship with community', status: 'established', dimension: 'Social' },
    { group: 'Community Interaction', id: 'F19', name: 'Good developer relations program', status: 'developing', dimension: 'Organizational' },
    { group: 'Expectations and Value', id: 'F24', name: 'Developer skills improvement', status: 'established', dimension: 'Organizational' },
    { group: 'Expectations and Value', id: 'F27', name: 'Engagement and rewards', status: 'developing', dimension: 'Economic' }
  ];
  
  // Toggle dimension expansion for dropdown
  const toggleDimension = (dimensionId) => {
    setExpandedDimensions(prev => ({
      ...prev,
      [dimensionId]: !prev[dimensionId]
    }));
  };
  
  // Processes data
  const processesData = [
    { id: 'P1', name: 'Access to documentation, source code, and tools', status: 'completed', linkedGuidelines: ['G1', 'G2', 'G3'] },
    { id: 'P2', name: 'Access to information about code in repositories', status: 'partial', linkedGuidelines: ['G1', 'G2', 'G3'] },
    { id: 'P3', name: 'Communication channels between actors and keystone', status: 'partial', linkedGuidelines: ['G3'] },
    { id: 'P4', name: 'Processes related to SECO governance', status: 'partial', linkedGuidelines: [] },
    { id: 'P5', name: 'Access to information about requirements flow', status: 'not-started', linkedGuidelines: ['G1', 'G2', 'G3'] },
    { id: 'P6', name: 'Processes related to data collection, processing, and sharing', status: 'not-started', linkedGuidelines: [] },
    { id: 'P7', name: 'Access to information about SECO architecture', status: 'not-started', linkedGuidelines: ['G1', 'G2', 'G3'] }
  ];
  
  // Guidelines data - Modified to include sustainability and SECO dimensions explicitly and action items
  const guidelinesData = [
    { 
      id: 'G1', 
      name: 'Access Capability', 
      description: 'Software ecosystem portals must be accessible, stable, and functional, with consistent and uninterrupted access.',
      secoDimension: 'technical',
      sustainabilityDimension: 'technical',
      conditioningFactors: ['CF2'],
      devExpFactors: ['F1', 'F5', 'F8'],
      processes: ['P1', 'P2', 'P5', 'P7'],
      successCriteria: [
        { id: '3.1.1', name: 'Accessible by main browsers', status: 'completed', notes: 'Verified through cross-browser testing' },
        { id: '3.1.2', name: 'Online availability', status: 'completed', notes: 'Uptime monitoring shows 99.5%+ availability' },
        { id: '3.1.3', name: 'Availability for multiple devices', status: 'partial', notes: 'Mobile responsiveness needs improvement' }
      ],
      actionItems: [7]
    },
    { 
      id: 'G2', 
      name: 'Availability of Tools for Accessibility', 
      description: 'Ecosystem interfaces must be compatible with tools that help people with disabilities, making information accessible to the widest possible audience.',
      secoDimension: 'technical',
      sustainabilityDimension: 'social',
      conditioningFactors: ['CF2', 'CF5'],
      devExpFactors: ['F5', 'F6'],
      processes: ['P1', 'P2', 'P5', 'P7'],
      successCriteria: [
        { id: '3.2.1', name: 'Helps with visual impairments', status: 'partial', notes: 'Screen reader compatibility is limited' },
        { id: '3.2.2', name: 'Helps with motor limitations', status: 'not-started', notes: 'No keyboard navigation implemented' },
        { id: '3.2.3', name: 'Helps with hearing impairments', status: 'partial', notes: 'Some videos lack captions' }
      ],
      actionItems: [1]
    },
    { 
      id: 'G3', 
      name: 'Availability in multiple languages', 
      description: 'Providing information in different languages offers foreign users a more enjoyable experience and makes communication more effective.',
      secoDimension: 'social',
      sustainabilityDimension: 'social',
      conditioningFactors: ['CF2', 'CF3', 'CF4'],
      devExpFactors: ['F5', 'F6', 'F17'],
      processes: ['P1', 'P2', 'P3', 'P5', 'P7'],
      successCriteria: [
        { id: '3.3.1', name: 'Multiple language support', status: 'partial', notes: 'Only English and Spanish currently supported' },
        { id: '3.3.2', name: 'Quality of translations', status: 'partial', notes: 'Some translations need review' },
        { id: '3.3.3', name: 'Language switching ease', status: 'partial', notes: 'UI for switching languages could be improved' }
      ],
      actionItems: [2]
    },
    { 
      id: 'G4', 
      name: 'Fast research for information', 
      description: 'The information should be organized so that users can access it easily and quickly. Effective search tools must be provided to enhance the speed of finding relevant information.',
      secoDimension: 'technical',
      sustainabilityDimension: 'technical',
      conditioningFactors: ['CF3', 'CF4', 'CF5'],
      devExpFactors: ['F5', 'F6', 'F13'],
      processes: ['P1', 'P2', 'P5', 'P7'],
      successCriteria: [
        { id: '1.3.1', name: 'Effective search functionality', status: 'partial', notes: 'Search results relevance needs improvement' },
        { id: '1.3.2', name: 'Information organization', status: 'partial', notes: 'Some categories are confusing' },
        { id: '1.3.3', name: 'Quick access to common resources', status: 'partial', notes: 'Frequently used resources need better visibility' }
      ],
      actionItems: [3]
    },
    { 
      id: 'G5', 
      name: 'Content quality', 
      description: 'A software ecosystem portal must keep its content up-to-date, clear, and concise. The language should be easy to understand and convey information without confusion or ambiguity.',
      secoDimension: 'business',
      sustainabilityDimension: 'technical',
      conditioningFactors: ['CF3', 'CF4', 'CF8'],
      devExpFactors: ['F5', 'F6'],
      processes: ['P1', 'P2', 'P5', 'P7'],
      successCriteria: [
        { id: '2.1.1', name: 'Up-to-date content', status: 'partial', notes: 'Some documentation is outdated' },
        { id: '2.1.2', name: 'Clear and concise language', status: 'completed', notes: 'Content is generally clear and readable' },
        { id: '2.1.3', name: 'Comprehensive information', status: 'partial', notes: 'Some advanced topics lack detail' }
      ],
      actionItems: [5, 6]
    },
    { 
      id: 'G6', 
      name: 'Avoid strict methods for code organization', 
      description: 'A software ecosystem portal, when providing implementation examples, should avoid imposing specific and strict methods for code organization, allowing developers flexibility.',
      secoDimension: 'technical',
      sustainabilityDimension: 'technical',
      conditioningFactors: ['CF3', 'CF4'],
      devExpFactors: ['F1', 'F13'],
      processes: ['P1', 'P2', 'P5', 'P7'],
      successCriteria: [
        { id: '2.2.1', name: 'Flexible implementation examples', status: 'not-started', notes: 'Examples are too prescriptive' },
        { id: '2.2.2', name: 'Various approaches demonstrated', status: 'not-started', notes: 'Only one approach is usually shown' },
        { id: '2.2.3', name: 'Adaptable code patterns', status: 'partial', notes: 'Some flexibility in code patterns exists' }
      ],
      actionItems: [4]
    },
    { 
      id: 'G7', 
      name: 'Transparent pricing information', 
      description: 'Clear pricing details should be available to all ecosystem participants with no hidden costs.',
      secoDimension: 'business',
      sustainabilityDimension: 'economic',
      conditioningFactors: ['CF2', 'CF4', 'CF8'],
      devExpFactors: ['F27'],
      processes: ['P6'],
      successCriteria: [
        { id: '4.1.1', name: 'Clear pricing structure', status: 'partial', notes: 'Basic pricing is clear but some add-ons are not' },
        { id: '4.1.2', name: 'Cost calculator availability', status: 'not-started', notes: 'No calculator available for custom configurations' },
        { id: '4.1.3', name: 'Transparent fee structure', status: 'completed', notes: 'All fees are clearly documented' }
      ],
      actionItems: [6]
    },
    { 
      id: 'G8', 
      name: 'Environmental impact reporting', 
      description: 'Ecosystem should provide transparency about environmental impacts of services and operations.',
      secoDimension: 'business',
      sustainabilityDimension: 'environmental',
      conditioningFactors: ['CF4', 'CF8'],
      devExpFactors: [],
      processes: ['P6'],
      successCriteria: [
        { id: '5.1.1', name: 'Carbon footprint reporting', status: 'not-started', notes: 'No carbon metrics available' },
        { id: '5.1.2', name: 'Energy efficiency metrics', status: 'partial', notes: 'Limited data on energy usage' },
        { id: '5.1.3', name: 'Sustainability roadmap', status: 'not-started', notes: 'No published environmental goals' }
      ],
      actionItems: []
    }
  ];

  // Action items data - linked to KPIs and guidelines with both SECO and sustainability dimensions
  const actionItems = [
    { id: 1, title: 'Improve accessibility tools support', guideline: 'G2', kpi: 'KPI2', deadline: 'Q2 2025', status: 'planning', impact: 'Increase compliance of criterion 3.2.2 from not started to partial', secoDimension: 'technical', sustainabilityDimension: 'social' },
    { id: 2, title: 'Add multilingual support for API docs', guideline: 'G3', kpi: 'KPI2', deadline: 'Q1 2025', status: 'in-progress', impact: 'Support 5 additional languages, raising G3 compliance to completed', dimension: 'Technical' },
    { id: 3, title: 'Implement AI-powered search', guideline: 'G4', kpi: 'KPI2', deadline: 'Q3 2025', status: 'planning', impact: 'Reduce average search time from 8m to 3m', dimension: 'Technical' },
    { id: 4, title: 'Restructure implementation examples', guideline: 'G6', kpi: 'KPI5', deadline: 'Q1 2025', status: 'in-progress', impact: 'Provide multiple pattern examples for each API', dimension: 'Technical' },
    { id: 5, title: 'Enhance documentation audit tools', guideline: 'G5', kpi: 'KPI5', deadline: 'Q2 2025', status: 'planning', impact: 'Improve content freshness tracking and updates', dimension: 'Technical' },
    { id: 6, title: 'Create pricing calculator', guideline: 'G5', kpi: 'KPI3', deadline: 'Q2 2025', status: 'planning', impact: 'Increase economic transparency from partial to completed', dimension: 'Economic' },
    { id: 7, title: 'Implement community response program', guideline: 'G1', kpi: 'KPI1', deadline: 'Q1 2025', status: 'in-progress', impact: 'Reduce response time from 2 days to 1 day', dimension: 'Social' },
    { id: 8, title: 'Create governance documentation system', guideline: 'G1', kpi: 'KPI4', deadline: 'Q3 2025', status: 'planning', impact: 'Improve governance transparency from partial to completed', dimension: 'Organizational' }
  ];

  // Helper functions
  const getStatusIcon = (status) => {
    if (status === 'completed') return <CheckCircle className="text-green-500" size={18} />;
    if (status === 'partial') return <AlertTriangle className="text-yellow-500" size={18} />;
    return <XCircle className="text-gray-400" size={18} />;
  };
  
  const getStatusColor = (status) => {
    if (status === 'completed') return 'bg-green-500';
    if (status === 'partial') return 'bg-yellow-500';
    return 'bg-gray-300';
  };
  
  const getStatusText = (status) => {
    if (status === 'completed') return 'Complete';
    if (status === 'partial') return 'Partial';
    return 'Not started';
  };
  
  const getFactorStatusColor = (status) => {
    if (status === 'advanced') return 'bg-green-600';
    if (status === 'established') return 'bg-green-400';
    if (status === 'developing') return 'bg-yellow-400';
    return 'bg-red-400';
  };
  
  const getFactorStatusText = (status) => {
    if (status === 'advanced') return 'Advanced';
    if (status === 'established') return 'Established';
    if (status === 'developing') return 'Developing';
    return 'Initial';
  };

  // Calculate the guidelines status for a dimension
  const getGuidelineStatusByDimension = (dimensionId, isDimension, dimensionType) => {
    const filteredGuidelines = guidelinesData.filter(g => 
      isDimension ? 
        (dimensionType === 'seco' ? g.secoDimension === dimensionId : g.sustainabilityDimension === dimensionId) : 
        true
    );
    
    let completed = 0;
    let partial = 0;
    let notStarted = 0;
    
    filteredGuidelines.forEach(g => {
      const criteriaCount = g.successCriteria.length;
      const completedCount = g.successCriteria.filter(c => c.status === 'completed').length;
      const partialCount = g.successCriteria.filter(c => c.status === 'partial').length;
      
      if (completedCount === criteriaCount) {
        completed++;
      } else if (completedCount + partialCount === 0) {
        notStarted++;
      } else {
        partial++;
      }
    });
    
    return {
      completed,
      partial,
      notStarted,
      total: filteredGuidelines.length
    };
  };

  // Filter guidelines based on selected factor or dimension
  const getFilteredGuidelines = () => {
    if (selectedFactor) {
      return guidelinesData.filter(g => g.conditioningFactors.includes(selectedFactor));
    }
    return guidelinesData;
  };

  // Calculate guideline status based on criteria
  const getGuidelineStatus = (guideline) => {
    const criteriaCount = guideline.successCriteria.length;
    const completedCount = guideline.successCriteria.filter(c => c.status === 'completed').length;
    const partialCount = guideline.successCriteria.filter(c => c.status === 'partial').length;
    
    if (completedCount === criteriaCount) return 'completed';
    if (completedCount + partialCount === 0) return 'not-started';
    return 'partial';
  };
  
  // Get action items by dimension
  const getActionItemsByDimension = (dimensionId, isDimension, dimensionType) => {
    return actionItems.filter(item => 
      isDimension ? 
        (dimensionType === 'seco' ? item.secoDimension === dimensionId : item.sustainabilityDimension === dimensionId) : 
        true
    );
  };
  
  // Get color for dimension
  const getDimensionColor = (dimension, type) => {
    const dimensions = type === 'seco' ? secoSystemDimensions : sustainabilityDimensions;
    const found = dimensions.find(d => d.id === dimension);
    return found ? found.color : 'gray';
  };

  // Add kpiData constant
  const kpiData = [
    {
      id: 'KPI1',
      name: 'Response Time',
      hotspots: [
        { area: 'Documentation Updates', severity: 'high', time: 48 },
        { area: 'Support Tickets', severity: 'high', time: 72 }
      ]
    },
    // Add more KPI data as needed
  ];

  // Update the useEffect for loading evaluation data
  useEffect(() => {
    const loadEvaluationData = async () => {
      try {
        setIsLoadingEvaluation(true);
        // Fetch real data from the API
        const data = await fetchEvaluationData();
        setEvaluationData(data);
        setIsLoadingEvaluation(false);
      } catch (error) {
        console.error('Error loading evaluation data:', error);
        setIsLoadingEvaluation(false);
      }
    };

    loadEvaluationData();
  }, []);

  // Add useEffect to load guideline-specific data when a guideline is selected
  useEffect(() => {
    const loadGuidelineData = async () => {
      if (!selectedGuideline) {
        setSelectedGuidelineData(null);
        return;
      }

      try {
        setIsLoadingEvaluation(true);
        const data = await fetchGuidelineData(selectedGuideline);
        setSelectedGuidelineData(data);
      } catch (error) {
        console.error(`Error loading guideline data:`, error);
      } finally {
        setIsLoadingEvaluation(false);
      }
    };

    loadGuidelineData();
  }, [selectedGuideline]);

  // Update the guideline selection handler
  const handleGuidelineSelect = async (guidelineId) => {
    setSelectedGuideline(guidelineId);
  };

  // Update the guideline details section to use selectedGuidelineData
  const renderGuidelineDetails = () => {
    if (!selectedGuideline || !selectedGuidelineData) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-400 py-10">
          <FileText size={48} />
          <p className="mt-2">Select a guideline to view details</p>
          {(selectedFactor || selectedDimension) && (
            <p className="mt-1 text-sm text-blue-500">
              {selectedFactor ? `Showing guidelines related to ${selectedFactor}` : `Showing ${selectedDimension} guidelines`}
            </p>
          )}
        </div>
      );
    }

    const guideline = guidelinesData.find(g => g.id === selectedGuideline);
    if (!guideline) return null;

    return (
      <div>
        {/* Existing guideline details rendering code */}
        {/* Add new sections for evaluation data */}
        {selectedGuidelineData.task_performance && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-500 mb-2">Task Performance</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={selectedGuidelineData.task_performance}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 60, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="task_name" type="category" width={120} />
                  <Tooltip />
                  <Bar dataKey="avg_time_seconds" fill="#3b82f6" name="Average Time (s)">
                    <LabelList dataKey="avg_time_seconds" position="right" />
                  </Bar>
                  <ReferenceLine
                    x={60}
                    stroke="#ef4444"
                    strokeDasharray="3 3"
                    label={{ value: 'Target Time', position: 'top' }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {selectedGuidelineData.feedback_summary && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-gray-500 mb-2">User Feedback</h3>
            <div className="space-y-2">
              {selectedGuidelineData.feedback_summary.map((feedback, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded">
                  <div className="font-medium text-sm">{feedback.question}</div>
                  <div className="text-sm text-gray-600 mt-1">
                    {feedback.answer} (Mentioned by {feedback.count} users)
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Add these state variables 
  const [dbTestResult, setDbTestResult] = useState(null);
  const [isTestingDb, setIsTestingDb] = useState(false);
  const [diagnosticResults, setDiagnosticResults] = useState(null);
  
  // Add a function to run diagnostics
  const runConnectionDiagnostics = async () => {
    setIsTestingDb(true);
    try {
      const results = await runDiagnostics();
      setDiagnosticResults(results);
      console.log("Diagnostic results:", results);
    } catch (error) {
      console.error("Error running diagnostics:", error);
    } finally {
      setIsTestingDb(false);
    }
  };
  
  // Add this new useEffect for the database test
  useEffect(() => {
    const runDatabaseTest = async () => {
      setIsTestingDb(true);
      try {
        const result = await testDatabaseConnection();
        setDbTestResult(result);
      } catch (error) {
        setDbTestResult({
          success: false,
          error: error.message
        });
      } finally {
        setIsTestingDb(false);
      }
    };
    
    runDatabaseTest();
  }, []);
  
  // Update your database test UI to show more helpful information:
  const renderDatabaseTestResult = () => {
    return (
      <div className="mb-4 bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">Database Connection Status</h3>
          <div className="space-x-2">
            <button 
              className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
              onClick={async () => await testDatabaseConnection()}
              disabled={isTestingDb}
            >
              {isTestingDb ? 'Testing...' : 'Test Connection'}
            </button>
            <button 
              className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
              onClick={runConnectionDiagnostics}
              disabled={isTestingDb}
            >
              Diagnose Issues
            </button>
          </div>
        </div>
        
        {dbTestResult && (
          <div className="mt-2">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${dbTestResult.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm font-medium">Connection Status: {dbTestResult.success ? 'Connected' : 'Failed'}</span>
            </div>
            
            {!dbTestResult.success && (
              <div className="mt-1 text-sm text-red-600">
                Error: {dbTestResult.error}
              </div>
            )}
          </div>
        )}
        
        {/* Diagnostic Results Display */}
        {diagnosticResults && (
          <div className="mt-3 pt-3 border-t border-gray-200 text-sm">
            <h4 className="font-medium">Diagnostic Results:</h4>
            
            <div className="mt-2 space-y-2">
              <div className="flex items-center">
                <div className={`w-2 h-2 rounded-full mr-2 ${diagnosticResults.apiConnection.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span>API Server: {diagnosticResults.apiConnection.message}</span>
              </div>
              
              {diagnosticResults.dbConnection && (
                <div className="flex items-center">
                  <div className={`w-2 h-2 rounded-full mr-2 ${diagnosticResults.dbConnection.success ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span>Database: {diagnosticResults.dbConnection.message}</span>
                </div>
              )}
            </div>
            
            {diagnosticResults.recommendations.length > 0 && (
              <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
                <div className="font-medium">Recommendations:</div>
                <ul className="mt-1 space-y-1 pl-5 list-disc text-xs">
                  {diagnosticResults.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };
  
  // Then add this component right after the header in your JSX return
  return (
    <div className="bg-gray-50 p-4 rounded-lg">
      <div className="bg-gray-800 text-white p-4 rounded-t-lg mb-4 flex justify-between items-center">
        <div className="flex items-center">
          <h1 className="text-xl font-bold">SECO Transparency Dashboard</h1>
          <div className="ml-3 px-2 py-1 bg-blue-600 rounded-full text-xs flex items-center">
            <Activity size={12} className="mr-1" /> 
            <span>Sustainable Transparency KPIs</span>
          </div>
        </div>
        <div className="flex space-x-2">
          <button 
            className={`px-3 py-1 rounded flex items-center ${activeTab === 'overview' ? 'bg-blue-600' : 'bg-gray-700'}`}
            onClick={() => {
              setActiveTab('overview');
              setSelectedFactor(null);
              setSelectedDimension(null);
              setShowGuidelinesForDimension(null);
            }}
          >
            <Info size={16} className="mr-1" /> Overview
          </button>
          <button 
            className={`px-3 py-1 rounded flex items-center ${activeTab === 'guidelines' ? 'bg-blue-600' : 'bg-gray-700'}`}
            onClick={() => setActiveTab('guidelines')}
          >
            <FileText size={16} className="mr-1" /> Guidelines
          </button>
          <button 
            className={`px-3 py-1 rounded flex items-center ${activeTab === 'hotspots' ? 'bg-blue-600' : 'bg-gray-700'}`}
            onClick={() => setActiveTab('hotspots')}
          >
            <Zap size={16} className="mr-1" /> Hotspots
          </button>
        </div>
      </div>
      
      {/* Add the database test result here */}
      {renderDatabaseTestResult()}
      
      <div className="mb-4 flex justify-between items-center">
        <div className="text-sm text-gray-500">Last updated: March 6, 2025</div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center">
            <span className="text-sm mr-2">Timeframe:</span>
            <select 
              className="bg-white border rounded px-2 py-1 text-sm"
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
            >
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </div>
          <div className="flex items-center bg-white px-3 py-1 rounded border">
            <Eye size={14} className="mr-1 text-blue-500" />
            <span className="text-sm">KPI Achievement Rate: </span>
            <span className="ml-1 font-bold text-yellow-600">66%</span>
          </div>
        </div>
      </div>
      
      {(activeTab === 'overview' && !showGuidelinesForDimension) && (
        <div>
          <div className="bg-white p-4 rounded-lg shadow mb-4">
            <h2 className="text-lg font-semibold text-blue-600 mb-4">SECO Transparency Dashboard</h2>
            <p className="text-sm text-gray-600 mb-4">
              This dashboard operationalizes sustainable transparency in software ecosystems. It covers technical, social, environmental, and economic dimensions to help SECO managers make data-driven decisions.
            </p>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div className="bg-blue-50 p-3 rounded-lg shadow">
                <div className="flex items-center mb-2">
                  <Code size={18} className="text-blue-600 mr-2" />
                  <h3 className="font-medium">Technical Dimension</h3>
                </div>
                <div className="text-3xl font-bold">70%</div>
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className="flex items-center mt-2">
                  <div className="flex-1 bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-blue-500 h-full" style={{width: '70%'}}></div>
                  </div>
                </div>
                <button 
                  className="mt-3 w-full px-2 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                  onClick={() => setShowGuidelinesForDimension('Technical')}
                >
                  View Guidelines
                </button>
              </div>
              
              <div className="bg-green-50 p-3 rounded-lg shadow">
                <div className="flex items-center mb-2">
                  <Users size={18} className="text-green-600 mr-2" />
                  <h3 className="font-medium">Social Dimension</h3>
                </div>
                <div className="text-3xl font-bold">80%</div>
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className="flex items-center mt-2">
                  <div className="flex-1 bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-green-500 h-full" style={{width: '80%'}}></div>
                  </div>
                </div>
                <button 
                  className="mt-3 w-full px-2 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                  onClick={() => setShowGuidelinesForDimension('Social')}
                >
                  View Guidelines
                </button>
              </div>
              
              <div className="bg-yellow-50 p-3 rounded-lg shadow">
                <div className="flex items-center mb-2">
                  <Globe size={18} className="text-yellow-600 mr-2" />
                  <h3 className="font-medium">Economic Dimension</h3>
                </div>
                <div className="text-3xl font-bold">50%</div>
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className="flex items-center mt-2">
                  <div className="flex-1 bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-yellow-500 h-full" style={{width: '50%'}}></div>
                  </div>
                </div>
                <button 
                  className="mt-3 w-full px-2 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
                  onClick={() => setShowGuidelinesForDimension('Economic')}
                >
                  View Guidelines
                </button>
              </div>
              
              <div className="bg-teal-50 p-3 rounded-lg shadow">
                <div className="flex items-center mb-2">
                  <Activity size={18} className="text-teal-600 mr-2" />
                  <h3 className="font-medium">Environmental Dimension</h3>
                </div>
                <div className="text-3xl font-bold">30%</div>
                <div className="text-sm text-gray-600">Overall Score</div>
                <div className="flex items-center mt-2">
                  <div className="flex-1 bg-gray-200 h-2 rounded-full overflow-hidden">
                    <div className="bg-teal-500 h-full" style={{width: '30%'}}></div>
                  </div>
                </div>
                <button 
                  className="mt-3 w-full px-2 py-1 bg-teal-600 text-white rounded text-sm hover:bg-teal-700"
                  onClick={() => setShowGuidelinesForDimension('Environmental')}
                >
                  View Guidelines
                </button>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-white p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Guidelines Status Summary</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'Technical', completed: 3, partial: 8, notStarted: 3 },
                      { name: 'Social', completed: 1, partial: 3, notStarted: 2 },
                      { name: 'Economic', completed: 1, partial: 2, notStarted: 1 },
                      { name: 'Environmental', completed: 0, partial: 2, notStarted: 4 }
                    ]}
                    layout="vertical"
                    margin={{ top: 20, right: 30, left: 80, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis type="category" dataKey="name" />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="completed" stackId="a" name="Completed" fill="#10b981" />
                    <Bar dataKey="partial" stackId="a" name="Partial" fill="#f59e0b" />
                    <Bar dataKey="notStarted" stackId="a" name="Not Started" fill="#9ca3af" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow">
              <h2 className="text-lg font-semibold mb-4">Conditioning Factors</h2>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {conditioningFactors.map(factor => (
                  <div 
                    key={factor.id} 
                    className="border rounded p-3 cursor-pointer hover:bg-gray-50"
                    onClick={() => {
                      setSelectedFactor(factor.id);
                      setActiveTab('guidelines');
                    }}
                  >
                    <div className="flex justify-between items-center">
                      <div className="font-medium">{factor.id}: {factor.name}</div>
                      <div className={`px-2 py-1 text-xs rounded-full ${
                        factor.status === 'advanced' ? 'bg-green-100 text-green-800' :
                        factor.status === 'established' ? 'bg-green-100 text-green-700' :
                        factor.status === 'developing' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {getFactorStatusText(factor.status)}
                      </div>
                    </div>
                    <div className="mt-2 flex space-x-1">
                      <div className={`h-1.5 w-1/4 rounded-l ${factor.status === 'initial' || factor.status === 'developing' || factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 w-1/4 ${factor.status === 'developing' || factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 w-1/4 ${factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 w-1/4 rounded-r ${factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded-lg shadow col-span-2">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold">Overall Transparency Status</h2>
                <div className="text-lg font-bold">58%</div>
              </div>
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span>Overall Ecosystem Transparency</span>
                  <span>58%</span>
                </div>
                <div className="w-full bg-gray-200 h-3 rounded-full overflow-hidden">
                  <div className="bg-blue-600 h-full" style={{width: '58%'}}></div>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-sm font-medium mb-2">Guidelines Status</div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div> Completed</span>
                      <span>5/27 (19%)</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-yellow-500 mr-1"></div> Partial</span>
                      <span>15/27 (56%)</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-gray-400 mr-1"></div> Not Started</span>
                      <span>7/27 (26%)</span>
                    </div>
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">Action Items</div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-blue-500 mr-1"></div> Planned</span>
                      <span>5/8</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-yellow-500 mr-1"></div> In Progress</span>
                      <span>3/8</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="flex items-center"><div className="w-3 h-3 rounded-full bg-green-500 mr-1"></div> Completed</span>
                      <span>0/8</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold">Transparency Hotspots</h2>
                <button 
                  className="text-xs text-blue-600 hover:underline"
                  onClick={() => setActiveTab('hotspots')}
                >
                  View all
                </button>
              </div>
              <div className="space-y-2">
                {kpiData.flatMap(kpi => 
                  kpi.hotspots.filter(h => h.severity === 'high')
                ).slice(0, 4).map((hotspot, index) => (
                  <div key={index} className="border rounded p-2 flex justify-between items-center">
                    <div className="flex items-center">
                      <div className="w-2 h-2 rounded-full bg-red-500 mr-2"></div>
                      <span className="text-sm">{hotspot.area}</span>
                    </div>
                    <div className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">
                      {hotspot.time} min avg
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {(activeTab === 'overview' && showGuidelinesForDimension) && (
        <div>
          <div className="bg-white p-4 rounded-lg shadow mb-4">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center">
                <button 
                  className="mr-2 p-1 rounded hover:bg-gray-100"
                  onClick={() => setShowGuidelinesForDimension(null)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <h2 className="text-lg font-semibold">{showGuidelinesForDimension} Dimension Guidelines</h2>
              </div>
              <div className={`px-3 py-1 rounded text-sm font-medium ${
                showGuidelinesForDimension === 'Technical' ? 'bg-blue-100 text-blue-800' :
                showGuidelinesForDimension === 'Social' ? 'bg-green-100 text-green-800' :
                showGuidelinesForDimension === 'Economic' ? 'bg-yellow-100 text-yellow-800' :
                'bg-teal-100 text-teal-800'
              }`}>
                Overall: {
                  showGuidelinesForDimension === 'Technical' ? '70%' :
                  showGuidelinesForDimension === 'Social' ? '80%' :
                  showGuidelinesForDimension === 'Economic' ? '50%' : '30%'
                }
              </div>
            </div>
            
            <div className="space-y-4">
              {guidelinesData
                .filter(g => g.dimension === showGuidelinesForDimension || g.dimension === showGuidelinesForDimension.toLowerCase())
                .map(guideline => {
                  const guidelineStatus = getGuidelineStatus(guideline);
                  return (
                    <div key={guideline.id} className="border rounded-lg p-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="flex items-center">
                            <div className={`p-1 rounded-full mr-2 ${
                              guidelineStatus === 'completed' ? 'bg-green-100' :
                              guidelineStatus === 'partial' ? 'bg-yellow-100' : 'bg-gray-100'
                            }`}>
                              {getStatusIcon(guidelineStatus)}
                            </div>
                            <h3 className="font-medium">{guideline.id}: {guideline.name}</h3>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">{guideline.description}</p>
                        </div>
                        <div className="text-xs flex flex-col items-end">
                          <span className={`px-2 py-1 rounded ${
                            guidelineStatus === 'completed' ? 'bg-green-100 text-green-800' :
                            guidelineStatus === 'partial' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {getStatusText(guidelineStatus)}
                          </span>
                          <span className="mt-1">{guideline.successCriteria.filter(c => c.status === 'completed').length}/{guideline.successCriteria.length} criteria met</span>
                        </div>
                      </div>
                      
                      <div className="mt-3">
                        <div className="text-xs text-gray-500 mb-1">Success Criteria</div>
                        <div className="space-y-2">
                          {guideline.successCriteria.map(criterion => (
                            <div key={criterion.id} className="flex justify-between items-center">
                              <div className="flex items-center">
                                {getStatusIcon(criterion.status)}
                                <span className="ml-2 text-sm">{criterion.name}</span>
                              </div>
                              <span className={`text-xs px-2 py-1 rounded ${
                                criterion.status === 'completed' ? 'bg-green-100 text-green-800' :
                                criterion.status === 'partial' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {getStatusText(criterion.status)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div className="mt-3 flex flex-wrap gap-1">
                        {guideline.conditioningFactors.map(cf => (
                          <span key={cf} className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                            {cf}
                          </span>
                        ))}
                        {guideline.devExpFactors.map(f => (
                          <span key={f} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
                            {f}
                          </span>
                        ))}
                        {guideline.processes.map(p => (
                          <span key={p} className="text-xs bg-gray-100 text-gray-800 px-2 py-1 rounded">
                            {p}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      )}
      
      {activeTab === 'guidelines' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Guidelines List */}
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-semibold">Transparency Guidelines</h2>
              <div className="flex space-x-1">
                {selectedFactor && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs flex items-center">
                    Filter: {selectedFactor}
                    <button 
                      className="ml-1 text-blue-800 hover:text-blue-900"
                      onClick={() => setSelectedFactor(null)}
                    >
                      ×
                    </button>
                  </span>
                )}
                {selectedDimension && (
                  <span className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs flex items-center">
                    Dimension: {selectedDimension}
                    <button 
                      className="ml-1 text-purple-800 hover:text-purple-900"
                      onClick={() => setSelectedDimension(null)}
                    >
                      ×
                    </button>
                  </span>
                )}
              </div>
            </div>
            
            {!selectedFactor && !selectedDimension && (
              <div className="mb-3 flex flex-wrap gap-1">
                <div className="text-xs mr-1 text-gray-500">Filter by factor:</div>
                {conditioningFactors.map(factor => (
                  <span 
                    key={factor.id} 
                    className="px-1.5 py-0.5 bg-blue-100 text-blue-800 rounded text-xs cursor-pointer hover:bg-blue-200"
                    onClick={() => setSelectedFactor(factor.id)}
                  >
                    {factor.id}
                  </span>
                ))}
              </div>
            )}
            
            <div className="space-y-2">
              {getFilteredGuidelines().map(guideline => {
                const guidelineStatus = getGuidelineStatus(guideline);
                return (
                  <div 
                    key={guideline.id} 
                    className={`border p-3 rounded cursor-pointer hover:bg-gray-50 transition ${selectedGuideline === guideline.id ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedGuideline(guideline.id)}
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex items-center">
                        {guideline.id === 'G1' && <Globe size={16} className="text-blue-500 mr-2" />}
                        {guideline.id === 'G2' && <Users size={16} className="text-green-500 mr-2" />}
                        {guideline.id === 'G3' && <Globe size={16} className="text-purple-500 mr-2" />}
                        {guideline.id === 'G4' && <Search size={16} className="text-yellow-500 mr-2" />}
                        {guideline.id === 'G5' && <BookOpen size={16} className="text-red-500 mr-2" />}
                        {guideline.id === 'G6' && <Code size={16} className="text-indigo-500 mr-2" />}
                        <span className="font-medium">{guideline.id}: {guideline.name}</span>
                      </div>
                      <div className="flex items-center">
                        <div className="flex items-center mr-1">
                          <span className={`mr-1 flex h-5 w-5 items-center justify-center rounded-full ${
                            guidelineStatus === 'completed' ? 'bg-green-100' : 
                            guidelineStatus === 'partial' ? 'bg-yellow-100' : 'bg-gray-100'
                          }`}>
                            {getStatusIcon(guidelineStatus)}
                          </span>
                          <span className="text-xs">
                            {guideline.successCriteria.filter(c => c.status === 'completed').length}/{guideline.successCriteria.length}
                          </span>
                        </div>
                        {selectedGuideline === guideline.id ? (
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        ) : (
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        )}
                      </div>
                    </div>
                    <div className="mt-1 flex space-x-1">
                      {guideline.conditioningFactors.map(cf => (
                        <span 
                          key={cf} 
                          className="text-xs bg-green-100 text-green-800 px-1.5 py-0.5 rounded cursor-pointer hover:bg-green-200"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFactor(cf);
                          }}
                        >
                          {cf}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
          {/* Guideline Details */}
          <div className="bg-white p-4 rounded-lg shadow col-span-2">
            {renderGuidelineDetails()}
          </div>
        </div>
      )}
      
      {activeTab === 'factors' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Conditioning Factors */}
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold text-green-600 mb-4">Conditioning Factors for Transparency</h2>
            <p className="text-sm text-gray-600 mb-3">
              These factors influence transparency in the SECO. They represent conditions that enable or limit transparency.
              Rather than percentages, they reflect qualitative maturity levels of the ecosystem.
            </p>
            <div className="space-y-4">
              {conditioningFactors.map(factor => (
                <div key={factor.id} className="border rounded p-3">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-medium">{factor.id}: {factor.name}</div>
                    <div className={`px-2 py-1 text-xs font-medium rounded-full ${
                      factor.status === 'advanced' ? 'bg-green-100 text-green-800' :
                      factor.status === 'established' ? 'bg-green-100 text-green-700' :
                      factor.status === 'developing' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {getFactorStatusText(factor.status)}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{factor.description}</p>
                  
                  {/* Maturity level indicator */}
                  <div className="flex items-center mb-2">
                    <div className="flex-grow grid grid-cols-4 gap-1">
                      <div className={`h-1.5 rounded-l ${factor.status === 'initial' || factor.status === 'developing' || factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 ${factor.status === 'developing' || factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 ${factor.status === 'established' || factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                      <div className={`h-1.5 rounded-r ${factor.status === 'advanced' ? getFactorStatusColor(factor.status) : 'bg-gray-300'}`}></div>
                    </div>
                    <div className="ml-2">
                      <span className="text-xs">
                        {factor.status === 'initial' ? 'Initial' : 
                         factor.status === 'developing' ? 'Developing' : 
                         factor.status === 'established' ? 'Established' : 'Advanced'}
                      </span>
                    </div>
                  </div>
                  
                  {/* Related guidelines */}
                  <div className="mt-2">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-xs text-gray-500">Related Guidelines:</span>
                      <button 
                        className="text-xs text-blue-600 hover:underline flex items-center"
                        onClick={() => {
                          setSelectedFactor(factor.id);
                          setActiveTab('guidelines');
                        }}
                      >
                        View <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {guidelinesData
                        .filter(g => g.conditioningFactors.includes(factor.id))
                        .map(g => (
                          <span key={g.id} className="text-xs bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded">{g.id}</span>
                        ))
                      }
                    </div>
                  </div>
                  
                  {/* Development recommendations for non-advanced factors */}
                  {factor.status !== 'advanced' && (
                    <div className="mt-2 text-xs bg-blue-50 p-2 rounded">
                      <div className="font-medium text-blue-700">Development recommendations:</div>
                      <ul className="mt-1 space-y-1 pl-4 list-disc">
                        {factor.id === 'CF1' && (
                          <>
                            <li>Implement structured communication channels</li>
                            <li>Reduce response time to developer queries</li>
                          </>
                        )}
                        {factor.id === 'CF2' && (
                          <>
                            <li>Improve search functionality and organization</li>
                            <li>Enhance accessibility for developers with disabilities</li>
                          </>
                        )}
                        {factor.id === 'CF3' && (
                          <>
                            <li>Create improved onboarding and learning materials</li>
                            <li>Simplify complex documentation sections</li>
                          </>
                        )}
                        {factor.id === 'CF5' && (
                          <>
                            <li>Improve UI/UX of documentation interfaces</li>
                            <li>Add contextual navigation elements</li>
                          </>
                        )}
                        {factor.id === 'CF6' && (
                          <>
                            <li>Implement audit logs for platform changes</li>
                            <li>Add version history for documentation</li>
                          </>
                        )}
                        {factor.id === 'CF7' && (
                          <>
                            <li>Implement project timeline visualization tools</li>
                            <li>Add roadmap and deprecation tracking</li>
                          </>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          {/* Developer Experience Factors */}
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold text-purple-600 mb-4">Developer Experience Factors</h2>
            <p className="text-sm text-gray-600 mb-3">
              These factors represent the developer experience aspects that influence SECO transparency.
              They reflect qualitative aspects of the ecosystem that impact how developers interact with the platform.
            </p>
            
            {/* Group factors by category */}
            {['Common Technological Platform', 'Projects and Applications', 'Community Interaction', 'Expectations and Value'].map(group => (
              <div key={group} className="mb-4">
                <h3 className="font-medium text-sm text-gray-600 mb-2">{group}</h3>
                <div className="space-y-3">
                  {devExpFactors.filter(f => f.group === group).map(factor => (
                    <div key={factor.id} className="border rounded p-2">
                      <div className="flex justify-between items-center mb-1">
                        <div className="text-sm font-medium">{factor.id}: {factor.name}</div>
                        <div className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                          factor.dimension === 'Technical' ? 'bg-blue-100 text-blue-800' : 
                          factor.dimension === 'Social' ? 'bg-green-100 text-green-800' : 
                          factor.dimension === 'Organizational' ? 'bg-purple-100 text-purple-800' : 
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {factor.dimension}
                        </div>
                      </div>
                      
                      {/* Maturity indication */}
                      <div className="flex items-center mb-2">
                        <div className="flex-grow flex space-x-1">
                          <div className={`h-1.5 w-1/4 rounded-l ${factor.status === 'initial' || factor.status === 'developing' || factor.status === 'established' ? 
                            (factor.dimension === 'Technical' ? 'bg-blue-400' : 
                             factor.dimension === 'Social' ? 'bg-green-400' : 
                             factor.dimension === 'Organizational' ? 'bg-purple-400' : 'bg-yellow-400') : 'bg-gray-300'}`}></div>
                          <div className={`h-1.5 w-1/4 ${factor.status === 'developing' || factor.status === 'established' ? 
                            (factor.dimension === 'Technical' ? 'bg-blue-400' : 
                             factor.dimension === 'Social' ? 'bg-green-400' : 
                             factor.dimension === 'Organizational' ? 'bg-purple-400' : 'bg-yellow-400') : 'bg-gray-300'}`}></div>
                          <div className={`h-1.5 w-1/4 ${factor.status === 'established' ? 
                            (factor.dimension === 'Technical' ? 'bg-blue-400' : 
                             factor.dimension === 'Social' ? 'bg-green-400' : 
                             factor.dimension === 'Organizational' ? 'bg-purple-400' : 'bg-yellow-400') : 'bg-gray-300'}`}></div>
                          <div className={`h-1.5 w-1/4 rounded-r bg-gray-300`}></div>
                        </div>
                        <div className="ml-2">
                          <span className="text-xs">
                            {factor.status === 'initial' ? 'Initial' : 
                             factor.status === 'developing' ? 'Developing' : 
                             factor.status === 'established' ? 'Established' : 'Advanced'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Show related guidelines */}
                      <div className="mt-1">
                        <div className="flex flex-wrap gap-1">
                          {guidelinesData
                            .filter(g => g.devExpFactors.includes(factor.id))
                            .map(g => (
                              <span 
                                key={g.id} 
                                className="text-xs bg-gray-100 text-gray-800 px-1 rounded cursor-pointer hover:bg-gray-200"
                                onClick={() => {
                                  setSelectedGuideline(g.id);
                                  setActiveTab('guidelines');
                                }}
                              >
                                {g.id}
                              </span>
                            ))
                          }
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            
            <div className="mt-4 p-3 bg-gray-50 rounded border text-sm">
              <p className="font-medium">Note on measurement approach:</p>
              <p className="text-xs text-gray-600 mt-1">
                Developer experience factors are assessed through qualitative methods including developer surveys, 
                interviews, and usage analytics. These factors influence transparency but are measured by maturity 
                level rather than percentages, using a four-tier scale: Initial, Developing, Established, and Advanced.
              </p>
            </div>
          </div>
        </div>
      )}
      
      <div className="mt-4 bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center">
          <h3 className="font-medium">Sustainable Transparency Dimensions</h3>
          <div className="flex items-center">
            <Clock size={14} className="text-gray-500 mr-1" />
            <div className="text-xs text-gray-500">Last updated: March 6, 2025</div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          {/* Show summary by transparency dimension */}
          <div className="border border-blue-200 bg-blue-50 rounded p-3">
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium text-blue-800 flex items-center">
                <Code size={14} className="mr-1" />
                Technical
              </div>
              {getStatusIcon('partial')}
            </div>
            <div className="mt-2 text-sm">
              <div className="flex justify-between items-center mb-1">
                <span>Completed</span>
                <span className="font-medium text-green-700">3/14</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-green-600 h-full" style={{width: '21%'}}></div>
              </div>
              
              <div className="flex justify-between items-center mb-1">
                <span>Partial</span>
                <span className="font-medium text-yellow-700">8/14</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-yellow-500 h-full" style={{width: '57%'}}></div>
              </div>
              
              <div className="flex justify-between items-center">
                <span>Not Started</span>
                <span className="font-medium text-gray-700">3/14</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full">
                <div className="bg-gray-400 h-full" style={{width: '21%'}}></div>
              </div>
            </div>
          </div>
          
          <div className="border border-green-200 bg-green-50 rounded p-3">
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium text-green-800 flex items-center">
                <Users size={14} className="mr-1" />
                Social
              </div>
              {getStatusIcon('partial')}
            </div>
            <div className="mt-2 text-sm">
              <div className="flex justify-between items-center mb-1">
                <span>Completed</span>
                <span className="font-medium text-green-700">1/6</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-green-600 h-full" style={{width: '17%'}}></div>
              </div>
              
              <div className="flex justify-between items-center mb-1">
                <span>Partial</span>
                <span className="font-medium text-yellow-700">3/6</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-yellow-500 h-full" style={{width: '50%'}}></div>
              </div>
              
              <div className="flex justify-between items-center">
                <span>Not Started</span>
                <span className="font-medium text-gray-700">2/6</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full">
                <div className="bg-gray-400 h-full" style={{width: '33%'}}></div>
              </div>
            </div>
          </div>
          
          <div className="border border-purple-200 bg-purple-50 rounded p-3">
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium text-purple-800 flex items-center">
                <Settings size={14} className="mr-1" />
                Organizational
              </div>
              {getStatusIcon('partial')}
            </div>
            <div className="mt-2 text-sm">
              <div className="flex justify-between items-center mb-1">
                <span>Completed</span>
                <span className="font-medium text-green-700">1/3</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-green-600 h-full" style={{width: '33%'}}></div>
              </div>
              
              <div className="flex justify-between items-center mb-1">
                <span>Partial</span>
                <span className="font-medium text-yellow-700">1/3</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-yellow-500 h-full" style={{width: '33%'}}></div>
              </div>
              
              <div className="flex justify-between items-center">
                <span>Not Started</span>
                <span className="font-medium text-gray-700">1/3</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full">
                <div className="bg-gray-400 h-full" style={{width: '33%'}}></div>
              </div>
            </div>
          </div>
          
          <div className="border border-yellow-200 bg-yellow-50 rounded p-3">
            <div className="flex justify-between items-center">
              <div className="text-sm font-medium text-yellow-800 flex items-center">
                <Globe size={14} className="mr-1" />
                Economic
              </div>
              {getStatusIcon('partial')}
            </div>
            <div className="mt-2 text-sm">
              <div className="flex justify-between items-center mb-1">
                <span>Completed</span>
                <span className="font-medium text-green-700">1/4</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-green-600 h-full" style={{width: '25%'}}></div>
              </div>
              
              <div className="flex justify-between items-center mb-1">
                <span>Partial</span>
                <span className="font-medium text-yellow-700">2/4</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full mb-2">
                <div className="bg-yellow-500 h-full" style={{width: '50%'}}></div>
              </div>
              
              <div className="flex justify-between items-center">
                <span>Not Started</span>
                <span className="font-medium text-gray-700">1/4</span>
              </div>
              <div className="w-full bg-white bg-opacity-30 h-1.5 rounded-full">
                <div className="bg-gray-400 h-full" style={{width: '25%'}}></div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="mt-3 border-t pt-2">
          <div className="text-xs text-gray-500 italic">
            This dashboard operationalizes SECO transparency through KPIs and hotspot analysis, enabling data-driven decisions that improve transparency across technical, social, organizational, and economic dimensions.
          </div>
        </div>
      </div>
      
      {activeTab === 'hotspots' && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <h2 className="text-lg font-semibold mb-4">Transparency Hotspots Analysis</h2>
            
            {isLoadingEvaluation ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
              </div>
            ) : (
              <>
                {/* Task Completion Times */}
                <div className="mb-6">
                  <h3 className="text-md font-medium mb-3">Task Completion Analysis</h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={evaluationData.taskCompletionTimes || []}
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="task_name" />
                        <YAxis label={{ value: 'Time (seconds)', angle: -90, position: 'insideLeft' }} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="avg_time_seconds" name="Average Time (s)" fill="#3b82f6" />
                        <ReferenceLine y={60} stroke="red" strokeDasharray="3 3" label="Target Time" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Interaction Types */}
                <div className="mb-6">
                  <h3 className="text-md font-medium mb-3">Interaction Frequency Analysis</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={evaluationData.interactionTypes || []}
                            cx="50%"
                            cy="50%"
                            labelLine={false}
                            outerRadius={80}
                            fill="#8884d8"
                            dataKey="count"
                            nameKey="type"
                            label={({type, count}) => `${type}: ${count}`}
                          >
                            {(evaluationData.interactionTypes || []).map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={['#3b82f6', '#10b981', '#f59e0b', '#ef4444'][index % 4]} />
                            ))}
                          </Pie>
                          <Tooltip />
                          <Legend />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    
                    <div className="h-64">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                          data={evaluationData.interactionTypes || []}
                          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="type" />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="count" name="Frequency" fill="#10b981" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

                {/* Heatmap Visualization */}
                <div className="mb-6">
                  <h3 className="text-md font-medium mb-3">User Interaction Heatmap</h3>
                  <div className="bg-gray-100 p-4 rounded-lg">
                    <HeatmapVisualization 
                      data={evaluationData.heatmapData || []} 
                      width={800} 
                      height={400}
                    />
                    <div className="text-sm text-center mt-2 text-gray-600">
                      Heatmap showing click concentrations in the user interface
                    </div>
                  </div>
                </div>

                {/* User Responses Section */}
                {evaluationData.userResponses && evaluationData.userResponses.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-md font-medium mb-3">User Feedback Analysis</h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {evaluationData.userResponses.map((user, index) => (
                        <div key={index} className="border rounded-lg p-3">
                          <div className="flex justify-between">
                            <div className="font-medium">{user.username || `User ${user.id}`}</div>
                            <div className="text-sm text-gray-500">{user.seco_portal || 'Portal User'}</div>
                          </div>
                          
                          <div className="mt-2 space-y-2">
                            {user.tasks && user.tasks.map((task, taskIndex) => (
                              <div key={taskIndex} className="bg-gray-50 p-2 rounded">
                                <div className="flex justify-between items-center text-sm">
                                  <div className="font-medium">{task.title}</div>
                                  <div className="text-blue-600">{task.duration_seconds}s</div>
                                </div>
                                
                                {task.answers && task.answers.length > 0 && (
                                  <div className="mt-1 space-y-1">
                                    {task.answers.map((answer, answerIndex) => (
                                      <div key={answerIndex} className="text-xs">
                                        <span className="text-gray-700">{answer.question}:</span> 
                                        <span className="ml-1">{answer.answer}</span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Navigation Flows Section */}
                {evaluationData.navigationFlows && evaluationData.navigationFlows.length > 0 && (
                  <div className="mb-6">
                    <h3 className="text-md font-medium mb-3">User Navigation Patterns</h3>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {evaluationData.navigationFlows.map((flow, index) => (
                        <div key={index} className="border rounded-lg p-3">
                          <div className="font-medium mb-2">User {flow.user_id} Navigation Path</div>
                          <div className="flex items-center overflow-x-auto pb-2">
                            {flow.path.map((step, stepIndex) => (
                              <div key={stepIndex} className="flex items-center min-w-max">
                                <div className="bg-blue-50 border border-blue-200 rounded px-2 py-1 text-xs">
                                  <div className="font-medium truncate max-w-xs" title={step.title}>
                                    {step.title || 'Unnamed Page'}
                                  </div>
                                  <div className="text-gray-500 text-xs truncate max-w-xs" title={step.url}>
                                    {step.url}
                                  </div>
                                </div>
                                {stepIndex < flow.path.length - 1 && (
                                  <svg className="h-5 w-5 text-gray-400 mx-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Analysis Summary */}
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h3 className="font-medium flex items-center text-blue-800">
                    <Lightbulb size={18} className="mr-2" />
                    Evaluation Analysis Summary
                  </h3>
                  <p className="mt-2 text-sm">
                    Based on the data above, the main transparency hotspots are:
                  </p>
                  <ul className="mt-1 space-y-1 list-disc list-inside text-sm">
                    <li>Users spend significantly more time than expected when searching for language documentation</li>
                    <li>Click interactions are concentrated in specific areas that may need redesign</li>
                    <li>Navigation patterns show users often revisit the same pages, indicating possible confusion</li>
                  </ul>
                  <div className="mt-3 pt-2 border-t border-blue-200 text-sm font-medium text-blue-800">
                    Recommendation: Focus on improving Guidelines G3 and G4 implementation with emphasis on search functionality and language documentation access.
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SECODashboard;