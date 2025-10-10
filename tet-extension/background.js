// Enhanced tab/page navigation tracking
chrome.tabs.onUpdated.addListener(function(tabId, changeInfo, tab) {
    // Only send message when page is completely loaded and it's the active tab
    if (changeInfo.status === 'complete' && tab.active && tab.url) {
      const message = {
        action: "pageNavigation",
        url: tab.url,
        timestamp: new Date().toISOString(),
        title: tab.title,
        tabId: tabId
      };
      
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) {
          console.log("🚫 Navigation message not handled:", chrome.runtime.lastError.message);
        } else if (response) {
          console.log("✅ Navigation tracked:", response);
        }
      });
    }
});

// Enhanced tab switching tracking
chrome.tabs.onActivated.addListener(function(activeInfo) {
    chrome.tabs.get(activeInfo.tabId, function(tab) {
      if (tab && tab.url) {
        const message = {
          action: "tabSwitch",
          url: tab.url,
          timestamp: new Date().toISOString(),
          title: tab.title,
          tabId: tab.id
        };
        
        chrome.runtime.sendMessage(message, (response) => {
          if (chrome.runtime.lastError) {
            console.log("🚫 Tab switch message not handled:", chrome.runtime.lastError.message);
          } else if (response) {
            console.log("✅ Tab switch tracked:", response);
          }
        });
      }
    });
});

// Heatmap data handling (new functionality)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("📨 Background script received message:", request.type);

  switch (request.type) {
    case "heatmapData":
      console.log("🔥 Received heatmap data:", {
        taskId: request.data.taskId?.[0],
        processId: request.data.processId?.[0],
        url: request.data.url?.[0],
        totalPoints: request.data.x?.length || 0,
        pageHeight: request.data.pageHeight,
        pageWidth: request.data.pageWidth
      });

      // Forward heatmap data to popup for processing
      chrome.runtime.sendMessage({
        type: "forwardHeatmapData",
        data: request.data
      }, (response) => {
        if (chrome.runtime.lastError) {
          console.error("❌ Error forwarding heatmap data:", chrome.runtime.lastError);
        } else {
          console.log("✅ Heatmap data forwarded successfully");
        }
      });

      sendResponse({ success: true, message: "Heatmap data received" });
      break;

    default:
      console.log("❓ Unknown message type in background:", request.type);
      sendResponse({ success: false, message: "Unknown message type" });
  }

  return true; // Keep message channel open for async response
});

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});