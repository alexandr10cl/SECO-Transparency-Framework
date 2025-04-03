// src/api/databaseTroubleshooter.js

// Function to check the basic API connectivity without querying the database
export const checkApiConnectivity = async () => {
  try {
    console.log("Testing basic API connectivity...");
    // Send a simple ping request that shouldn't require database access
    const response = await fetch('/api/ping');
    
    if (response.ok) {
      return {
        success: true,
        message: "API server is reachable"
      };
    } else {
      return {
        success: false,
        message: `API server returned status: ${response.status}`,
        status: response.status
      };
    }
  } catch (error) {
    return {
      success: false,
      message: "Cannot reach API server. Check if Flask is running.",
      error: error.message
    };
  }
};

// Function to test direct database connection
export const testDatabaseDirectly = async () => {
  try {
    console.log("Testing database connection directly...");
    const response = await fetch('/api/db-test');
    
    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        message: `Database connection failed: ${response.status}`,
        details: errorText
      };
    }
    
    const data = await response.json();
    return {
      success: true,
      message: "Database connection successful",
      details: data
    };
  } catch (error) {
    return {
      success: false,
      message: "Error testing database connection",
      error: error.message
    };
  }
};

// Add this function to check if tables exist
export const checkTablesExist = async () => {
  try {
    console.log("Checking if tables exist...");
    const response = await fetch('/api/check-tables');
    
    if (!response.ok) {
      return {
        success: false,
        message: `Failed to check tables: ${response.status}`,
        details: await response.text()
      };
    }
    
    const data = await response.json();
    return {
      success: true,
      details: data
    };
  } catch (error) {
    return {
      success: false,
      message: "Error checking tables",
      error: error.message
    };
  }
};

// Enhanced diagnostics
export const runDiagnostics = async () => {
  const results = {
    apiConnection: await checkApiConnectivity(),
    dbConnection: null,
    recommendations: []
  };
  
  // Only test DB directly if API is reachable
  if (results.apiConnection.success) {
    results.dbConnection = await testDatabaseDirectly();
    
    // Generate recommendations based on test results
    if (!results.dbConnection.success) {
      results.recommendations.push(
        "Check the Flask logs for detailed error messages",
        "Verify database credentials in the Flask configuration",
        "Ensure the database server is running and accessible"
      );
    }
  } else {
    results.recommendations.push(
      "Ensure the Flask server is running",
      "Check for CORS issues - API URL may be incorrect",
      "Verify that the proxy configuration in package.json is correct",
      "Look at the terminal where your Flask server is running for error messages"
    );
  }
  
  return results;
}; 