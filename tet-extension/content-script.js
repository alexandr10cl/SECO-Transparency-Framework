// SECO-TransP Content Script for Heatmap Data Capture
// Based on UFPA UX-Tracking Extension code with extensive logging

console.log("🔥 SECO-TransP Content Script loaded on:", window.location.href);

// Global variables for heatmap data collection (based on UFPA structure)
let pageHeight = 0;
let isRecording = false;
let hasStartedRecording = false;
let currentTaskId = null;
let currentProcessId = null;

// Get page height (UFPA approach)
pageHeight = Math.max(document.body.scrollHeight, document.body.offsetHeight);
console.log("📏 Page height detected:", pageHeight);

// Mouse and keyboard tracking variables (UFPA structure)
let mouse = { id: "", class: "", x: 0, y: 0 };
let keyboard = { id: "", class: "", x: 0, y: 0, typed: "" };

// Heatmap data structure (adapted from UFPA dataDict)
let heatmapData = {
  type: [],
  time: [],
  class: [],
  id: [],
  x: [],
  y: [],
  value: [],
  scroll: [],
  taskId: [],
  processId: [],
  url: [],
  timestamp: []
};

// Time tracking variables (UFPA approach)
let clocker = 0;
let mouseTimeout;
let freezeInterval;
let clockInterval;
let sendInterval;

// Function to get screen coordinates (UFPA function)
function getScreenCoordinates(obj) {
  let posX = 0, posY = 0;
  while (obj) {
    posX += obj.offsetLeft;
    posY += obj.offsetTop;
    obj = obj.offsetParent;
  }
  return { x: posX, y: posY };
}

// Function to store interaction data (UFPA approach with SECO enhancements)
function storeInteraction(interDict) {
  if (!isRecording || !currentTaskId) {
    console.log("⚠️ Not recording or no task ID, skipping interaction");
    return;
  }

  interDict.time = clocker;
  interDict.scroll = Math.round(document.documentElement.scrollTop);
  interDict.taskId = currentTaskId;
  interDict.processId = currentProcessId;
  interDict.url = window.location.href;
  interDict.timestamp = new Date().toISOString();

  // Store in heatmap data structure
  Object.keys(interDict).forEach(key => {
    if (heatmapData[key] !== undefined) {
      heatmapData[key].push(interDict[key]);
    }
  });

  console.log("📊 Interaction stored:", {
    type: interDict.type,
    x: interDict.x,
    y: interDict.y,
    taskId: interDict.taskId,
    url: interDict.url,
    totalPoints: heatmapData.x.length
  });
}

// Mouse event handlers (UFPA approach with throttling)
function setupMouseListeners() {
  console.log("🖱️ Setting up mouse listeners");
  document.addEventListener('mousemove', storeMouseData);
  document.addEventListener('click', storeMouseData);
  document.addEventListener('wheel', storeMouseData);
}

function storeMouseData(e) {
  clearTimeout(mouseTimeout);
  mouseTimeout = setTimeout(() => {
    if (!isRecording || !currentTaskId) return;

    clearTimeout(freezeInterval);
    freezeInterval = setTimeout(() => {
      storeInteraction({ 
        type: 'freeze', 
        x: mouse.x, 
        y: mouse.y, 
        id: mouse.id, 
        class: mouse.class, 
        value: null 
      });
    }, 10000);

    // Capture mouse information (UFPA approach)
    mouse.id = e.target.id;
    mouse.class = e.target.className;
    mouse.x = e.pageX;
    mouse.y = e.pageY;

    // Store the interaction
    storeInteraction({
      type: e.type,
      x: mouse.x,
      y: mouse.y,
      id: mouse.id,
      class: mouse.class,
      value: null
    });
  }, 200); // 200ms throttle (UFPA approach)
}

// Keyboard event handlers (UFPA approach)
function setupKeyboardListeners() {
  console.log("⌨️ Setting up keyboard listeners");
  document.addEventListener('keydown', handleKeyDown);
}

function handleKeyDown(e) {
  if (!isRecording || !currentTaskId) return;

  if (e.key.length === 1) keyboard.typed += e.key;
  if (e.key === 'Enter' || e.key === 'Backspace') {
    storeInteraction({
      type: 'keyboard',
      x: mouse.x,
      y: mouse.y,
      id: keyboard.id,
      class: keyboard.class,
      value: { key: keyboard.typed }
    });
    keyboard.typed = '';
  }
}

