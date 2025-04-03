// src/services/evaluation.js

// Function to fetch evaluation data from our API
export const fetchEvaluationData = async () => {
  try {
    console.log("Attempting to fetch evaluation data from API...");
    const response = await fetch('/api/evaluation-data');
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`API Error (${response.status}):`, errorText);
      throw new Error(`HTTP error! Status: ${response.status}. Details: ${errorText}`);
    }
    
    const data = await response.json();
    console.log("Successfully fetched evaluation data:", data);
    
    // Check if this is real database data by looking for specific properties
    const isDbData = verifyDatabaseData(data);
    console.log("Is this database data?", isDbData ? "YES - Using real data" : "NO - Using mock data");
    
    return data;
  } catch (error) {
    console.error('Error fetching evaluation data:', error);
    // Log detailed error info
    console.warn('Falling back to mock data');
    return getMockEvaluationData();
  }
};

// Function to test database connectivity
export const testDatabaseConnection = async () => {
  try {
    console.log("Testing database connection...");
    const response = await fetch('/api/evaluation-data?test=true');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const data = await response.json();
    const isDbData = verifyDatabaseData(data);
    
    // Create a detailed report
    console.log("==== DATABASE CONNECTION TEST ====");
    console.log("Response received:", !!data);
    console.log("Data appears to be from database:", isDbData);
    console.log("Task data sample:", data.taskCompletionTimes?.slice(0, 2));
    console.log("Interaction data sample:", data.interactionTypes?.slice(0, 2));
    console.log("================================");
    
    return {
      success: true,
      isDbData,
      data: data
    };
  } catch (error) {
    console.error("Database connection test failed:", error);
    return {
      success: false,
      error: error.message
    };
  }
};

// Function to verify if data is from database vs mock data
function verifyDatabaseData(data) {
  // Real database data will likely have these characteristics that differ from our mock data:
  
  // 1. Check for presence of specific database fields that wouldn't be in mock data
  if (data.taskCompletionTimes && data.taskCompletionTimes.length > 0) {
    // If we have timestamps or IDs that look like real data
    const hasRealIds = data.taskCompletionTimes.some(task => 
      typeof task.task_id === 'number' && task.task_id > 10
    );
    
    if (hasRealIds) return true;
  }
  
  // 2. Check for realistic interaction counts that differ from our mock data
  if (data.interactionTypes && data.interactionTypes.length > 0) {
    // Our mock data has predefined interaction counts (150, 75, etc.)
    // Real data would have different values
    const hasRealisticCounts = !data.interactionTypes.every(type => 
      [25, 75, 150].includes(type.count)
    );
    
    if (hasRealisticCounts) return true;
  }
  
  // 3. Check for the unique structure of user responses from the database
  if (data.userResponses && data.userResponses.length > 0) {
    const hasRealUserData = data.userResponses.some(user => 
      user.tasks && user.tasks.some(task => task.answers && task.answers.length > 0)
    );
    
    if (hasRealUserData) return true;
  }
  
  // If none of the above checks passed, it's likely mock data
  return false;
}

// Function to fetch evaluation data for a specific guideline
export const fetchGuidelineData = async (guidelineId) => {
  try {
    const response = await fetch(`http://localhost:5000/api/evaluation-data?guideline=${guidelineId}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching guideline data for ${guidelineId}:`, error);
    return getMockGuidelineData(guidelineId); // Fallback to mock data
  }
};

// Provide mock data for a specific guideline
function getMockGuidelineData(guidelineId) {
  // Mock data structured to match what the component expects
  return {
    task_performance: [
      { task_name: "Translate the page", avg_time_seconds: 45 },
      { task_name: "Find language docs", avg_time_seconds: 75 },
      { task_name: "Complete task", avg_time_seconds: 30 }
    ],
    feedback_summary: [
      { question: "Was the documentation clear?", answer: "Yes", count: 12 },
      { question: "Did you encounter any issues?", answer: "Navigation was confusing", count: 8 },
      { question: "What could be improved?", answer: "Better translation options", count: 15 }
    ],
    // Add more mock data specific to guidelines if needed
  };
}
  
// Provide mock data for development/testing
function getMockEvaluationData() {
  return {
    taskCompletionTimes: [
      { task_id: 1, task_name: "Translate the page", avg_time_seconds: 45 },
      { task_id: 2, task_name: "Find language docs", avg_time_seconds: 75 },
      { task_id: 3, task_name: "Task description", avg_time_seconds: 30 }
    ],
    interactionTypes: [
      { type: "click", count: 150 },
      { type: "display_update", count: 75 },
      { type: "task_start", count: 25 },
      { type: "task_complete", count: 25 }
    ],
    heatmapData: [
      { x: 100, y: 150, value: 10 },
      { x: 150, y: 200, value: 8 },
      { x: 200, y: 100, value: 5 },
      { x: 300, y: 250, value: 12 }
    ],
    userResponses: [
      // Mock user responses
    ],
    navigationFlows: [
      // Mock navigation flows
    ]
  };
}