import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ScatterChart, Scatter, ZAxis, Cell, Treemap, LabelList } from 'recharts';
import { Info, FileText, Users, Settings, CheckCircle, AlertTriangle, XCircle, Search, Globe, BookOpen, Code, Shield, Zap, Clock, Activity, Target, Eye, Lightbulb, ChevronRight, ChevronDown } from 'lucide-react';
import { PieChart, Pie, ReferenceLine } from 'recharts';
import { fetchEvaluationData, fetchGuidelineData, testDatabaseConnection } from './api/evaluation';
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
  // New state variables
  const [guidelineViewTab, setGuidelineViewTab] = useState('overall'); // 'overall' | 'tasks' | 'sustainability'
  const [evaluationTab, setEvaluationTab] = useState('dissatisfaction'); // 'dissatisfaction' | 'classification'
  
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
      actionItems: [7],
      dissatisfactors: [
        { issue: 'Mobile layout issues', severity: 'medium', impact: 'Users on mobile devices have difficulty accessing some features' },
        { issue: 'Screen reader compatibility', severity: 'high', impact: 'Vision-impaired users cannot navigate effectively' }
      ]
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
      actionItems: [1],
      dissatisfactors: [
        { issue: 'Keyboard navigation missing', severity: 'high', impact: 'Users with motor impairments cannot use the platform' },
        { issue: 'Limited screen reader support', severity: 'high', impact: 'Vision-impaired users have poor experience' },
        { issue: 'Missing video captions', severity: 'medium', impact: 'Hearing-impaired users miss important content' }
      ]
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
      actionItems: [2],
      dissatisfactors: [
        { issue: 'Limited language options', severity: 'high', impact: 'Non-English/Spanish speakers cannot use the platform effectively' },
        { issue: 'Translation quality issues', severity: 'medium', impact: 'Some technical terms are incorrectly translated' }
      ]
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
      actionItems: [3],
      dissatisfactors: [
        { issue: 'Poor search results', severity: 'high', impact: 'Developers spend excessive time searching for information' },
        { issue: 'Confusing information architecture', severity: 'medium', impact: 'Navigation between related topics is difficult' }
      ]
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
      actionItems: [5, 6],
      dissatisfactors: [
        { issue: 'Outdated documentation', severity: 'high', impact: 'Developers waste time with deprecated methods' },
        { issue: 'Incomplete advanced topics', severity: 'medium', impact: 'Advanced use cases require external resources' }
      ]
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
      actionItems: [4],
      dissatisfactors: [
        { issue: 'Too prescriptive examples', severity: 'medium', impact: 'Developers feel forced into one coding style' },
        { issue: 'Limited implementation variety', severity: 'medium', impact: 'Solutions do not fit various architectural patterns' }
      ]
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
      actionItems: [6],
      dissatisfactors: [
        { issue: 'Hidden addon costs', severity: 'high', impact: 'Budget planning is difficult with unexpected costs' },
        { issue: 'No cost calculator', severity: 'medium', impact: 'Custom configurations require manual calculations' }
      ]
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
      actionItems: [],
      dissatisfactors: [
        { issue: 'No carbon metrics', severity: 'high', impact: 'Cannot track environmental cost of using platform' },
        { issue: 'Lack of sustainability roadmap', severity: 'medium', impact: 'No visibility into future environmental improvements' }
      ]
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

  // Calculate percentages for guideline status
  const calculateGuidelineStatusPercentages = (guideline) => {
    if (!guideline) return { completed: 0, partial: 0, notStarted: 0 };
    
    const total = guideline.successCriteria.length;
    const completed = guideline.successCriteria.filter(c => c.status === 'completed').length;
    const partial = guideline.successCriteria.filter(c => c.status === 'partial').length;
    const notStarted = total - completed - partial;
    
    return {
      completed: Math.round((completed / total) * 100),
      partial: Math.round((partial / total) * 100),
      notStarted: Math.round((notStarted / total) * 100)
    };
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
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
            
            <div className="space-y-2 overflow-y-auto max-h-[calc(100vh-200px)]">
              {getFilteredGuidelines().map(guideline => {
                const guidelineStatus = getGuidelineStatus(guideline);
                const isSelected = selectedGuideline === guideline.id;
                return (
                  <div 
                    key={guideline.id} 
                    className={`border p-3 rounded-lg cursor-pointer hover:bg-gray-50 transition ${isSelected ? 'border-blue-500 bg-blue-50' : ''}`}
                    onClick={() => setSelectedGuideline(guideline.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div className="text-blue-600 mr-2">
                          {guideline.id === 'G1' && <Globe size={16} />}
                          {guideline.id === 'G2' && <Users size={16} />}
                          {guideline.id === 'G3' && <Globe size={16} />}
                          {guideline.id === 'G4' && <Search size={16} />}
                          {guideline.id === 'G5' && <BookOpen size={16} />}
                          {guideline.id === 'G6' && <Code size={16} />}
                          {guideline.id === 'G7' && <Activity size={16} />}
                          {guideline.id === 'G8' && <Shield size={16} />}
                      </div>
                        <div>
                      <div className="flex items-center">
                            <span className="font-medium text-sm">{guideline.id}: {guideline.name}</span>
                        </div>
                          <div className="flex mt-1 space-x-1">
                            {guideline.conditioningFactors.slice(0, 3).map(cf => (
                        <span 
                          key={cf} 
                                className="text-xs bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded"
                        >
                          {cf}
                        </span>
                      ))}
                            {guideline.conditioningFactors.length > 3 && (
                              <span className="text-xs bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded">
                                +{guideline.conditioningFactors.length - 3}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center">
                        <div className="mr-2 flex items-center">
                          <span className="text-yellow-500 mr-1">
                            {guideline.id === 'G1' && "2/3"}
                            {guideline.id === 'G2' && "0/3"}
                            {guideline.id === 'G3' && "0/3"}
                            {guideline.id === 'G4' && "0/3"}
                            {guideline.id === 'G5' && "1/3"}
                            {guideline.id === 'G6' && "0/3"}
                            {guideline.id === 'G7' && "1/3"}
                            {guideline.id === 'G8' && "0/3"}
                          </span>
                        </div>
                        <div>
                          {isSelected ? (
                            <ChevronDown className="h-4 w-4 text-blue-500" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-gray-400" />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          
          {/* Guideline Detail Panel */}
          <div className="col-span-2 bg-white p-4 rounded-lg shadow">
            {!selectedGuideline ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-400 py-10">
                <FileText size={48} />
                <p className="mt-2">Select a guideline to view details</p>
                {(selectedFactor || selectedDimension) && (
                  <p className="mt-1 text-sm text-blue-500">
                    {selectedFactor ? `Showing guidelines related to ${selectedFactor}` : `Showing ${selectedDimension} guidelines`}
                  </p>
                )}
              </div>
            ) : (
              <div className="flex h-full">
                {/* MAIN CONTENT */}
                <div className="flex-grow flex flex-col">
                  <h2 className="text-xl font-bold mb-4">GUIDELINE OVERALL STATUS</h2>
                  
                  {/* TAB BAR */}
                  <div className="flex border rounded-lg overflow-hidden mb-6">
                    {['overall', 'tasks', 'sustainability'].map(t => (
                      <button
                        key={t}
                        onClick={() => setGuidelineViewTab(t)}
                        className={`flex-1 px-6 py-3 text-sm font-medium ${
                          guidelineViewTab === t 
                            ? 'bg-white border-b-2 border-blue-600 text-blue-600' 
                            : 'bg-gray-50 text-gray-600'
                        }`}
                      >
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </button>
                    ))}
                    </div>
                  
                  {/* CONTENT AREA */}
                  <div className="flex-grow overflow-y-auto">
                    {guidelineViewTab === 'overall' && (
                      <div className="grid grid-cols-2 gap-4">
                        {/* TOP ROW */}
                        {/* — EVALUATION CARD — */}
                        <div className="border rounded-lg">
                          <div className="p-4">
                            <h3 className="font-semibold uppercase text-sm mb-4">Evaluation</h3>
                            
                            <div className="flex border-b mb-4">
                              {['dissatisfaction', 'classification'].map(t => (
                      <button 
                                  key={t} 
                                  onClick={() => setEvaluationTab(t)}
                                  className={`flex-1 py-2 text-sm ${
                                    evaluationTab === t 
                                      ? 'text-blue-600 border-b-2 border-blue-600' 
                                      : 'text-gray-500'
                                  }`}
                                >
                                  {t.charAt(0).toUpperCase() + t.slice(1)}
                      </button>
                              ))}
                    </div>
                            
                            {evaluationTab === 'dissatisfaction' && (
                              <div className="space-y-4">
                                <div className="pb-3">
                                  <div className="flex justify-between items-center">
                                    <div className="font-medium">Poor search results</div>
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-800">
                                      high
                                    </span>
                    </div>
                                  <p className="text-xs text-gray-600 mt-1">Developers spend excessive time searching for information</p>
                  </div>
                                <div>
                                  <div className="flex justify-between items-center">
                                    <div className="font-medium">Confusing information architecture</div>
                                    <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-800">
                                      medium
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-600 mt-1">Navigation between related topics is difficult</p>
                                </div>
                              </div>
                            )}
                            
                            {evaluationTab === 'classification' && (
                              <div className="space-y-3">
                                {(() => {
                                  const guideline = guidelinesData.find(g => g.id === selectedGuideline);
                                  return guideline?.successCriteria?.map((criteria, index) => (
                                    <div key={index} className="flex items-center justify-between border-b pb-3 last:border-b-0">
                                      <div className="flex items-center">
                                        {getStatusIcon(criteria.status)}
                                        <span className="ml-2">{criteria.name}</span>
                                      </div>
                                      <span className={`text-xs px-2 py-0.5 rounded ${
                                        criteria.status === 'completed' ? 'bg-green-100 text-green-800' :
                                        criteria.status === 'partial' ? 'bg-yellow-100 text-yellow-800' :
                                        'bg-gray-100 text-gray-800'
                                      }`}>
                                        {getStatusText(criteria.status)}
                                      </span>
                                    </div>
                                  )) || <div className="text-sm text-gray-400 italic">No classification data available</div>
                                })()}
                    </div>
                  )}
                </div>
            </div>
                        
                        {/* TRANSPARENCY CARD */}
                        <div className="border rounded-lg p-4">
                          <h3 className="font-semibold uppercase text-sm mb-4">Transparency</h3>
                          <button className="text-blue-600 text-sm flex items-center">
                            KSF <span className="ml-1">›</span>
                          </button>
          </div>
          
                        {/* BOTTOM ROW */}
                        {/* — DX CARD — */}
                        <div className="border rounded-lg p-4">
                          <h3 className="font-semibold uppercase text-sm mb-2">DX</h3>
                          <p className="text-xs text-gray-500 mb-2">Sentiment</p>
                          <span className="inline-block px-3 py-1 rounded-full bg-gray-200 text-blue-600 text-sm">Happy</span>
                          
                          {/* word cloud placeholder */}
                          <div className="my-6 h-20 flex items-center justify-center text-gray-400 italic">
                            word cloud
                          </div>
                          
                          <div className="flex justify-between text-xs mt-4">
                            <span className="text-blue-600">Happy</span>
                            <button className="text-blue-600">Action ›</button>
                        </div>
                      </div>
                      
                        {/* SUSTAINABILITY CARD */}
                        <div className="border rounded-lg p-4">
                          <h3 className="font-semibold uppercase text-sm mb-4">Sustainability</h3>
                          <button className="text-blue-600 text-sm flex items-center">
                            Action <span className="ml-1">›</span>
                          </button>
                          <div className="mt-8 text-xs text-gray-400 text-center italic">
                            Sustainability metrics will appear here
                        </div>
                        </div>
                      </div>
                    )}
                    
                    {guidelineViewTab === 'tasks' && (
                      <div className="h-60 flex items-center justify-center text-sm text-gray-500 border rounded-lg">
                        TODO: tasks view
                        </div>
                    )}
                    
                    {guidelineViewTab === 'sustainability' && (
                      <div className="h-60 flex items-center justify-center text-sm text-gray-500 border rounded-lg">
                        TODO: sustainability view
                      </div>
                    )}
                    </div>
                </div>
              </div>
            )}
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
    </div>
  );
};

export default SECODashboard;