// Clock function (UFPA approach)
function startClock() {
  console.log("⏰ Starting clock");
  clockInterval = setInterval(() => {
    clocker++;
  }, 1000);
}

function stopClock() {
  console.log("⏰ Stopping clock");
  clearInterval(clockInterval);
  clocker = 0;
}

// Data sending function (adapted from UFPA)
function sendHeatmapData() {
  if (!isRecording || !currentTaskId) {
    console.log("⚠️ Not recording or no task ID, skipping data send");
    return;
  }

  if (heatmapData.x.length === 0) {
    console.log("📊 No heatmap data to send");
    return;
  }

  console.log("📤 Sending heatmap data:", {
    taskId: currentTaskId,
    processId: currentProcessId,
    url: window.location.href,
    totalPoints: heatmapData.x.length,
    pageHeight: pageHeight
  });

  // Send data to background script
  chrome.runtime.sendMessage({
    type: 'heatmapData',
    data: {
      ...heatmapData,
      pageHeight: pageHeight,
      pageWidth: window.innerWidth,
      pageTitle: document.title,
      pageDescription: document.querySelector('meta[name="description"]')?.getAttribute('content') || null
    }
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error("❌ Error sending heatmap data:", chrome.runtime.lastError);
    } else {
      console.log("✅ Heatmap data sent successfully");
    }
  });

  // Clear data after sending (UFPA approach)
  Object.keys(heatmapData).forEach(key => {
    if (Array.isArray(heatmapData[key])) {
      heatmapData[key] = [];
    }
  });
}

// Start recording function (UFPA approach with SECO integration)
function startRecording(taskId, processId) {
  console.log("🎬 Starting heatmap recording for task:", taskId, "process:", processId);
  
  isRecording = true;
  hasStartedRecording = true;
  currentTaskId = taskId;
  currentProcessId = processId;

  // Setup event listeners
  setupMouseListeners();
  setupKeyboardListeners();

  // Start clock
  startClock();

  // Start data sending interval (every 5 seconds like UFPA)
  sendInterval = setInterval(sendHeatmapData, 5000);

  console.log("✅ Heatmap recording started successfully");
}

// Stop recording function (UFPA approach)
function stopRecording() {
  console.log("🛑 Stopping heatmap recording");
  
  isRecording = false;
  hasStartedRecording = false;

  // Stop clock
  stopClock();

  // Clear intervals
  clearInterval(sendInterval);
  clearTimeout(freezeInterval);
  clearTimeout(mouseTimeout);

  // Remove event listeners
  document.removeEventListener('mousemove', storeMouseData);
  document.removeEventListener('click', storeMouseData);
  document.removeEventListener('wheel', storeMouseData);
  document.removeEventListener('keydown', handleKeyDown);

  // Send final data
  sendHeatmapData();

  // Reset variables
  currentTaskId = null;
  currentProcessId = null;

  console.log("✅ Heatmap recording stopped successfully");
}

// Cleanup function (UFPA approach)
function cleanup() {
  console.log("🧹 Cleaning up heatmap recording");
  
  stopRecording();
  
  // Clear all data
  Object.keys(heatmapData).forEach(key => {
    if (Array.isArray(heatmapData[key])) {
      heatmapData[key] = [];
    }
  });

  console.log("✅ Cleanup completed");
}

// Message listener for communication with popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("📨 Content script received message:", request.type);

  switch (request.type) {
    case "startHeatmapCapture":
      console.log("🎬 Starting heatmap capture for task:", request.taskId);
      startRecording(request.taskId, request.processId);
      sendResponse({ success: true, message: "Heatmap capture started" });
      break;

    case "stopHeatmapCapture":
      console.log("🛑 Stopping heatmap capture");
      stopRecording();
      sendResponse({ success: true, message: "Heatmap capture stopped" });
      break;

    case "getHeatmapStatus":
      sendResponse({
        isRecording: isRecording,
        currentTaskId: currentTaskId,
        currentProcessId: currentProcessId,
        totalPoints: heatmapData.x.length,
        url: window.location.href
      });
      break;

    case "cleanupHeatmap":
      cleanup();
      sendResponse({ success: true, message: "Heatmap cleanup completed" });
      break;

    default:
      console.log("❓ Unknown message type:", request.type);
      sendResponse({ success: false, message: "Unknown message type" });
  }

  return true; // Keep message channel open for async response
});

// Initialize content script
console.log("🚀 SECO-TransP Content Script initialized successfully");

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  console.log("🔄 Page unloading, cleaning up heatmap data");
  cleanup();
});



