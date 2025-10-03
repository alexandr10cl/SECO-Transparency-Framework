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

// Open side panel when extension icon is clicked
chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});